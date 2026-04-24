from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.inventory_schemas as schemas
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.inventory_models import InventoryProduct
from app.inventory_routes import _get_owner_ids

router = APIRouter(prefix="/inventory_delete_product", tags=["inventory"])


@router.delete("", response_model=schemas.DeleteProductResponse)
def delete_product(
    data: schemas.DeleteProductRequest,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, session = current

    membership = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user.id,
            HomeMembership.is_active.is_(True),
        )
        .first()
    )

    if not membership:
        return JSONResponse(
            status_code=404,
            content={
                "code": "NOT_IN_HOME",
                "error": "Accés denegat: L'usuari no pertany a cap llar activa.",
            },
        )

    home_id = membership.home_id
    home = db.query(Home).filter(Home.id == home_id, Home.is_active.is_(True)).first()

    try:
        product_id = int(data.id_producte)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "code": "PRODUCT_ID_INVALID",
                "detail": "L'ID del producte ha de ser numèric.",
            },
        )

    inv_product = (
        db.query(InventoryProduct)
        .filter(
            InventoryProduct.id_inventari == product_id,
            InventoryProduct.id_llar == home_id,
        )
        .first()
    )

    if not inv_product:
        return JSONResponse(
            status_code=404,
            content={
                "code": "PRODUCT_NOT_FOUND",
                "error": "El producte no s'ha trobat.",
            },
        )

    owner_ids = _get_owner_ids(inv_product.id_inventari, db)

    if owner_ids and user.id not in owner_ids:
        return JSONResponse(
            status_code=403,
            content={
                "code": "PRODUCT_DELETE_FORBIDDEN",
                "error": "No tens permís per eliminar aquest producte "
                "perquè és privat d'un altre membre.",
            },
        )

    db.delete(inv_product)

    if home:
        home.updated_at = datetime.utcnow()

    db.commit()

    return schemas.DeleteProductResponse(
        code="PRODUCT_DELETED",
        missatge="El producte s'ha eliminat completament de l'inventari.",
    )
