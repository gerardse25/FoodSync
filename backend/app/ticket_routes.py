"""
app/ticket_routes.py

Router per al flux OCR de tickets (RF-ING-02, RF-ING-04).

Endpoints:
  POST /inventory/ticket/ocr     → processa imatge, retorna llista editable
  POST /inventory/ticket/confirm → confirma i guarda productes a inventari

Principis:
  - El router NO conté lògica OCR (delegada a ticket_ocr_service.py).
  - La confirmació reutilitza helpers ja existents d'inventory_routes.py.
  - Cap producte es persisteix fins a la confirmació explícita (RF-ING-04).
  - Errors amb format consistent amb la resta del projecte (code + error/missatge).
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.ticket_schemas as ticket_schemas
from app.database import get_db
from app.inventory_models import CatalogProduct, InventoryProduct, InventoryProductOwner
from app.inventory_routes import (
    _get_active_home,
    _get_active_membership,
    _get_or_create_category_row,
    _json_error,
    _normalize_product_name,
    _validate_owner_list,
    _validate_price_quantity,
)
from app.ticket_ocr_service import (
    ImageValidationError,
    process_ticket_image,
    validate_image,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory/ticket", tags=["inventory", "ticket"])


# ── POST /inventory/ticket/ocr ────────────────────────────────────────────────


@router.post("/ocr", response_model=None)
async def ocr_ticket(
    file: UploadFile,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    RF-ING-02: Rep una imatge de ticket, executa OCR i retorna
    una llista editable de productes detectats.

    NO persisteix res a la BD.
    """
    user, _session = current

    # 1. Usuari ha de pertànyer a una llar activa
    membership = _get_active_membership(user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "error": "Accés denegat: L'usuari no pertany a cap llar activa.",
            },
        )

    # 2. Llegir contingut i validar
    image_bytes = await file.read()
    content_type = file.content_type or ""

    try:
        validate_image(content_type=content_type, size=len(image_bytes))
    except ImageValidationError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "error": exc.message},
        )

    # 3. Processar imatge (OCR + enriquiment OFF)
    try:
        detected_items = process_ticket_image(image_bytes)
    except RuntimeError as exc:
        # Error d'inicialitzacio del motor (instal·lacio, models, etc.)
        return JSONResponse(
            status_code=500,
            content={"code": "OCR_ENGINE_ERROR", "error": str(exc)},
        )
    except Exception as exc:  # noqa: BLE001
        # Error durant l'execucio OCR (imatge corrupta, format inesperat)
        logger.exception("[ticket/ocr] Error durant OCR: %s", exc)
        return JSONResponse(
            status_code=422,
            content={
                "code": "OCR_PROCESSING_ERROR",
                "error": f"No s'ha pogut processar la imatge. Detall: {exc}",
            },
        )

    # 4. Construir OcrDetectedProduct per cada ítem detectat
    productes = []
    for item in detected_items:
        productes.append(
            ticket_schemas.OcrDetectedProduct(
                nom=item.get("nom"),
                marca=item.get("marca"),
                categoria=item.get("categoria"),
                categoria_label=item.get("categoria_label"),
                quantitat=item.get("quantitat"),
                preu=item.get("preu"),
                data_caducitat=item.get("data_caducitat"),
                data_compra=item.get("data_compra"),
                quantitat_envas=item.get("quantitat_envas"),
                nutriscore=item.get("nutriscore"),
                imatge_url=item.get("imatge_url"),
                id_propietaris_privats=item.get("id_propietaris_privats", []),
            )
        )

    if not productes:
        return ticket_schemas.OcrTicketResponse(
            code="OCR_NO_PRODUCTS",
            missatge=(
                "No s'han detectat productes al ticket. "
                "Comprova que la imatge sigui nítida i contigui línies de productes."
            ),
            productes=[],
        )

    return ticket_schemas.OcrTicketResponse(
        code="OCR_SUCCESS",
        missatge=f"S'han detectat {len(productes)} producte(s) al ticket.",
        productes=productes,
    )


# ── POST /inventory/ticket/confirm ───────────────────────────────────────────


