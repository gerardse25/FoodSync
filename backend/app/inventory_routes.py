from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
import app.inventory_schemas as schemas
from app.barcode_service import is_valid_barcode, lookup_barcode_enriched
from app.database import get_db
from app.home_models import Home, HomeMembership
from app.inventory_models import (
    CatalogProduct,
    Category,
    InventoryProduct,
    InventoryProductOwner,
)
from app.models import User
from app.product_schemas import CATEGORY_LABELS_CA, ProductCategory
from app.validation import contains_control_characters, contains_escape_sequences
from app.inventory_service import InventoryFilterParams, get_filtered_products

router = APIRouter(prefix="/inventory", tags=["inventory"])

LABEL_TO_CATEGORY_VALUE = {
    label: category.value for category, label in CATEGORY_LABELS_CA.items()
}


def _json_error(detail: str, status_code: int = 400, code: Optional[str] = None):
    payload = {"error": detail}
    if code:
        payload["code"] = code
    return JSONResponse(status_code=status_code, content=payload)


def _get_active_membership(user_id, db: Session):
    return (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user_id,
            HomeMembership.is_active.is_(True),
        )
        .first()
    )


def _get_active_home(home_id, db: Session):
    return (
        db.query(Home)
        .filter(
            Home.id == home_id,
            Home.is_active.is_(True),
        )
        .first()
    )


def _normalize_product_name(value: str | None):
    raw = value if value is not None else ""

    if contains_control_characters(raw) or contains_escape_sequences(raw):
        return None, _json_error(
            "El camp nom conté caràcters no permesos.", 400, "NAME_INVALID_CHARACTERS"
        )

    trimmed = raw.strip()

    if not trimmed:
        return None, _json_error("El camp nom és obligatori.", 422, "NAME_REQUIRED")

    if len(trimmed) > 100:
        return None, _json_error("El camp nom és massa llarg.", 422, "NAME_TOO_LONG")

    return trimmed, None


def _validate_price_quantity(price, quantity):
    if price is None:
        return _json_error("El preu és obligatori.", 422, "PRICE_REQUIRED")

    if quantity is None:
        return _json_error("La quantitat és obligatòria.", 422, "QUANTITY_REQUIRED")

    if price < 0:
        return _json_error("El preu no pot ser negatiu.", 422, "PRICE_INVALID")

    if price != round(price, 2):
        return _json_error(
            "El preu no pot tenir més de 2 decimals.", 422, "PRICE_INVALID"
        )

    if quantity <= 0:
        return _json_error(
            "La quantitat ha de ser superior a 0.", 422, "QUANTITY_INVALID"
        )

    if quantity > 99:
        return _json_error(
            "La quantitat màxima permesa és 99.", 422, "QUANTITY_TOO_HIGH"
        )

    return None


def _validate_owner(home_id, owner_user_id, db: Session):
    if owner_user_id is None:
        return None

    owner_membership = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.home_id == home_id,
            HomeMembership.user_id == owner_user_id,
            HomeMembership.is_active.is_(True),
        )
        .first()
    )

    if not owner_membership:
        return _json_error(
            "El propietari indicat no pertany a la llar.",
            400,
            "OWNER_NOT_IN_HOME",
        )

    return None


def _get_or_create_category_row(
    category_enum: ProductCategory, db: Session
) -> Category:
    label = CATEGORY_LABELS_CA[category_enum]

    category_row = db.query(Category).filter(Category.nom == label).first()
    if category_row:
        return category_row

    category_row = Category(nom=label)
    db.add(category_row)
    db.flush()
    return category_row


