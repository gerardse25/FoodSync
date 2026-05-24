from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

import app.auth
import app.shopping_list_schemas as schemas
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.shopping_list_models import ShoppingListItem
from app.validation import contains_control_characters

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])


def _is_malicious(value: str) -> bool:
    v = value.upper()
    return "SELECT" in v or "DROP" in v or "DELETE" in v or "<SCRIPT>" in v


def _verify_membership(home_id: UUID, user_id: UUID, db: Session):
    membership = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user_id,
            HomeMembership.home_id == home_id,
            HomeMembership.is_active.is_(True),
        )
        .first()
    )
    return membership


@router.get("/{home_id}", response_model=None)
def get_shopping_list(
    home_id: UUID,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _ = current

    # Verify home and membership
    home = (
        db.query(Home).filter(Home.id == home_id, Home.is_active.is_(True)).first()
    )
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "code": "HOME_NOT_FOUND",
                "detail": "La llar no existeix o ha estat dissolta.",
            },
        )

    membership = _verify_membership(home_id, user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "detail": "Accés denegat: L'usuari no pertany a aquesta llar activa.",
            },
        )

    # Query all shopping list items
    rows = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.home_id == home_id)
        .all()
    )

    items_data = []
    for item in rows:
        items_data.append(
            {
                "id": str(item.id),
                "product_name": item.product_name,
                "quantity": item.quantity,
                "notes": item.notes,
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "code": "LIST_RETRIEVED",
            "message": "Llista de la compra obtinguda correctament.",
            "items": items_data,
        },
    )


@router.post("/{home_id}")
async def add_shopping_list_item(
    home_id: UUID,
    request: Request,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _ = current

    # Verify home and membership
    home = (
        db.query(Home).filter(Home.id == home_id, Home.is_active.is_(True)).first()
    )
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "code": "HOME_NOT_FOUND",
                "detail": "La llar no existeix o ha estat dissolta.",
            },
        )

    membership = _verify_membership(home_id, user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "detail": "Accés denegat: L'usuari no pertany a aquesta llar activa.",
            },
        )

    # Manual Request Validation
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_JSON",
                "detail": "El cos de la petició no és un JSON vàlid.",
            },
        )

    # 1. Validate quantity presence
    if "quantity" not in payload:
        return JSONResponse(
            status_code=400,
            content={
                "code": "QUANTITY_REQUIRED",
                "detail": "El camp quantitat és obligatori.",
            },
        )

    # 2. Validate product_name presence
    if "product_name" not in payload:
        return JSONResponse(
            status_code=400,
            content={
                "code": "NAME_REQUIRED",
                "detail": "El camp producte és obligatori.",
            },
        )

    product_name_raw = payload.get("product_name")
    if product_name_raw is None or not isinstance(product_name_raw, str):
        return JSONResponse(
            status_code=400,
            content={
                "code": "NAME_REQUIRED",
                "detail": "El camp producte ha de ser una cadena de text no buida.",
            },
        )

    product_name = product_name_raw.strip()
    if not product_name:
        return JSONResponse(
            status_code=400,
            content={
                "code": "NAME_REQUIRED",
                "detail": "El camp producte no pot estar buit.",
            },
        )

    # 3. Validate product_name control characters
    if contains_control_characters(product_name_raw):
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_NAME",
                "detail": "El camp producte no pot contenir caràcters de control.",
            },
        )

    # 4. Validate product_name length
    if len(product_name) > 100:
        return JSONResponse(
            status_code=400,
            content={
                "code": "NAME_TOO_LONG",
                "detail": "El camp producte no pot superar els 100 caràcters.",
            },
        )

    # 5. Validate product_name sql/script injection
    if _is_malicious(product_name):
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_NAME",
                "detail": "El camp producte conté caràcters o paraules no permeses.",
            },
        )

    # 6. Validate quantity type and value
    quantity = payload.get("quantity")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_QUANTITY",
                "detail": "La quantitat ha de ser un enter superior a zero.",
            },
        )

    # 7. Validate notes
    notes_raw = payload.get("notes")
    notes = None
    if "notes" in payload and notes_raw is not None:
        if not isinstance(notes_raw, str):
            return JSONResponse(
                status_code=400,
                content={
                    "code": "INVALID_NOTES",
                    "detail": "El camp notes ha de ser una cadena de text.",
                },
            )
        notes = notes_raw.strip()
        if contains_control_characters(notes_raw):
            return JSONResponse(
                status_code=400,
                content={
                    "code": "INVALID_NOTES",
                    "detail": "El camp notes no pot contenir caràcters de control.",
                },
            )
        if len(notes) > 300:
            return JSONResponse(
                status_code=400,
                content={
                    "code": "NOTES_TOO_LONG",
                    "detail": "El camp notes no pot superar els 300 caràcters.",
                },
            )
        if _is_malicious(notes):
            return JSONResponse(
                status_code=400,
                content={
                    "code": "INVALID_NOTES",
                    "detail": "El camp notes conté caràcters o paraules no permeses.",
                },
            )

    # Check if product name is already in the shopping list (case-insensitive)
    item = (
        db.query(ShoppingListItem)
        .filter(
            ShoppingListItem.home_id == home_id,
            func.lower(ShoppingListItem.product_name) == func.lower(product_name),
        )
        .first()
    )

    is_new = False
    if item:
        item.quantity += quantity
        # update casing to latest value
        item.product_name = product_name
        if notes is not None:
            item.notes = notes
        item.updated_at = datetime.utcnow()
    else:
        is_new = True
        item = ShoppingListItem(
            home_id=home_id,
            product_name=product_name,
            quantity=quantity,
            notes=notes,
        )
        db.add(item)

    # Update home's updated_at to trigger sync/changes
    home.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    status_code = 201 if is_new else 200

    return JSONResponse(
        status_code=status_code,
        content={
            "code": "PRODUCT_ADDED_TO_LIST" if is_new else "LIST_ITEM_UPDATED",
            "message": "Producte afegit a la llista de la compra",
            "data": {
                "id": str(item.id),
                "product_name": item.product_name,
                "quantity": item.quantity,
                "notes": item.notes,
                "is_new": is_new,
            },
        },
    )


