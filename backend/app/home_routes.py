"""
Mòdul de gestió de llar compartida (HOME).

Endpoints:
  POST   /home/              → Crear una llar
  POST   /home/join          → Unir-se a una llar via codi d'invitació
  GET    /home/              → Veure la llar pròpia + membres
  GET    /home/invite-code   → Obtenir el codi d'invitació (només propietari)
  POST   /home/invite-code/regenerate → Regenerar codi (només propietari)
  DELETE /home/leave         → Sortir de la llar
  DELETE /home/kick          → Expulsar un membre (només propietari)

Decisions tècniques:
  - Segueix el mateix patró de routes.py: lògica inline sense capa service separada.
  - Missatges d'error en català, coherents amb la resta del projecte.
  - Soft-delete per a membresies (left_at + is_active=False).
  - Si el propietari surt, la llar es dissol (tots els membres en són expulsats).
  - updated_at de Home s'actualitza en qualsevol canvi de membres per facilitar
    la sincronització poll-based des del client (comparar updated_at).
  - invite_code només visible per al propietari (privacitat).
  - Concurrència: .with_for_update() en lectures crítiques de membre_count.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import app.auth
import app.models
from app.database import get_db
from app.home_models import HOME_MAX_MEMBERS, Home, HomeMembership, _generate_invite_code
from app.home_schemas import (
    CreateHomeSchema,
    HomeDetailResponse,
    HomeResponse,
    JoinHomeSchema,
    KickMemberSchema,
    MemberResponse,
)

router = APIRouter(prefix="/home", tags=["home"])


# ── Helpers privats ───────────────────────────────────────────────────────────

def _get_active_membership(user_id, db: Session) -> HomeMembership | None:
    """Retorna la membresia activa de l'usuari o None."""
    return (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user_id,
            HomeMembership.is_active,
        )
        .first()
    )


def _get_active_home(home_id, db: Session) -> Home | None:
    """Retorna la llar activa o None."""
    return (
        db.query(Home)
        .filter(Home.id == home_id, Home.is_active)
        .first()
    )


def _count_active_members(home_id, db: Session) -> int:
    # FOR UPDATE sobre les files, després comptem en Python
    rows = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.home_id == home_id,
            HomeMembership.is_active,
        )
        .with_for_update()
        .all()
    )
    return len(rows)


def _get_members_with_users(home_id, db: Session) -> list[MemberResponse]:
    """Retorna la llista de membres amb informació d'usuari."""
    memberships = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.home_id == home_id,
            HomeMembership.is_active,
        )
        .all()
    )

    result = []
    for m in memberships:
        user = (
            db.query(app.models.User)
            .filter(app.models.User.id == m.user_id)
            .first()
        )
        if user:
            result.append(
                MemberResponse(
                    user_id=str(m.user_id),
                    username=user.username,
                    role=m.role,
                    joined_at=m.joined_at.isoformat(),
                )
            )
    return result


def _build_home_response(
    home: Home,
    members: list[MemberResponse],
    requesting_user_id,
    include_members: bool = False,
) -> HomeResponse | HomeDetailResponse:
    """
    Construeix la resposta de llar.
    El invite_code només s'exposa al propietari.
    """
    is_owner = str(home.owner_id) == str(requesting_user_id)

    base = dict(
        id=str(home.id),
        name=home.name,
        owner_id=str(home.owner_id),
        invite_code=home.invite_code if is_owner else None,
        member_count=len(members),
        created_at=home.created_at.isoformat(),
    )

    if include_members:
        return HomeDetailResponse(**base, members=members)
    return HomeResponse(**base)