def _apply_off_snapshot_to_catalog_product(
    catalog_product: CatalogProduct, off_data: dict
) -> None:
    if not catalog_product.marca:
        catalog_product.marca = off_data.get("brand")

    if not catalog_product.imatge_url:
        catalog_product.imatge_url = off_data.get("image_url")

    if not catalog_product.quantitat_envas:
        catalog_product.quantitat_envas = off_data.get("package_quantity_label")

    if not catalog_product.ingredients_text:
        catalog_product.ingredients_text = off_data.get("ingredients_text")

    if not catalog_product.allergens_text:
        catalog_product.allergens_text = off_data.get("allergens_text")

    if not catalog_product.nutriscore_grade:
        catalog_product.nutriscore_grade = off_data.get("nutriscore_grade")

    if not catalog_product.nutriments_per_100g:
        catalog_product.nutriments_per_100g = off_data.get("nutriments_per_100g")

    catalog_product.off_last_synced_at = datetime.utcnow()

@router.get("", response_model=None)
def get_inventory(
    search: Optional[str] = Query(
        None, description="Cerca parcial per nom (case-insensitive). Àlies: nom"
    ),
    nom: Optional[str] = Query(None, include_in_schema=False),  # àlies legacy
    categoria: Optional[str] = Query(None, description="Filtre exacte per categoria"),
    min_quantity: Optional[int] = Query(
        None, ge=0, description="Quantitat mínima (inclusiva)"
    ),
    max_quantity: Optional[int] = Query(
        None, ge=0, description="Quantitat màxima (inclusiva)"
    ),
    owner_user_id: Optional[str] = Query(
        None, description="Filtre per UUID de propietari"
    ),
    nutrition_score: Optional[str] = Query(
        None, description="[Futur] Nutriscore (A-E). Acceptat, ignorat."
    ),
    expiry_filter: Optional[str] = Query(
        None, description="[Futur] expired|expiring_soon|ok. Acceptat, ignorat."
    ),
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "error": "Accés denegat: L'usuari no pertany a cap llar activa.",
            },
        )

    # Validació owner_user_id
    if owner_user_id is not None:
        try:
            UUID(owner_user_id)
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=400,
                content={
                    "code": "INVALID_USER_ID",
                    "error": "owner_user_id ha de ser un UUID vàlid.",
                },
            )

    # Validació rang quantitat
    if (
        min_quantity is not None
        and max_quantity is not None
        and min_quantity > max_quantity
    ):
        return JSONResponse(
            status_code=400,
            content={
                "code": "QUANTITY_RANGE_INVALID",
                "error": "min_quantity no pot ser superior a max_quantity.",
            },
        )

    # Compatibilitat amb el paràmetre legacy `nom`
    effective_search = search or nom

    filters = InventoryFilterParams(
        search=effective_search,
        categoria=categoria,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        owner_user_id=owner_user_id,
        nutrition_score=nutrition_score,
        expiry_filter=expiry_filter,
    )

    results = get_filtered_products(db, membership.home_id, filters)

    productes = []
    for inv_prod, cat_prod, category in results:
        owners_data = _build_owner_schemas(inv_prod.id_inventari, db)
        productes.append(
            schemas.InventoryProductSchema(
                id_producte=str(inv_prod.id_inventari),
                nom=cat_prod.nom,
                quantitat=inv_prod.quantitat,
                categoria=category.nom if category else "Sense categoria",
                data_caducitat=inv_prod.data_caducitat,
                es_privat=len(owners_data) > 0,
                propietaris=owners_data,
            )
        )

    return JSONResponse(
        status_code=200,
        content={
            "code": "INVENTORY_RETRIEVED",
            "missatge": "Inventari obtingut correctament",
            "productes": [p.model_dump(mode="json") for p in productes],
        },
    )


@router.get("/categories/all")
def get_all_inventory_categories():
    return {
        "code": "ALL_CATEGORIES_RETRIEVED",
        "missatge": "Categories completes obtingudes correctament",
        "categories": [
            {"value": category.value, "label": CATEGORY_LABELS_CA[category]}
            for category in ProductCategory
        ],
    }


@router.get("/categories")
def get_inventory_categories(
    q: Optional[str] = Query(None, description="Text per cercar categories"),
    db: Session = Depends(get_db),
):
    query = db.query(Category).order_by(Category.nom.asc())

    if q:
        query = query.filter(Category.nom.ilike(f"%{q}%"))

    categories = query.all()

    return {
        "missatge": "Categories obtingudes correctament",
        "categories": [{"id": c.id_categoria, "nom": c.nom} for c in categories],
    }

