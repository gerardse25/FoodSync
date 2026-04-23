from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.inventory_schemas as schemas
from app.database import get_db
from app.home_models import HomeMembership
from app.inventory_models import CatalogProduct, Category, InventoryProduct
from app.models import User
router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=schemas.InventoryResponseSchema)
def get_inventory(
    nom: Optional[str] = Query(None, description="Terme de cerca per filtrar l'inventari"),
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
            content={"code": "NOT_IN_HOME", "error": "Accés denegat: L'usuari no pertany a cap llar activa."},
        )

    home_id = membership.home_id

    query = (
        db.query(InventoryProduct, CatalogProduct, Category, User)
        .join(
            CatalogProduct,
            InventoryProduct.id_producte_cataleg == CatalogProduct.id_producte_cataleg,
        )
        .outerjoin(
            Category,
            CatalogProduct.id_categoria == Category.id_categoria,
        )
        .outerjoin(
            User,
            InventoryProduct.id_propietari_privat == User.id,
        )
        .filter(
            InventoryProduct.id_llar == home_id,
        )
    )

    if nom:
        nom = nom.strip()
        query = query.filter(CatalogProduct.nom.ilike(f"%{nom}%"))

    results = query.all()

    productes = []
    for inv_prod, cat_prod, category, owner in results:
        owner_data = None
        es_privat = False

        if inv_prod.id_propietari_privat:
            es_privat = True
            if owner:
                owner_data = schemas.ProductOwnerSchema(
                    id_usuari=str(owner.id),
                    nom=owner.username,
                )

        productes.append(
            schemas.InventoryProductSchema(
                id_producte=str(inv_prod.id_inventari),
                nom=cat_prod.nom,
                quantitat=inv_prod.quantitat,
                categoria=category.nom if category else "Sense categoria",
                data_caducitat=inv_prod.data_caducitat,
                es_privat=es_privat,
                propietari=owner_data,
            )
        )

    return schemas.InventoryResponseSchema(
        missatge="Inventari obtingut correctament",
        productes=productes,
    )