def _dissolve_home(home: Home, db: Session) -> None:
    """
    Dissol una llar: desactiva totes les membresies i la llar.
    S'utilitza quan el propietari surt o elimina la llar.
    """
    now = datetime.utcnow()

    memberships = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.home_id == home.id,
            HomeMembership.is_active,
        )
        .all()
    )

    for m in memberships:
        m.is_active = False
        m.left_at = now

    home.is_active = False
    home.updated_at = now


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_home(
    data: CreateHomeSchema,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Crea una nova llar.
    Restricció: un usuari no pot crear una llar si ja pertany a una altra.
    El creador és automàticament el propietari amb rol 'owner'.
    """
    user, _session = current

    # Verificar que l'usuari no pertany ja a una llar
    existing = _get_active_membership(user.id, db)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ja pertanys a una llar. Surt-ne primer per crear-ne una de nova",
        )

    # Crear la llar amb codi d'invitació únic
    invite_code = _generate_invite_code()
    # Garantir unicitat del codi (reintents en cas de col·lisió)
    attempts = 0
    while (
        db.query(Home).filter(Home.invite_code == invite_code, Home.is_active).first()
        and attempts < 5
    ):
        invite_code = _generate_invite_code()
        attempts += 1

    home = Home(
        name=data.name,
        owner_id=user.id,
        invite_code=invite_code,
    )
    db.add(home)
    db.flush()  # obtenir home.id sense commit

    # Crear la membresia del propietari
    membership = HomeMembership(
        home_id=home.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
    db.commit()
    db.refresh(home)

    members = _get_members_with_users(home.id, db)

    return {
        "message": "Llar creada correctament",
        "home": _build_home_response(home, members, user.id, include_members=True),
    }


@router.post("/join", status_code=status.HTTP_200_OK)
def join_home(
    data: JoinHomeSchema,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unir-se a una llar via codi d'invitació.
    Restriccions:
      - L'usuari no pot pertànyer a cap altra llar.
      - La llar no pot superar HOME_MAX_MEMBERS membres.
      - No es pot re-unir a una llar de la qual ja formes part.
    """
    user, _session = current

    # Verificar que l'usuari no pertany ja a una llar
    existing = _get_active_membership(user.id, db)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ja pertanys a una llar. Surt-ne primer per unir-te a una altra",
        )

    # Buscar la llar pel codi d'invitació
    home = (
        db.query(Home)
        .filter(
            Home.invite_code == data.invite_code,
            Home.is_active,
        )
        .first()
    )

    if not home:
        raise HTTPException(
            status_code=404,
            detail="Codi d'invitació invàlid o caducat",
        )

    # Verificar límit de membres (amb lock per evitar race conditions)
    current_count = _count_active_members(home.id, db)
    if current_count >= HOME_MAX_MEMBERS:
        raise HTTPException(
            status_code=409,
            detail=f"La llar ha assolit el límit màxim de {HOME_MAX_MEMBERS} membres",
        )

    # Crear la membresia
    membership = HomeMembership(
        home_id=home.id,
        user_id=user.id,
        role="member",
    )
    db.add(membership)

    # Actualitzar updated_at per propagar el canvi als clients
    home.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(home)

    members = _get_members_with_users(home.id, db)

    return {
        "message": "T'has unit a la llar correctament",
        "home": _build_home_response(home, members, user.id, include_members=True),
    }