# @router.get("/products")
# def get_filtered_inventory(
#     search: Optional[str] = Query(
#         None, description="Cerca parcial per nom del producte (case-insensitive)"
#     ),
#     categoria: Optional[str] = Query(
#         None, description="Filtre exacte per nom de categoria"
#     ),
#     min_quantity: Optional[int] = Query(
#         None, ge=0, description="Quantitat mínima (inclusiva)"
#     ),
#     max_quantity: Optional[int] = Query(
#         None, ge=0, description="Quantitat màxima (inclusiva)"
#     ),
#     owner_user_id: Optional[str] = Query(
#         None,
#         description="Filtre per usuari propietari del producte (UUID en format string)",
#     ),
#     nutrition_score: Optional[str] = Query(
#         None, description="[Futur] Filtre per nutriscore (A-E). Acceptat però ignorat."
#     ),
#     expiry_filter: Optional[str] = Query(
#         None,
#         description=(
#             "[Futur] Filtre per caducitat: expired | expiring_soon | ok. "
#             "Acceptat però ignorat."
#         ),
#     ),
#     current=Depends(app.auth.get_current_user),
#     db: Session = Depends(get_db),
# ):
#     """
#     RF-INV-02: Cerca i filtrat de productes de l'inventari.
 
#     Filtres actius (combinables amb AND):
#       - search: coincidència parcial al nom (case-insensitive)
#       - categoria: filtre exacte per nom de categoria
#       - min_quantity / max_quantity: rang de quantitat
 
#     Filtres preparats per a futures iteracions (acceptats, ignorats ara):
#       - nutrition_score: filtre per nutriscore (A, B, C, D, E)
#       - expiry_filter: filtre per caducitat (expired, expiring_soon, ok)
 
#     Si no s'especifica cap filtre, retorna tots els productes de la llar.
#     """
#     user, _session = current

#     membership = _get_active_membership(user.id, db)

#     if not membership:
#         return JSONResponse(
#             status_code=403,
#             content={
#                 "code": "NOT_IN_HOME",
#                 "error": "Accés denegat: L'usuari no pertany a cap llar activa.",
#             },
#         )
 
#      # Validació UUID owner_user_id
#     if owner_user_id is not None:
#         try:
#             UUID(owner_user_id)
#         except (ValueError, TypeError):
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "code": "INVALID_USER_ID",
#                     "error": "owner_user_id ha de ser un UUID vàlid.",
#                 },
#             )

#     # Validació de rang de quantitat
#     if (
#         min_quantity is not None
#         and max_quantity is not None
#         and min_quantity > max_quantity
#     ):
#         return JSONResponse(
#             status_code=400,
#             content={
#                 "code": "QUANTITY_RANGE_INVALID",
#                 "error": (
#                     "min_quantity no pot ser superior a max_quantity."
#                 ),
#             },
#         )
    
 
#     home_id = membership.home_id
 
#     filters = InventoryFilterParams(
#         search=search,
#         categoria=categoria,
#         min_quantity=min_quantity,
#         max_quantity=max_quantity,
#         owner_user_id=owner_user_id,
#         nutrition_score=nutrition_score,
#         expiry_filter=expiry_filter,
#     )
 
#     results = get_filtered_products(db, home_id, filters)
 
#     productes = []
#     for inv_prod, cat_prod, category in results:
#         owners_data = _build_owner_schemas(inv_prod.id_inventari, db)
#         es_privat = len(owners_data) > 0
 
#         productes.append(
#             schemas.InventoryProductSchema(
#                 id_producte=str(inv_prod.id_inventari),
#                 nom=cat_prod.nom,
#                 quantitat=inv_prod.quantitat,
#                 categoria=category.nom if category else "Sense categoria",
#                 data_caducitat=inv_prod.data_caducitat,
#                 es_privat=es_privat,
#                 propietaris=owners_data,
#             )
#         )
 
