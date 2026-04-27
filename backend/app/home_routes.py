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
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.models
from app.database import get_db
from app.home_models import (
    HOME_MAX_MEMBERS,
    Home,
    HomeMembership,
    _generate_invite_code,
)
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
    return db.query(Home).filter(Home.id == home_id, Home.is_active).first()


def _count_active_members(home_id, db: Session) -> int:
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
        user = db.query(app.models.User).filter(app.models.User.id == m.user_id).first()
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


def _make_user_products_public(user_id, home_id, db: Session) -> None:
    from app.inventory_models import InventoryProduct, InventoryProductOwner

    product_ids_tuples = (
        db.query(InventoryProduct.id_inventari)
        .join(InventoryProductOwner, InventoryProduct.id_inventari == InventoryProductOwner.id_inventari)
        .filter(
            InventoryProduct.id_llar == home_id,
            InventoryProductOwner.user_id == user_id
        )
        .all()
    )
    product_ids = [p[0] for p in product_ids_tuples]
    if product_ids:
        db.query(InventoryProduct).filter(
            InventoryProduct.id_inventari.in_(product_ids),
            InventoryProduct.es_privat == True
        ).update({"es_privat": False}, synchronize_session=False)
        
        db.query(InventoryProductOwner).filter(
            InventoryProductOwner.id_inventari.in_(product_ids),
            InventoryProductOwner.user_id == user_id
        ).delete(synchronize_session=False)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_home(
    data: CreateHomeSchema,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    if data.name is None:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "El nom és obligatori.",
                "code": "REQUIRED_FIELDS_MISSING",
            },
        )

    name = data.name.strip()

    if len(name) < 2 or len(name) > 20:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "El nom ha de tenir entre 2 i 20 caràcters.",
                "code": "HOME_NAME_INVALID_LENGTH",
            },
        )

    if "  " in name:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "El nom no pot contenir espais consecutius.",
                "code": "HOME_NAME_INVALID_SPACES",
            },
        )

    if not all(c.isalnum() or c == " " for c in name):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "El nom conté caràcters no vàlids.",
                "code": "HOME_NAME_INVALID_CHARACTERS",
            },
        )

    existing = _get_active_membership(user.id, db)
    if existing:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Ja pertanys a una llar.",
                "code": "USER_ALREADY_HAS_HOME",
            },
        )

    invite_code = _generate_invite_code()
    attempts = 0
    while (
        db.query(Home)
        .filter(
            Home.invite_code == invite_code,
            Home.is_active,
        )
        .first()
        and attempts < 5
    ):
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
    home_data = _build_home_response(
        home,
        members,
        user.id,
        include_members=True,
    ).model_dump()

    return JSONResponse(
        status_code=201,
        content={
            "message": "Llar creada correctament",
            "code": "HOME_CREATED",
            "home": home_data,
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

    home = (
            db.query(Home)
            .filter(Home.invite_code == invite_code, Home.is_active)
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

    # 1. Busquem qualsevol membresia prèvia d'aquest usuari en AQUESTA llar (activa o no)
    existing_membership_in_this_home = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user.id,
            HomeMembership.home_id == home.id,
        )
        .first()
    )

    # Si ja està activa, error 409
    if existing_membership_in_this_home and existing_membership_in_this_home.is_active:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Ja formes part d'aquesta llar.",
                "code": "USER_ALREADY_IN_HOME",
            },
        )

    # 2. Comprovar si l'usuari ja està en UNA ALTRA llar activa
    existing_active_elsewhere = _get_active_membership(user.id, db)
    if existing_active_elsewhere:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Ja pertanys a una llar.",
                "code": "USER_ALREADY_HAS_HOME",
            },
        )

    if home.owner_id == user.id:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "No pots unir-te a la teva pròpia llar.",
                "code": "CANNOT_JOIN_OWN_HOME",
            },
        )

    current_count = _count_active_members(home.id, db)
    if current_count >= HOME_MAX_MEMBERS:
        return JSONResponse(
            status_code=409,
            content={
                "detail": (
                    f"La llar ha assolit el límit màxim de "
                    f"{HOME_MAX_MEMBERS} membres"
                ),
                "code": "HOME_MEMBER_LIMIT_REACHED",
            },
        )

    if existing_membership_in_this_home:
        membership = existing_membership_in_this_home
        membership.is_active = True
        membership.left_at = None
        membership.joined_at = datetime.utcnow()
        membership.role = "member"
    else:
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
            content={
                "detail": "No pertanys a cap llar",
                "code": "NOT_IN_HOME",
            },
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "La llar no existeix o ha estat dissolta",
                "code": "HOME_NOT_FOUND",
            },
        )

    members = _get_members_with_users(home.id, db)
    response_obj = _build_home_response(home, members, user.id, include_members=True)

    import fastapi.encoders

    # Convertim a dict per evitar lazy-loading fora de la sessió
    data = fastapi.encoders.jsonable_encoder(response_obj)
    data["code"] = "HOME_RETRIEVED"

    return JSONResponse(status_code=200, content=data)


