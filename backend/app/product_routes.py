from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.models
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.product_models import Product
from app.product_schemas import CreateManualProductSchema
from app.validation import contains_control_characters, contains_escape_sequences

router = APIRouter(prefix="/products", tags=["products"])


def _json_error(code: str, detail: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "code": code,
        },
    )


def _get_active_membership(user_id, db: Session):
    return (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user_id,
            HomeMembership.is_active,
        )
        .first()
    )


def _get_active_home(home_id, db: Session):
    return (
        db.query(Home)
        .filter(
            Home.id == home_id,
            Home.is_active,
        )
        .first()
    )


def _normalize_product_text(value: str | None, field_name: str, max_len: int):
    raw = value if value is not None else ""

    # Validar caracteres inválidos ANTES del strip
    if contains_control_characters(raw) or contains_escape_sequences(raw):
        return None, _json_error(
            f"{field_name.upper()}_INVALID_CHARACTERS",
            f"El camp {field_name} conté caràcters no permesos",
            400,
        )

    trimmed = raw.strip()

    if not trimmed:
        return None, _json_error(
            f"{field_name.upper()}_REQUIRED",
            f"El camp {field_name} és obligatori",
            422,
        )

    if len(trimmed) > max_len:
        return None, _json_error(
            f"{field_name.upper()}_TOO_LONG",
            f"El camp {field_name} és massa llarg",
            422,
        )

    if contains_control_characters(trimmed) or contains_escape_sequences(trimmed):
        return None, _json_error(
            f"{field_name.upper()}_INVALID_CHARACTERS",
            f"El camp {field_name} conté caràcters no permesos",
            400,
        )

    return trimmed, None


@router.post("/manual", status_code=201)
def create_manual_product(
    data: CreateManualProductSchema,
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

    name, error = _normalize_product_text(data.name, "name", 120)
    if error:
        return error

    category, error = _normalize_product_text(data.category, "category", 64)
    if error:
        return error

    if data.price is None:
        return _json_error("PRICE_REQUIRED", "El camp price és obligatori", 422)

    if data.quantity is None:
        return _json_error("QUANTITY_REQUIRED", "El camp quantity és obligatori", 422)

    if data.price < 0:
        return _json_error("PRICE_INVALID", "El preu no pot ser negatiu", 422)

    if data.price != round(data.price, 2):
        return _json_error(
            "PRICE_INVALID", "El preu no pot tenir més de 2 decimals", 422
        )

    if data.quantity <= 0:
        return _json_error(
            "QUANTITY_INVALID", "La quantitat ha de ser superior a 0", 422
        )

    owner_user_id = data.owner_user_id

    if owner_user_id is not None:
        owner_membership = (
            db.query(HomeMembership)
            .filter(
                HomeMembership.home_id == home.id,
                HomeMembership.user_id == owner_user_id,
                HomeMembership.is_active,
            )
            .first()
        )

        if not owner_membership:
            return _json_error(
                "OWNER_NOT_IN_HOME",
                "El propietari indicat no pertany a la llar",
                400,
            )

    product = Product(
        home_id=home.id,
        created_by_user_id=user.id,
        owner_user_id=owner_user_id,
        name=name,
        category=category,
        price=data.price,
        quantity=data.quantity,
        purchase_date=data.purchase_date,
        expiration_date=data.expiration_date,
    )

    db.add(product)

    # Important per a la sincronització amb la llar
    home.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(product)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Producte creat correctament",
            "code": "PRODUCT_CREATED",
            "product": {
                "id": str(product.id),
                "home_id": str(product.home_id),
                "created_by_user_id": str(product.created_by_user_id),
                "owner_user_id": (
                    str(product.owner_user_id) if product.owner_user_id else None
                ),
                "is_private": product.owner_user_id is not None,
                "name": product.name,
                "category": product.category,
                "price": str(product.price),
                "quantity": product.quantity,
                "purchase_date": (
                    product.purchase_date.isoformat() if product.purchase_date else None
                ),
                "expiration_date": (
                    product.expiration_date.isoformat()
                    if product.expiration_date
                    else None
                ),
                "created_at": product.created_at.isoformat(),
            },
        },
    )
