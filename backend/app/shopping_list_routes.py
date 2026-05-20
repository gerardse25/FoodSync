from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.shopping_list_schemas as schemas
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.inventory_models import CatalogProduct, InventoryProduct, InventoryProductOwner
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

    # Verify product_id
    try:
        product_id = int(data.product_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "code": "PRODUCT_ID_INVALID",
                "detail": "L'ID del producte ha de ser numèric.",
            },
        )

    catalog_product = (
        db.query(CatalogProduct)
        .filter(CatalogProduct.id_producte_cataleg == product_id)
        .first()
    )
    if not catalog_product:
        return JSONResponse(
            status_code=404,
            content={
                "code": "PRODUCT_NOT_FOUND",
                "detail": "El producte no existeix al catàleg.",
            },
        )

    # Check if product is already in the shopping list
    item = (
        db.query(ShoppingListItem)
        .filter(
            ShoppingListItem.home_id == home_id,
            ShoppingListItem.product_id == product_id,
        )
        .first()
    )

    is_new = False
    if item:
        item.quantity += data.quantity
        if data.notes is not None:
            item.notes = data.notes
        item.updated_at = datetime.utcnow()
    else:
        is_new = True
        item = ShoppingListItem(
            home_id=home_id,
            product_id=product_id,
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
                "product_id": str(item.product_id),
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
            "product_id": str(item.product_id),
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


@router.post(
    "/{home_id}/{inventory_item_id}",
    response_model=schemas.ConsumeInventoryItemResponse,
)
def consume_inventory_item(
    home_id: UUID,
    inventory_item_id: str,
    data: schemas.ConsumeInventoryItemRequest,
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

    try:
        inv_item_id = int(inventory_item_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVENTORY_ITEM_ID_INVALID",
                "detail": "L'ID de l'element d'inventari ha de ser numèric.",
            },
        )

    inv_product = (
        db.query(InventoryProduct)
        .filter(
            InventoryProduct.id_inventari == inv_item_id,
            InventoryProduct.id_llar == home_id,
        )
        .first()
    )

    if not inv_product:
        return JSONResponse(
            status_code=404,
            content={
                "code": "INVENTORY_PRODUCT_NOT_FOUND",
                "detail": "Producte d'inventari no trobat.",
            },
        )

    # Check owner privileges if the product is private
    owner_ids = [
        r.user_id
        for r in db.query(InventoryProductOwner)
        .filter(InventoryProductOwner.id_inventari == inv_product.id_inventari)
        .all()
    ]

    if owner_ids and user.id not in owner_ids:
        return JSONResponse(
            status_code=403,
            content={
                "code": "PRODUCT_MODIFICATION_FORBIDDEN",
                "detail": "No tens permís per modificar aquest producte perquè és privat d'un altre membre.",
            },
        )

    # 1. Update/Delete from inventory
    new_quantity = inv_product.quantitat - data.quantity_consumed
    if new_quantity <= 0:
        db.delete(inv_product)
        inventory_status = "deleted"
    else:
        inv_product.quantitat = new_quantity
        inventory_status = "updated"

    # 2. Add to shopping list if add_to_shopping_list is True
    shopping_item_data = None
    if data.add_to_shopping_list:
        product_id = inv_product.id_producte_cataleg
        # Check if already in shopping list
        sl_item = (
            db.query(ShoppingListItem)
            .filter(
                ShoppingListItem.home_id == home_id,
                ShoppingListItem.product_id == product_id,
            )
            .first()
        )

        sl_qty = (
            data.shopping_list_quantity
            if data.shopping_list_quantity is not None
            else 1
        )

        is_new = False
        if sl_item:
            sl_item.quantity += sl_qty
            sl_item.updated_at = datetime.utcnow()
        else:
            is_new = True
            sl_item = ShoppingListItem(
                home_id=home_id, product_id=product_id, quantity=sl_qty
            )
            db.add(sl_item)

        db.flush()  # get sl_item.id if new
        shopping_item_data = {
            "item_id": str(sl_item.id),
            "product_id": str(sl_item.product_id),
            "quantity": sl_item.quantity,
            "is_new": is_new,
        }

    # 3. Sychronization / Notification updates
    home.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Inventari actualitzat correctament.",
        "data": {
            "inventory_status": inventory_status,
            "shopping_list_item": shopping_item_data,
        },
    }
