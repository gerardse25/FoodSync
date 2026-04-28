from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.inventory_schemas as schemas
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.inventory_models import CatalogProduct, InventoryProduct
from app.inventory_routes import _get_owner_ids

router = APIRouter(prefix="/inventory_modify", tags=["inventory"])


@router.patch("", response_model=schemas.ConsumeProductResponse)
def consume_product(
    data: schemas.ConsumeProductRequest,
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
            status_code=403,
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
                "detail": "Producte no trobat a l'inventari de la llar.",
            },
        )

    owner_ids = _get_owner_ids(inv_product.id_inventari, db)

    if owner_ids and user.id not in owner_ids:
        return JSONResponse(
            status_code=403,
            content={
                "code": "PRODUCT_MODIFICATION_FORBIDDEN",
                "error": "No tens permís per modificar aquest producte "
                "perquè és privat d'un altre membre.",
            },
        )

    if inv_product.quantitat == 0 and data.modificacio < 0:
        return JSONResponse(
            status_code=400,
            content={
                "code": "PRODUCT_OUT_OF_STOCK",
                "error": "El producte ja està esgotat (quantitat 0).",
            },
        )
    elif inv_product.quantitat + data.modificacio < 0:
        return JSONResponse(
            status_code=400,
            content={
                "code": "PRODUCT_INSUFFICIENT_STOCK",
                "error": "No pots consumir més unitats de les que hi ha disponibles.",
            },
        )
    elif inv_product.quantitat + data.modificacio > 99:
        return JSONResponse(
            status_code=400,
            content={
                "code": "QUANTITY_TOO_HIGH",
                "error": "La quantitat màxima permesa és 99.",
            },
        )

    inv_product.quantitat += data.modificacio

    if home:
        home.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(inv_product)

    catalog_product = (
        db.query(CatalogProduct)
        .filter(CatalogProduct.id_producte_cataleg == inv_product.id_producte_cataleg)
        .first()
    )
    nom_producte = catalog_product.nom if catalog_product else "Desconegut"

    mod = data.modificacio
    if mod < 0:
        abs_mod = abs(mod)
        if abs_mod == 1:
            msg = "S'ha consumit 1 unitat del producte"
        else:
            msg = f"S'han consumit {abs_mod} unitats del producte"
    elif mod > 0:
        if mod == 1:
            msg = "S'ha afegit 1 unitat del producte"
        else:
            msg = f"S'han afegit {mod} unitats del producte"
    else:
        msg = "La quantitat no s'ha modificat"

    return schemas.ConsumeProductResponse(
        code="PRODUCT_QUANTITY_UPDATED",
        missatge=msg,
        producte=schemas.ConsumeProductResponseItem(
            id_producte=str(inv_product.id_inventari),
            nom=nom_producte,
            quantitat_restant=inv_product.quantitat,
        ),
    )