#     return JSONResponse(
#         status_code=200,
#         content={
#             "code": "PRODUCTS_FETCHED",
#             "products": [p.model_dump(mode="json") for p in productes],
#         },
#     )

@router.get(
    "/{id_producte}", response_model=schemas.InventoryProductDetailResponseSchema
)
def get_inventory_product_detail(
    id_producte: int,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return JSONResponse(
            status_code=403,
            content={
                "code": "NOT_IN_HOME",
                "error": "Accés denegat: L'usuari no pertany a cap llar activa.",
            },
        )

    home_id = membership.home_id

    result = (
        db.query(InventoryProduct, CatalogProduct, Category)
        .join(
            CatalogProduct,
            InventoryProduct.id_producte_cataleg == CatalogProduct.id_producte_cataleg,
        )
        .outerjoin(
            Category,
            CatalogProduct.id_categoria == Category.id_categoria,
        )
        .filter(
            InventoryProduct.id_inventari == id_producte,
            InventoryProduct.id_llar == home_id,
        )
        .first()
    )

    if not result:
        return _json_error("El producte no s'ha trobat.", 404)

    inv_prod, cat_prod, category = result

    owners_data = _build_owner_schemas(inv_prod.id_inventari, db)
    es_privat = len(owners_data) > 0

    estat_stock = "En estoc" if inv_prod.quantitat > 0 else "Exhaurit"

    nutricio = None
    if cat_prod.nutriments_per_100g:
        nutricio = schemas.InventoryNutritionSchema(**cat_prod.nutriments_per_100g)

    detail = schemas.InventoryProductDetailSchema(
        id_producte=str(inv_prod.id_inventari),
        nom=cat_prod.nom,
        marca=cat_prod.marca,
        quantitat_stock=inv_prod.quantitat,
        quantitat_envas=cat_prod.quantitat_envas,
        categoria=category.nom if category else None,
        data_caducitat=inv_prod.data_caducitat,
        data_compra=inv_prod.data_compra,
        preu=str(inv_prod.preu) if inv_prod.preu is not None else None,
        es_privat=es_privat,
        propietaris=owners_data,
        estat_stock=estat_stock,
        nutriscore=cat_prod.nutriscore_grade,
        informacio_nutricional_100g_ml=nutricio,
        ingredients=cat_prod.ingredients_text,
        allergens=cat_prod.allergens_text,
        imatge_url=cat_prod.imatge_url,
    )

    return schemas.InventoryProductDetailResponseSchema(
        missatge="Detall del producte obtingut correctament",
        producte=detail,
    )


@router.post(
    "/manual", response_model=schemas.CreateInventoryProductResponse, status_code=201
)
def create_inventory_product_manual(
    data: schemas.CreateInventoryManualProductRequest,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return _json_error("No pertanys a cap llar.", 404, "NOT_IN_HOME")

    home = _get_active_home(membership.home_id, db)
    if not home:
        return _json_error(
            "La llar no existeix o ha estat dissolta.", 404, "HOME_NOT_FOUND"
        )

    name, error = _normalize_product_name(data.nom)
    if error:
        return error

    if data.categoria is None:
        return _json_error("La categoria és obligatòria.", 422, "CATEGORY_REQUIRED")

    validation_error = _validate_price_quantity(data.preu, data.quantitat)
    if validation_error:
        return validation_error

    owner_ids, owner_error = _validate_owner_list(
        home.id, data.id_propietaris_privats, db
    )
    if owner_error:
        return owner_error

    category_row = _get_or_create_category_row(data.categoria, db)

    catalog_product = CatalogProduct(
        codi_barres=None,
        nom=name,
        marca=None,
        id_categoria=category_row.id_categoria,
        imatge_url=None,
    )
    db.add(catalog_product)
    db.flush()

    inventory_product = InventoryProduct(
        id_llar=home.id,
        id_producte_cataleg=catalog_product.id_producte_cataleg,
        quantitat=data.quantitat,
        data_caducitat=data.data_caducitat,
        preu=data.preu,
        data_compra=data.data_compra,
        metode_registre="manual",
    )
    db.add(inventory_product)
    db.flush()

    for owner_id in owner_ids:
        db.add(
            InventoryProductOwner(
                id_inventari=inventory_product.id_inventari,
                user_id=owner_id,
            )
        )

    home.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(inventory_product)

    return schemas.CreateInventoryProductResponse(
        code="PRODUCT_CREATED",
        missatge="Producte manual afegit correctament a l'inventari.",
        producte=schemas.CreateInventoryProductResponseItem(
            id_producte=str(inventory_product.id_inventari),
            id_producte_cataleg=str(catalog_product.id_producte_cataleg),
            nom=catalog_product.nom,
            quantitat=inventory_product.quantitat,
            categoria=category_row.nom,
            preu=(
                str(inventory_product.preu)
                if inventory_product.preu is not None
                else None
            ),
            data_compra=inventory_product.data_compra,
            data_caducitat=inventory_product.data_caducitat,
            codi_barres=catalog_product.codi_barres,
            metode_registre=inventory_product.metode_registre,
        ),
    )



@router.get("/barcode/{barcode}", response_model=schemas.BarcodeLookupResponseSchema)
def lookup_inventory_product_by_barcode(
    barcode: str,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return _json_error("No pertanys a cap llar.", 404, "NOT_IN_HOME")

    barcode = barcode.strip()
    if not is_valid_barcode(barcode):
        return _json_error(
            "El codi de barres ha de contenir entre 8 i 14 dígits numèrics.",
            400,
            "BARCODE_INVALID_FORMAT",
        )

    # 1) Primer consultem el catàleg local
    local_result = (
        db.query(CatalogProduct, Category)
        .outerjoin(Category, CatalogProduct.id_categoria == Category.id_categoria)
        .filter(CatalogProduct.codi_barres == barcode)
        .first()
    )

    if local_result:
        catalog_product, category = local_result

        category_value = None
        if category:
            category_value = LABEL_TO_CATEGORY_VALUE.get(category.nom)

        return schemas.BarcodeLookupResponseSchema(
            found=True,
            barcode=barcode,
            source="local_catalog",
            code="BARCODE_FOUND_LOCAL",
            product=schemas.BarcodeLookupProductSchema(
                nom=catalog_product.nom,
                categoria=category_value,
                marca=catalog_product.marca,
                quantitat_envas=catalog_product.quantitat_envas,
                nutriscore=catalog_product.nutriscore_grade,
                imatge_url=catalog_product.imatge_url,
            ),
        )

    # 2) Si no hi és, consultem OFF
    result = lookup_barcode_enriched(barcode)

    if result is None:
        return _json_error(
            "El servei de codi de barres no està disponible.",
            503,
            "BARCODE_SERVICE_UNAVAILABLE",
        )

    if not result.get("found"):
        return schemas.BarcodeLookupResponseSchema(
            found=False,
            barcode=barcode,
            source="open_food_facts",
            code="BARCODE_NOT_FOUND",
            message="Producte no trobat. Pots afegir-lo manualment.",
            product=None,
        )

    return schemas.BarcodeLookupResponseSchema(
        found=True,
        barcode=barcode,
        source="open_food_facts",
        code="BARCODE_FOUND_OFF",
        product=schemas.BarcodeLookupProductSchema(
            nom=result.get("name"),
            categoria=result.get("category"),
            marca=result.get("brand"),
            quantitat_envas=result.get("package_quantity_label"),
            nutriscore=result.get("nutriscore_grade"),
            imatge_url=result.get("image_url"),
        ),
    )


@router.post(
    "/barcode/confirm",
    response_model=schemas.CreateInventoryProductResponse,
    status_code=201,
)
def confirm_and_add_barcode_product(
    data: schemas.ConfirmBarcodeProductRequest,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return _json_error("No pertanys a cap llar.", 404, "NOT_IN_HOME")

    home = _get_active_home(membership.home_id, db)
    if not home:
        return _json_error(
            "La llar no existeix o ha estat dissolta.", 404, "HOME_NOT_FOUND"
        )

    barcode = data.barcode.strip()
    if not is_valid_barcode(barcode):
        return _json_error(
            "El codi de barres ha de contenir entre 8 i 14 dígits numèrics.",
            400,
            "BARCODE_INVALID_FORMAT",
        )

    validation_error = _validate_price_quantity(data.preu, data.quantitat)
    if validation_error:
        return validation_error

    owner_ids, owner_error = _validate_owner_list(
        home.id, data.id_propietaris_privats, db
    )
    if owner_error:
        return owner_error

    catalog_product = (
        db.query(CatalogProduct).filter(CatalogProduct.codi_barres == barcode).first()
    )

    off_data = None
    if catalog_product is None or catalog_product.off_last_synced_at is None:
        off_data = lookup_barcode_enriched(barcode)

    resolved_name = None

    if data.nom is not None and data.nom.strip():
        resolved_name, error = _normalize_product_name(data.nom)
        if error:
            return error
    elif catalog_product is not None and catalog_product.nom:
        resolved_name = catalog_product.nom
    elif off_data and off_data.get("found") and off_data.get("name"):
        resolved_name, error = _normalize_product_name(off_data.get("name"))
        if error:
            return error

    if not resolved_name:
        return _json_error(
            "No s'ha pogut determinar el nom del producte. Revisa'l manualment.",
            422,
            "NAME_REQUIRED",
        )

    resolved_category = None

    if data.categoria is not None:
        resolved_category = data.categoria
    else:
        if catalog_product is not None and catalog_product.id_categoria is not None:
            category_row_existing = (
                db.query(Category)
                .filter(Category.id_categoria == catalog_product.id_categoria)
                .first()
            )
            if category_row_existing:
                for enum_value, label in CATEGORY_LABELS_CA.items():
                    if label == category_row_existing.nom:
                        resolved_category = enum_value
                        break

        if (
            resolved_category is None
            and off_data
            and off_data.get("found")
            and off_data.get("category")
        ):
            off_category_value = off_data.get("category")
            try:
                resolved_category = ProductCategory(off_category_value)
            except ValueError:
                resolved_category = None

    if resolved_category is None:
        return _json_error(
            "No s'ha pogut determinar la categoria del producte. Revisa-la manualment.",
            422,
            "CATEGORY_REQUIRED",
        )

    category_row = _get_or_create_category_row(resolved_category, db)

    is_new_catalog_product = False

    if catalog_product is None:
        catalog_product = CatalogProduct(
            codi_barres=barcode,
            nom=resolved_name,
            marca=None,
            id_categoria=category_row.id_categoria,
            imatge_url=None,
        )
        db.add(catalog_product)
        db.flush()
        is_new_catalog_product = True

    if is_new_catalog_product or not catalog_product.nom:
        catalog_product.nom = resolved_name

    if is_new_catalog_product or catalog_product.id_categoria is None:
        catalog_product.id_categoria = category_row.id_categoria

    if off_data and off_data.get("found"):
        _apply_off_snapshot_to_catalog_product(catalog_product, off_data)

    inventory_product = InventoryProduct(
        id_llar=home.id,
        id_producte_cataleg=catalog_product.id_producte_cataleg,
        quantitat=data.quantitat,
        data_caducitat=data.data_caducitat,
        preu=data.preu,
        data_compra=data.data_compra,
        metode_registre="barcode",
    )
    db.add(inventory_product)
    db.flush()

    for owner_id in owner_ids:
        db.add(
            InventoryProductOwner(
                id_inventari=inventory_product.id_inventari,
                user_id=owner_id,
            )
        )

    home.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(inventory_product)

    return schemas.CreateInventoryProductResponse(
        code="PRODUCT_CREATED",
        missatge="Producte amb codi de barres afegit correctament a l'inventari.",
        producte=schemas.CreateInventoryProductResponseItem(
            id_producte=str(inventory_product.id_inventari),
            id_producte_cataleg=str(catalog_product.id_producte_cataleg),
            nom=catalog_product.nom,
            quantitat=inventory_product.quantitat,
            categoria=category_row.nom,
            preu=(
                str(inventory_product.preu)
                if inventory_product.preu is not None
                else None
            ),
            data_compra=inventory_product.data_compra,
            data_caducitat=inventory_product.data_caducitat,
            codi_barres=catalog_product.codi_barres,
            metode_registre=inventory_product.metode_registre,
        ),
    )


@router.patch("/owners", response_model=schemas.UpdateProductOwnersResponse)
def update_product_owners(
    data: schemas.UpdateProductOwnersRequest,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    membership = _get_active_membership(user.id, db)
    if not membership:
        return _json_error("No pertanys a cap llar.", 404, "NOT_IN_HOME")

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
            InventoryProduct.id_llar == membership.home_id,
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

    current_owner_ids = _get_owner_ids(product_id, db)

    # Regla:
    # - si és compartit (0 owners), qualsevol membre de la llar pot canviar owners
    # - si és privat (>0 owners), només un owner actual pot canviar owners
    if current_owner_ids and user.id not in current_owner_ids:
        return JSONResponse(
            status_code=403,
            content={
                "code": "PRODUCT_OWNERSHIP_FORBIDDEN",
                "error": "No tens permís per modificar la propietat d'aquest producte.",
            },
        )

    new_owner_ids, owner_error = _validate_owner_list(
        membership.home_id,
        data.owner_user_ids,
        db,
    )
    if owner_error:
        return owner_error

    (
        db.query(InventoryProductOwner)
        .filter(InventoryProductOwner.id_inventari == product_id)
        .delete()
    )

    for owner_id in new_owner_ids:
        db.add(
            InventoryProductOwner(
                id_inventari=product_id,
                user_id=owner_id,
            )
        )

    db.commit()

    owners_data = _build_owner_schemas(product_id, db)

    return schemas.UpdateProductOwnersResponse(
        code="PRODUCT_OWNERS_UPDATED",
        missatge="La propietat del producte s'ha actualitzat correctament.",
        id_producte=str(product_id),
        es_privat=len(owners_data) > 0,
        propietaris=owners_data,
    )


def _get_product_owner_rows(product_id: int, db: Session):
    return (
        db.query(InventoryProductOwner, User)
        .join(User, InventoryProductOwner.user_id == User.id)
        .filter(InventoryProductOwner.id_inventari == product_id)
        .all()
    )


def _build_owner_schemas(product_id: int, db: Session):
    rows = _get_product_owner_rows(product_id, db)
    return [
        schemas.ProductOwnerSchema(
            id_usuari=str(user.id),
            nom=user.username,
        )
        for _, user in rows
    ]


def _get_owner_ids(product_id: int, db: Session) -> set:
    rows = (
        db.query(InventoryProductOwner.user_id)
        .filter(InventoryProductOwner.id_inventari == product_id)
        .all()
    )
    return {row[0] for row in rows}


def _validate_owner_list(home_id, owner_user_ids, db: Session):
    owner_user_ids = owner_user_ids or []

    normalized = []
    seen = set()

    for owner_id in owner_user_ids:
        if owner_id not in seen:
            seen.add(owner_id)
            normalized.append(owner_id)

    for owner_id in normalized:
        membership = (
            db.query(HomeMembership)
            .filter(
                HomeMembership.home_id == home_id,
                HomeMembership.user_id == owner_id,
                HomeMembership.is_active.is_(True),
            )
            .first()
        )
        if not membership:
            return None, _json_error(
                "Un dels propietaris indicats no pertany a la llar.",
                400,
                "OWNER_NOT_IN_HOME",
            )

    return normalized, None