@router.get("/invite-code", status_code=status.HTTP_200_OK)
def get_invite_code(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership or membership.role != "owner":
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Només el propietari pot veure el codi d'invitació",
                "code": "OWNER_PERMISSION_REQUIRED",
            },
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "La llar no existeix",
                "code": "HOME_NOT_FOUND",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "code": "INVITE_CODE_RETRIEVED",
            "invite_code": home.invite_code,
            "home_id": str(home.id),
        },
    )


@router.post("/invite-code/regenerate", status_code=status.HTTP_200_OK)
def regenerate_invite_code(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership or membership.role != "owner":
        return JSONResponse(
            status_code=403,
            content={
                "detail": ("Només el propietari pot regenerar el codi d'invitació"),
                "code": "OWNER_PERMISSION_REQUIRED",
            },
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        raise HTTPException(status_code=404, detail="La llar no existeix")

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

    return JSONResponse(
        status_code=200,
        content={
            "code": "INVITE_CODE_REGENERATED",
            "message": "Codi d'invitació regenerat correctament",
            "invite_code": home.invite_code,
        },
    )


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
            new_owner_membership = other_memberships[0]

            new_owner_user = (
                db.query(app.models.User)
                .filter(app.models.User.id == new_owner_membership.user_id)
                .first()
            )
            new_owner_name = new_owner_user.username if new_owner_user else "usuari"

            membership.is_active = False
            membership.left_at = now
            new_owner_membership.role = "owner"
            home.owner_id = new_owner_membership.user_id
            home.updated_at = now

            _make_user_products_public(user.id, home.id, db)
            db.commit()

            return JSONResponse(
                status_code=200,
                content={
                    "message": (
                        f"Has sortit de la llar. La propietat ha estat "
                        f"transferida a {new_owner_name}"
                    ),
                    "code": "HOME_LEFT_OWNER_TRANSFERRED",
                },
            )
        else:
            membership.is_active = False
            membership.left_at = now
            home.is_active = False
            home.updated_at = now

            _make_user_products_public(user.id, home.id, db)
            db.commit()

            return JSONResponse(
                status_code=200,
                content={
                    "message": ("Has sortit de la llar i aquesta ha estat dissolta"),
                    "code": "HOME_LEFT_AND_DISSOLVED",
                },
            )

    # ==================== Membre normal ====================
    membership.is_active = False
    membership.left_at = now
    home.updated_at = now
    
    _make_user_products_public(user.id, home.id, db)
    db.commit()
    db.expire_all()

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
    user, _session = current

    owner_membership = _get_active_membership(user.id, db)
    if not owner_membership or owner_membership.role != "owner":
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Només el propietari pot expulsar membres",
                "code": "OWNER_PERMISSION_REQUIRED",
            },
        )

    if str(data.user_id) == str(user.id):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "No pots expulsar-te a tu mateix",
                "code": "CANNOT_KICK_SELF",
            },
        )

    home = _get_active_home(owner_membership.home_id, db)
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "La llar no existeix",
                "code": "HOME_NOT_FOUND",
            },
        )

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
        return JSONResponse(
            status_code=404,
            content={
                "detail": "L'usuari no pertany a aquesta llar",
                "code": "TARGET_USER_NOT_IN_HOME",
            },
        )

    now = datetime.utcnow()
    target_membership.is_active = False
    target_membership.left_at = now
    home.updated_at = now
    
    _make_user_products_public(data.user_id, home.id, db)
    db.commit()

    kicked_user = (
        db.query(app.models.User).filter(app.models.User.id == data.user_id).first()
    )
    kicked_username = kicked_user.username if kicked_user else str(data.user_id)

    return JSONResponse(
        status_code=200,
        content={
            "code": "MEMBER_KICKED",
            "message": (f"L'usuari '{kicked_username}' ha estat expulsat de la llar"),
        },
    )


@router.get("/sync", status_code=status.HTTP_200_OK)
def sync_home(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)

    if not membership:
        return JSONResponse(
            status_code=404,
            content={
                "home_active": False,
                "detail": "No pertanys a cap llar",
                "code": "NOT_IN_HOME",
            },
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
        .filter(
            HomeMembership.home_id == home.id,
            HomeMembership.is_active,  # E712 fix: sense == True
        )
        .count()
    )

    return JSONResponse(
        status_code=200,
        content={
            "home_active": True,
            "home_id": str(home.id),
            "updated_at": (home.updated_at.isoformat() if home.updated_at else None),
            "member_count": member_count,
            "code": "HOME_SYNC_OK",
        },
    )
