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
from fastapi.responses import JSONResponse

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
    user, _session = current

    # ==================== REQUIRED ====================
    if data.name is None:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "El nom és obligatori.",
                "code": "REQUIRED_FIELDS_MISSING",
            },
        )
    
    # Trim inicial
    name = data.name.strip()

    # ==================== LENGTH ====================
    if len(name) < 2 or len(name) > 20:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "El nom ha de tenir entre 2 i 20 caràcters.",
                "code": "HOME_NAME_INVALID_LENGTH",
            },
        )

    # ==================== SPACES DOBLES ====================
    if "  " in name:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "El nom no pot contenir espais consecutius.",
                "code": "HOME_NAME_INVALID_SPACES",
            },
        )

    # ==================== CARÀCTERS ====================
    if not all(c.isalnum() or c == " " for c in name):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "El nom conté caràcters no vàlids.",
                "code": "HOME_NAME_INVALID_CHARACTERS",
            },
        )

    # ==================== USER ALREADY HAS HOME ====================
    existing = _get_active_membership(user.id, db)
    if existing:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Ja pertanys a una llar.",
                "code": "USER_ALREADY_HAS_HOME",
            },
        )

    # ==================== CREACIÓ ====================
    invite_code = _generate_invite_code()
    attempts = 0
    while db.query(Home).filter(Home.invite_code == invite_code, Home.is_active).first() and attempts < 5:
        invite_code = _generate_invite_code()
        attempts += 1

    home = Home(
        name=name,
        owner_id=user.id,
        invite_code=invite_code,
    )
    db.add(home)
    db.flush()

    membership = HomeMembership(
        home_id=home.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
    db.commit()
    db.refresh(home)

    members = _get_members_with_users(home.id, db)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Llar creada correctament",
            "code": "HOME_CREATED",
            "home": _build_home_response(home, members, user.id, include_members=True).model_dump(),
        },
    )


@router.post("/join", status_code=status.HTTP_200_OK)
def join_home(
    data: JoinHomeSchema,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    invite_code = data.invite_code.strip() if data.invite_code else ""

    # ==================== VALIDACIÓ CODI ====================
    if not invite_code:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "El codi d'invitació és obligatori.",
                "code": "INVITE_CODE_REQUIRED",
            },
        )

    if any(ord(c) < 32 or ord(c) > 126 for c in invite_code):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "El codi d'invitació conté caràcters no vàlids.",
                "code": "INVITE_CODE_INVALID_FORMAT",
            },
        )

    # ==================== BUSCAR LLAR ====================
    home = (
        db.query(Home)
        .filter(
            Home.invite_code == invite_code,
            Home.is_active,
        )
        .first()
    )

    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Codi d'invitació invàlid o caducat",
                "code": "INVITE_CODE_INVALID_OR_EXPIRED",
            },
        )

    # ==================== VALIDACIONS USUARI ====================

    # Ja és membre d'aquesta llar
    existing_in_home = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user.id,
            HomeMembership.home_id == home.id,
        )
        .first()
    )

    if existing_in_home:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Ja formes part d'aquesta llar.",
                "code": "USER_ALREADY_IN_HOME",
            },
        )

    # Ja pertany a una altra llar
    existing = _get_active_membership(user.id, db)
    if existing:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Ja pertanys a una llar.",
                "code": "USER_ALREADY_HAS_HOME",
            },
        )

    # No pot unir-se a la seva pròpia llar
    if home.owner_id == user.id:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "No pots unir-te a la teva pròpia llar.",
                "code": "CANNOT_JOIN_OWN_HOME",
            },
        )

    # ==================== LÍMIT MEMBRES ====================
    current_count = _count_active_members(home.id, db)
    if current_count >= HOME_MAX_MEMBERS:
        return JSONResponse(
            status_code=409,
            content={
                "detail": f"La llar ha assolit el límit màxim de {HOME_MAX_MEMBERS} membres",
                "code": "HOME_MEMBER_LIMIT_REACHED",
            },
        )

    # ==================== CREAR MEMBRESIA ====================
    membership = HomeMembership(
        home_id=home.id,
        user_id=user.id,
        role="member",
    )
    db.add(membership)

    home.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(home)

    members = _get_members_with_users(home.id, db)

    return {
        "message": "T'has unit a la llar correctament",
        "code": "HOME_JOINED",
        "home": _build_home_response(home, members, user.id, include_members=True),
    }


