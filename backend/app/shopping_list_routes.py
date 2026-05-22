from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

import app.auth
import app.shopping_list_schemas as schemas
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.shopping_list_models import ShoppingListItem

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])


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
            schemas.ShoppingListProductDetails(
                item_id=item.id,
                product_name=item.product_name,
                quantity=item.quantity,
                notes=item.notes,
            ).model_dump(mode="json")
        )

    return JSONResponse(
        status_code=200,
        content={
            "code": "SHOPPING_LIST_RETRIEVED",
            "message": "Llista de la compra obtinguda correctament.",
            "items": items_data,
        },
    )


@router.post("/{home_id}", response_model=schemas.AddShoppingListItemResponse)
def add_shopping_list_item(
    home_id: UUID,
    data: schemas.AddShoppingListItemRequest,
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

    # Check if product name is already in the shopping list (case-insensitive)
    item = (
        db.query(ShoppingListItem)
        .filter(
            ShoppingListItem.home_id == home_id,
            func.lower(ShoppingListItem.product_name) == func.lower(data.product_name),
        )
        .first()
    )

    is_new = False
    if item:
        item.quantity += data.quantity
        # Optional: update casing if a different one is provided
        item.product_name = data.product_name
        if data.notes is not None:
            item.notes = data.notes
        item.updated_at = datetime.utcnow()
    else:
        is_new = True
        item = ShoppingListItem(
            home_id=home_id,
            product_name=data.product_name,
            quantity=data.quantity,
            notes=data.notes,
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
            "message": "Producte afegit a la llista de la compra",
            "data": {
                "item_id": str(item.id),
                "product_name": item.product_name,
                "quantity": item.quantity,
                "is_new": is_new,
            },
        },
    )


@router.patch("/{home_id}/{item_id}")
def update_shopping_list_item(
    home_id: UUID,
    item_id: UUID,
    data: schemas.UpdateShoppingListItemRequest,
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
                "code": "ITEM_NOT_FOUND",
                "detail": "No s'ha trobat l'element a la llista.",
            },
        )

    if data.quantity <= 0:
        db.delete(item)
        home.updated_at = datetime.utcnow()
        db.commit()
        return JSONResponse(
            status_code=200,
            content={
                "code": "ITEM_DELETED",
                "message": "L'element s'ha eliminat de la llista de la compra perquè la quantitat és zero o menor.",
            },
        )

    item.quantity = data.quantity
    item.updated_at = datetime.utcnow()
    home.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return {
        "code": "ITEM_QUANTITY_UPDATED",
        "message": "Quantitat actualitzada correctament.",
        "data": {
            "item_id": str(item.id),
            "product_name": item.product_name,
            "quantity": item.quantity,
        },
    }


@router.delete("/{home_id}/{item_id}", status_code=204)
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
                "code": "ITEM_NOT_FOUND",
                "detail": "L'element no s'ha trobat.",
            },
        )

    db.delete(item)
    home.updated_at = datetime.utcnow()
    db.commit()
    return Response(status_code=204)
