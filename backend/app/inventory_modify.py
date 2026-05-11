from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.inventory_schemas as schemas
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.inventory_models import CatalogProduct, InventoryProduct, Category
from app.inventory_routes import (
    _get_owner_ids,
    _build_owner_schemas,
    _get_or_create_category_row,
    _normalize_product_name,
)

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


@router.patch("/{id_producte}", response_model=schemas.ModifyInventoryProductResponse)
def modify_product(
    id_producte: str,
    data: schemas.ModifyInventoryProductRequest,
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

    try:
        product_id_int = int(id_producte)
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
            InventoryProduct.id_inventari == product_id_int,
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

    update_data = data.model_dump(exclude_unset=True)

    if "preu" in update_data and update_data["preu"] is not None:
        if data.preu < 0:
            return JSONResponse(
                status_code=400,
                content={"code": "PRICE_INVALID", "error": "El preu no pot ser negatiu."},
            )
        if data.preu.as_tuple().exponent < -2:
            return JSONResponse(
                status_code=400,
                content={"code": "PRICE_INVALID", "error": "El preu no pot tenir més de 2 decimals."},
            )

    resolved_name = None
    if "nom" in update_data and update_data["nom"] is not None:
        name_val, name_err = _normalize_product_name(data.nom)
        if name_err:
            return name_err
        resolved_name = name_val

    old_catalog_product = (
        db.query(CatalogProduct)
        .filter(CatalogProduct.id_producte_cataleg == inv_product.id_producte_cataleg)
        .first()
    )

    requires_new_catalog = False
    new_name = old_catalog_product.nom
    new_category_id = old_catalog_product.id_categoria

    if resolved_name is not None and resolved_name != old_catalog_product.nom:
        requires_new_catalog = True
        new_name = resolved_name

    if "categoria" in update_data and update_data["categoria"] is not None:
        category_row = _get_or_create_category_row(data.categoria, db)
        if category_row.id_categoria != old_catalog_product.id_categoria:
            requires_new_catalog = True
            new_category_id = category_row.id_categoria

    if requires_new_catalog:
        new_catalog_product = CatalogProduct(
            codi_barres=None,
            nom=new_name,
            marca=old_catalog_product.marca,
            id_categoria=new_category_id,
            imatge_url=old_catalog_product.imatge_url,
            quantitat_envas=old_catalog_product.quantitat_envas,
            ingredients_text=old_catalog_product.ingredients_text,
            allergens_text=old_catalog_product.allergens_text,
            nutriscore_grade=old_catalog_product.nutriscore_grade,
            nutriments_per_100g=old_catalog_product.nutriments_per_100g,
        )
        db.add(new_catalog_product)
        db.flush()
        inv_product.id_producte_cataleg = new_catalog_product.id_producte_cataleg
        final_catalog_product = new_catalog_product
    else:
        final_catalog_product = old_catalog_product

    if "preu" in update_data:
        inv_product.preu = data.preu

    if "data_caducitat" in update_data:
        inv_product.data_caducitat = data.data_caducitat

    db.commit()
    db.refresh(inv_product)

    category = db.query(Category).filter(Category.id_categoria == final_catalog_product.id_categoria).first()

    owners_data = _build_owner_schemas(inv_product.id_inventari, db)
    es_privat = len(owners_data) > 0
    estat_stock = "En estoc" if inv_product.quantitat > 0 else "Exhaurit"

    nutricio = None
    if final_catalog_product.nutriments_per_100g:
        nutricio = schemas.InventoryNutritionSchema(**final_catalog_product.nutriments_per_100g)

    detail = schemas.InventoryProductDetailSchema(
        id_producte=str(inv_product.id_inventari),
        nom=final_catalog_product.nom,
        marca=final_catalog_product.marca,
        quantitat_stock=inv_product.quantitat,
        quantitat_envas=final_catalog_product.quantitat_envas,
        categoria=category.nom if category else None,
        data_caducitat=inv_product.data_caducitat,
        data_compra=inv_product.data_compra,
        preu=str(inv_product.preu) if inv_product.preu is not None else None,
        es_privat=es_privat,
        propietaris=owners_data,
        estat_stock=estat_stock,
        nutriscore=final_catalog_product.nutriscore_grade,
        informacio_nutricional_100g_ml=nutricio,
        ingredients=final_catalog_product.ingredients_text,
        allergens=final_catalog_product.allergens_text,
        imatge_url=final_catalog_product.imatge_url,
    )

    return schemas.ModifyInventoryProductResponse(
        code="PRODUCT_UPDATED",
        missatge="Producte modificat amb èxit.",
        producte=detail,
    )