@router.patch("/{home_id}/{item_id}")
async def update_shopping_list_item(
    home_id: UUID,
    item_id: UUID,
    request: Request,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _ = current

    # Verify home and membership
    home = (
        db.query(Home).filter(Home.id == home_id, Home.is_active.is_(True)).first()
    )
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "code": "HOME_NOT_FOUND",
                "detail": "La llar no existeix o ha estat dissolta.",
            },
        )

    membership = _verify_membership(home_id, user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "detail": "Accés denegat: L'usuari no pertany a aquesta llar activa.",
            },
        )

    # Find the item
    item = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.id == item_id, ShoppingListItem.home_id == home_id)
        .first()
    )

    if not item:
        return JSONResponse(
            status_code=404,
            content={
                "code": "LIST_ITEM_NOT_FOUND",
                "detail": "No s'ha trobat l'element a la llista.",
            },
        )

    # Manual validation for PATCH keys
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_JSON",
                "detail": "El cos de la petició no és un JSON vàlid.",
            },
        )

    # Check for unauthorized fields in update payload
    invalid_keys = [k for k in payload.keys() if k != "quantity"]
    if invalid_keys:
        return JSONResponse(
            status_code=400,
            content={
                "code": "ONLY_QUANTITY_CAN_BE_UPDATED",
                "detail": "Només es pot actualitzar el camp quantitat.",
            },
        )

    if "quantity" not in payload:
        return JSONResponse(
            status_code=400,
            content={
                "code": "NO_FIELDS_TO_UPDATE",
                "detail": "No s'ha especificat cap camp per actualitzar.",
            },
        )

    quantity = payload.get("quantity")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_QUANTITY",
                "detail": "La quantitat ha de ser un enter superior a zero.",
            },
        )

    item.quantity = quantity
    item.updated_at = datetime.utcnow()
    home.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return JSONResponse(
        status_code=200,
        content={
            "code": "LIST_ITEM_UPDATED",
            "message": "Quantitat actualitzada correctament.",
            "data": {
                "id": str(item.id),
                "product_name": item.product_name,
                "quantity": item.quantity,
                "notes": item.notes,
            },
        },
    )


@router.delete("/{home_id}/{item_id}")
def delete_shopping_list_item(
    home_id: UUID,
    item_id: UUID,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _ = current

    # Verify home and membership
    home = (
        db.query(Home).filter(Home.id == home_id, Home.is_active.is_(True)).first()
    )
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "code": "HOME_NOT_FOUND",
                "detail": "La llar no existeix o ha estat dissolta.",
            },
        )

    membership = _verify_membership(home_id, user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "detail": "Accés denegat: L'usuari no pertany a aquesta llar activa.",
            },
        )

    # Find the item
    item = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.id == item_id, ShoppingListItem.home_id == home_id)
        .first()
    )

    if not item:
        return JSONResponse(
            status_code=404,
            content={
                "code": "LIST_ITEM_NOT_FOUND",
                "detail": "L'element no s'ha trobat.",
            },
        )

    db.delete(item)
    home.updated_at = datetime.utcnow()
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "code": "LIST_ITEM_DELETED",
            "message": "Producte eliminat de la llista de la compra.",
            "data": {
                "id": str(item_id),
            },
        },
    )