@router.post("/confirm", response_model=None)
def confirm_ticket(
    data: ticket_schemas.ConfirmTicketRequest,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    RF-ING-04: Rep la llista de productes validats/editats pel frontend
    i els persisteix a l'inventari.

    Reutilitza helpers d'inventory_routes per no duplicar lògica.
    """
    user, _session = current

    # 1. Verificar llar activa
    membership = _get_active_membership(user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "error": "Accés denegat: L'usuari no pertany a cap llar activa.",
            },
        )

    home = _get_active_home(membership.home_id, db)
    if not home:
        return JSONResponse(
            status_code=404,
            content={
                "code": "HOME_NOT_FOUND",
                "error": "La llar de l'usuari no s'ha trobat o no és activa.",
            },
        )

    if not data.productes:
        return _json_error(
            "Cal proporcionar almenys un producte per confirmar.",
            422,
            "NO_PRODUCTS_PROVIDED",
        )

    # 2. Validar tots els productes abans de persistir cap
    validated_products = []
    for idx, prod_item in enumerate(data.productes):
        name, error = _normalize_product_name(prod_item.nom)
        if error:
            return error

        if prod_item.categoria is None:
            return _json_error(
                "La categoria és obligatòria.",
                422,
                "CATEGORY_REQUIRED",
            )

        validation_error = _validate_price_quantity(prod_item.preu, prod_item.quantitat)
        if validation_error:
            return validation_error

        owner_ids_normalized: list = []
        if prod_item.id_propietaris_privats:
            owner_ids_normalized, owner_error = _validate_owner_list(
                home.id,
                prod_item.id_propietaris_privats,
                db,
            )
            if owner_error:
                # Afegim context de quin producte ha fallat
                error_content = owner_error.body
                import json

                error_dict = json.loads(error_content)
                error_dict["producte_index"] = idx
                return JSONResponse(
                    status_code=owner_error.status_code,
                    content=error_dict,
                )

        validated_products.append(
            {
                "item": prod_item,
                "name": name,
                "owner_ids": owner_ids_normalized,
            }
        )

    # 3. Persistir productes
    guardats: list[ticket_schemas.ConfirmedProductItem] = []

    for validated_product in validated_products:
        prod_item = validated_product["item"]
        name = validated_product["name"]
        owner_ids_normalized = validated_product["owner_ids"]

        # Categoria → fila a BD
        category_row = _get_or_create_category_row(prod_item.categoria, db)

        # Buscar producte al catàleg per nom (sense codi de barres)
        catalog_product = (
            db.query(CatalogProduct).filter(CatalogProduct.nom == name).first()
        )

        if catalog_product is None:
            catalog_product = CatalogProduct(
                codi_barres=None,
                nom=name,
                marca=None,
                id_categoria=category_row.id_categoria,
                imatge_url=None,
            )
            db.add(catalog_product)
            db.flush()
        else:
            # Actualitzar categoria si estava absent
            if catalog_product.id_categoria is None:
                catalog_product.id_categoria = category_row.id_categoria

        # Determinar si és privat
        is_private = len(owner_ids_normalized) > 0

        # Crear InventoryProduct
        inv_product = InventoryProduct(
            id_llar=home.id,
            id_producte_cataleg=catalog_product.id_producte_cataleg,
            quantitat=prod_item.quantitat,
            data_caducitat=prod_item.data_caducitat,
            preu=prod_item.preu,
            data_compra=prod_item.data_compra,
            metode_registre="receipt",
            es_privat=is_private,
        )
        db.add(inv_product)
        db.flush()

        # Propietaris
        for owner_id in owner_ids_normalized:
            db.add(
                InventoryProductOwner(
                    id_inventari=inv_product.id_inventari,
                    user_id=owner_id,
                )
            )

        guardats.append(
            ticket_schemas.ConfirmedProductItem(
                id_producte=str(inv_product.id_inventari),
                id_producte_cataleg=str(catalog_product.id_producte_cataleg),
                nom=catalog_product.nom,
                quantitat=inv_product.quantitat,
                categoria=category_row.nom,
                preu=str(inv_product.preu) if inv_product.preu is not None else None,
                data_compra=inv_product.data_compra,
                data_caducitat=inv_product.data_caducitat,
                metode_registre=inv_product.metode_registre,
                owner_user_ids=[str(oid) for oid in owner_ids_normalized],
            )
        )

    home.updated_at = datetime.utcnow()
    db.commit()

    return ticket_schemas.ConfirmTicketResponse(
        code="TICKET_CONFIRMED",
        missatge=f"S'han guardat {len(guardats)} producte(s) a l'inventari.",
        productes_guardats=guardats,
    )