@router.get("/", status_code=status.HTTP_200_OK)
def get_home(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return JSONResponse(
            status_code=404,
            content={"detail": "No pertanys a cap llar", "code": "NOT_IN_HOME"}
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        return JSONResponse(
            status_code=404,
            content={"detail": "La llar no existeix o ha estat dissolta", "code": "HOME_NOT_FOUND"}
        )

    members = _get_members_with_users(home.id, db)

    # Construïm la resposta
    response_obj = _build_home_response(home, members, user.id, include_members=True)
    
    # IMPORTANT: Convertim a dict abans de posar-ho al JSONResponse 
    # per evitar que Pydantic intenti fer lazy-loading de dades de la BD fora de la sessió.
    import fastapi.encoders
    data = fastapi.encoders.jsonable_encoder(response_obj)
    data["code"] = "HOME_RETRIEVED"
    
    return JSONResponse(status_code=200, content=data)

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
        return JSONResponse(status_code=403, content={
            "detail": "Només el propietari pot veure el codi d'invitació",
            "code": "OWNER_PERMISSION_REQUIRED",
        })

    home = _get_active_home(membership.home_id, db)
    if not home:
        return JSONResponse(status_code=404, content={"detail": "La llar no existeix", "code": "HOME_NOT_FOUND"})

    return JSONResponse(status_code=200, content={
        "code": "INVITE_CODE_RETRIEVED",
        "invite_code": home.invite_code,
        "home_id": str(home.id),
    })


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
        return JSONResponse(status_code=403, content={
            "detail": "Només el propietari pot regenerar el codi d'invitació",
            "code": "OWNER_PERMISSION_REQUIRED",
        })

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

    return JSONResponse(status_code=200, content={
        "code": "INVITE_CODE_REGENERATED",
        "message": "Codi d'invitació regenerat correctament",
        "invite_code": home.invite_code,
    })

@router.delete("/leave", status_code=status.HTTP_200_OK)
def leave_home(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return JSONResponse(
            status_code=404,
            content={"detail": "No pertanys a cap llar", "code": "NOT_IN_HOME"},
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        return JSONResponse(
            status_code=404,
            content={"detail": "La llar no existeix", "code": "NOT_IN_HOME"},
        )

    now = datetime.utcnow()

    other_memberships = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.home_id == home.id,
            HomeMembership.is_active,
            HomeMembership.user_id != user.id,
        )
        .order_by(HomeMembership.joined_at.asc())
        .all()
    )

   # ==================== Propietari ====================
    if membership.role == "owner":
        if other_memberships:
            # 1. Triem el nou propietari (el més antic)
            new_owner_membership = other_memberships[0]
            
            # 2. Busquem l'usuari per obtenir el seu nom ABANS del commit
            # Utilitzem app.models.User tal com el tens a l'import
            new_owner_user = (
                db.query(app.models.User)
                .filter(app.models.User.id == new_owner_membership.user_id)
                .first()
            )
            
            # Guardem el nom en una variable de text (string)
            new_owner_name = new_owner_user.username if new_owner_user else "usuari"

            # 3. Fem els canvis de lògica
            membership.is_active = False
            membership.left_at = now
            
            new_owner_membership.role = "owner"
            home.owner_id = new_owner_membership.user_id
            home.updated_at = now

            db.commit()
            
            # No cal db.expire_all() aquí, el TestClient ho agrairà
            return JSONResponse(
                status_code=200,
                content={
                    "message": f"Has sortit de la llar. La propietat ha estat transferida a {new_owner_name}",
                    "code": "HOME_LEFT_OWNER_TRANSFERRED",
                },
            )
        else:
            # Cas llar privada (sol)
            membership.is_active = False
            membership.left_at = now
            home.is_active = False
            home.updated_at = now
            
            db.commit()
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Has sortit de la llar i aquesta ha estat dissolta",
                    "code": "HOME_LEFT_AND_DISSOLVED",
                },
            )

    # ==================== Membre normal ====================
    membership.is_active = False
    membership.left_at = now
    home.updated_at = now
    db.commit()
    db.expire_all()  # ← neteja la sessió

    if other_memberships:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Has sortit de la llar correctament",
                "code": "HOME_LEFT",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "message": "Has sortit de la llar correctament",
            "code": "HOME_LEFT",
        },
    )


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
        return JSONResponse(status_code=403, content={
            "detail": "Només el propietari pot expulsar membres",
            "code": "OWNER_PERMISSION_REQUIRED",
        })

    # No es pot expulsar a si mateix
    if str(data.user_id) == str(user.id):
        return JSONResponse(status_code=400, content={
            "detail": "No pots expulsar-te a tu mateix",
            "code": "CANNOT_KICK_SELF",
        })

    home = _get_active_home(owner_membership.home_id, db)
    if not home:
        return JSONResponse(status_code=404, content={
            "detail": "La llar no existeix", 
            "code": "HOME_NOT_FOUND"
            })

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
        return JSONResponse(status_code=404, content={
            "detail": "L'usuari no pertany a aquesta llar",
            "code": "TARGET_USER_NOT_IN_HOME",
        })

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

    return JSONResponse(status_code=200, content={
        "code": "MEMBER_KICKED",
        "message": f"L'usuari '{kicked_username}' ha estat expulsat de la llar",
    })

@router.get("/sync", status_code=status.HTTP_200_OK)
def sync_home(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    
    # Si no hi ha membresia, vol dir que l'usuari ja no és a la llar
    if not membership:
        return JSONResponse(
            status_code=404,
            content={
                "home_active": False,
                "detail": "No pertanys a cap llar",
                "code": "NOT_IN_HOME"
            }
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        return JSONResponse(
            status_code=200,
            content={
                "home_active": False,
                "updated_at": None,
                "message": "La llar ha estat dissolta",
                "code": "HOME_DISSOLVED",
            },
        )

    member_count = (
        db.query(HomeMembership)
        .filter(HomeMembership.home_id == home.id, HomeMembership.is_active == True)
        .count() # .count() és més eficient que len(.all())
    )

    return JSONResponse(
        status_code=200,
        content={
            "home_active": True,
            "home_id": str(home.id),
            "updated_at": home.updated_at.isoformat() if home.updated_at else None,
            "member_count": member_count,
            "code": "HOME_SYNC_OK",
        },
    )