@router.get("/", status_code=status.HTTP_200_OK)
def get_home(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna la informació de la llar a la qual pertany l'usuari.
    Inclou la llista de membres.
    El codi d'invitació només s'exposa al propietari.
    """
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        raise HTTPException(
            status_code=404,
            detail="No pertanys a cap llar",
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        raise HTTPException(
            status_code=404,
            detail="La llar no existeix o ha estat dissolta",
        )

    members = _get_members_with_users(home.id, db)

    return _build_home_response(home, members, user.id, include_members=True)


@router.get("/invite-code", status_code=status.HTTP_200_OK)
def get_invite_code(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna el codi d'invitació de la llar.
    Restringit al propietari.
    """
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership or membership.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Només el propietari pot veure el codi d'invitació",
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        raise HTTPException(status_code=404, detail="La llar no existeix")

    return {
        "invite_code": home.invite_code,
        "home_id": str(home.id),
    }


@router.post("/invite-code/regenerate", status_code=status.HTTP_200_OK)
def regenerate_invite_code(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Regenera el codi d'invitació de la llar.
    Restringit al propietari.
    Útil per invalidar invitacions antigues.
    """
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership or membership.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Només el propietari pot regenerar el codi d'invitació",
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        raise HTTPException(status_code=404, detail="La llar no existeix")

    # Generar nou codi únic
    new_code = _generate_invite_code()
    attempts = 0
    while (
        db.query(Home).filter(Home.invite_code == new_code, Home.is_active).first()
        and attempts < 5
    ):
        new_code = _generate_invite_code()
        attempts += 1

    home.invite_code = new_code
    home.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Codi d'invitació regenerat correctament",
        "invite_code": home.invite_code,
    }


@router.delete("/leave", status_code=status.HTTP_200_OK)
def leave_home(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sortir de la llar.

    Comportament:
      - Membre normal: desactiva la seva membresia.
      - Propietari: dissol la llar i expulsa tots els membres.
        (El propietari ha de transferir la propietat o dissoldra la llar.)

    Decisió de disseny: no transferim propietat automàticament per evitar
    assignacions no consentides. El propietari és responsable de la llar.
    """
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        raise HTTPException(
            status_code=404,
            detail="No pertanys a cap llar",
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        raise HTTPException(status_code=404, detail="La llar no existeix")

    now = datetime.utcnow()

    if membership.role == "owner":
        # Dissoldre la llar
        _dissolve_home(home, db)
        db.commit()
        return {"message": "Has sortit de la llar i aquesta ha estat dissolta"}

    # Membre normal: soft-delete de la membresia
    membership.is_active = False
    membership.left_at = now
    home.updated_at = now
    db.commit()

    return {"message": "Has sortit de la llar correctament"}


@router.delete("/kick", status_code=status.HTTP_200_OK)
def kick_member(
    data: KickMemberSchema,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Expulsar un membre de la llar.
    Restringit al propietari.
    Restriccions:
      - No es pot expulsar a un mateix.
      - No es pot expulsar algú que no sigui de la llar.
    """
    user, _session = current

    # Verificar que l'usuari és propietari
    owner_membership = _get_active_membership(user.id, db)
    if not owner_membership or owner_membership.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Només el propietari pot expulsar membres",
        )

    # No es pot expulsar a si mateix
    if str(data.user_id) == str(user.id):
        raise HTTPException(
            status_code=400,
            detail="No pots expulsar-te a tu mateix. Utilitza l'endpoint de sortir",
        )

    home = _get_active_home(owner_membership.home_id, db)
    if not home:
        raise HTTPException(status_code=404, detail="La llar no existeix")

    # Buscar la membresia del membre a expulsar
    target_membership = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.home_id == home.id,
            HomeMembership.user_id == data.user_id,
            HomeMembership.is_active,
        )
        .first()
    )

    if not target_membership:
        raise HTTPException(
            status_code=404,
            detail="L'usuari no pertany a aquesta llar",
        )

    now = datetime.utcnow()
    target_membership.is_active = False
    target_membership.left_at = now
    home.updated_at = now
    db.commit()

    # Obtenir el nom de l'usuari expulsat per al missatge de resposta
    kicked_user = (
        db.query(app.models.User)
        .filter(app.models.User.id == data.user_id)
        .first()
    )
    kicked_username = kicked_user.username if kicked_user else str(data.user_id)

    return {"message": f"L'usuari '{kicked_username}' ha estat expulsat de la llar"}


@router.get("/sync", status_code=status.HTTP_200_OK)
def sync_home(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Endpoint de sincronització lleuger.
    Retorna l'updated_at de la llar perquè els clients puguin detectar
    canvis sense descarregar tota la informació (poll-based sync).

    El client compara el seu updated_at local amb el retornat:
      - Si és diferent → cridar GET /home/ per actualitzar l'estat complet.
      - Si és igual → no cal fer res.
    """
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        raise HTTPException(
            status_code=404,
            detail="No pertanys a cap llar",
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        # La llar ha estat dissolta (el propietari ha sortit)
        return {
            "home_active": False,
            "updated_at": None,
            "message": "La llar ha estat dissolta",
        }

    return {
        "home_active": True,
        "home_id": str(home.id),
        "updated_at": home.updated_at.isoformat(),
        "member_count": _count_active_members(home.id, db),
    }
