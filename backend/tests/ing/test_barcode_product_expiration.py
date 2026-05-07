import uuid

import pytest
from freezegun import freeze_time

BARCODE_LOOKUP_ENDPOINT_PREFIX = "/inventory/barcode"
BARCODE_CONFIRM_ENDPOINT = "/inventory/barcode/confirm"


def seed_local_catalog_product(
    app_modules,
    *,
    barcode: str,
    nom: str = "Local barcode product",
    categoria_label: str = "Arròs",
    marca: str = "LocalBrand",
    quantitat_envas: str = "500 g",
    nutriscore_grade: str = "a",
    imatge_url: str = "https://example.com/product.jpg",
    off_last_synced_at=None,
):
    inventory_models = app_modules["inventory_models"]
    SessionLocal = app_modules["database"].SessionLocal

    with SessionLocal() as db:
        category = (
            db.query(inventory_models.Category).filter_by(nom=categoria_label).first()
        )
        if category is None:
            category = inventory_models.Category(nom=categoria_label)
            db.add(category)
            db.flush()

        catalog_product = inventory_models.CatalogProduct(
            codi_barres=barcode,
            nom=nom,
            marca=marca,
            id_categoria=category.id_categoria,
            imatge_url=imatge_url,
            quantitat_envas=quantitat_envas,
            nutriscore_grade=nutriscore_grade,
            off_last_synced_at=off_last_synced_at,
        )
        db.add(catalog_product)
        db.commit()
        db.refresh(catalog_product)

        return {
            "id_producte_cataleg": catalog_product.id_producte_cataleg,
            "codi_barres": catalog_product.codi_barres,
            "nom": catalog_product.nom,
            "marca": catalog_product.marca,
            "categoria_label": categoria_label,
            "quantitat_envas": catalog_product.quantitat_envas,
            "nutriscore_grade": catalog_product.nutriscore_grade,
            "imatge_url": catalog_product.imatge_url,
        }


def list_inventory_products_db(app_modules, home_id):
    inventory_models = app_modules["inventory_models"]
    SessionLocal = app_modules["database"].SessionLocal

    home_uuid = uuid.UUID(str(home_id))

    with SessionLocal() as db:
        rows = (
            db.query(inventory_models.InventoryProduct)
            .filter(inventory_models.InventoryProduct.id_llar == home_uuid)
            .all()
        )

        result = []
        for row in rows:
            owner_ids = [str(owner.user_id) for owner in row.owners]
            result.append(
                {
                    "id": row.id_inventari,
                    "catalog_id": row.id_producte_cataleg,
                    "quantity": row.quantitat,
                    "price": str(row.preu) if row.preu is not None else None,
                    "purchase_date": row.data_compra,
                    "expiration_date": row.data_caducitat,
                    "expiration_estimated": getattr(row, "data_caducitat_estimada", None),
                    "registration_method": row.metode_registre,
                    "owner_user_ids": owner_ids,
                }
            )
        return result


def test_barcode_preview_returns_product_data_and_estimated_expiration_for_local_catalog(
    client,
    shared_home_setup,
    app_modules,
):
    headers = shared_home_setup["owner_headers"]
    barcode = "12345678"

    seed_local_catalog_product(
        app_modules,
        barcode=barcode,
        nom="Local rice",
        categoria_label="Arròs",
        marca="LocalBrand",
    )

    with freeze_time("2026-01-10"):
        response = client.get(
            f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}",
            headers=headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["found"] is True
    assert body["code"] == "BARCODE_FOUND_LOCAL"
    assert body["barcode"] == barcode
    assert body["product"]["nom"] == "Local rice"
    assert body["product"]["categoria"] == "RICE"

    assert body["product"]["data_compra"] == "2026-01-10"
    assert body["product"]["data_caducitat"] == "2027-01-10"
    assert body["product"]["data_caducitat_estimada"] is True


def test_barcode_preview_uses_current_system_date_for_expiration_estimation(
    client,
    shared_home_setup,
    app_modules,
):
    headers = shared_home_setup["owner_headers"]
    barcode = "23456789"

    seed_local_catalog_product(
        app_modules,
        barcode=barcode,
        nom="Local rice",
        categoria_label="Arròs",
    )

    with freeze_time("2026-01-10"):
        response = client.get(
            f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}",
            headers=headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["product"]["categoria"] == "RICE"
    assert body["product"]["data_compra"] == "2026-01-10"
    assert body["product"]["data_caducitat"] == "2027-01-10"


def test_barcode_preview_different_categories_return_different_estimated_expirations(
    client,
    shared_home_setup,
    app_modules,
):
    headers = shared_home_setup["owner_headers"]

    rice_barcode = "34567890"
    other_barcode = "45678901"

    seed_local_catalog_product(
        app_modules,
        barcode=rice_barcode,
        nom="Rice product",
        categoria_label="Arròs",
    )
    seed_local_catalog_product(
        app_modules,
        barcode=other_barcode,
        nom="Other product",
        categoria_label="Altres",
    )

    with freeze_time("2026-01-10"):
        rice_response = client.get(
            f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{rice_barcode}",
            headers=headers,
        )
        other_response = client.get(
            f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{other_barcode}",
            headers=headers,
        )

    assert rice_response.status_code == 200, rice_response.text
    assert other_response.status_code == 200, other_response.text

    rice_body = rice_response.json()
    other_body = other_response.json()

    assert rice_body["product"]["categoria"] == "RICE"
    assert other_body["product"]["categoria"] == "OTHER"

    assert rice_body["product"]["data_caducitat"] == "2027-01-10"
    assert other_body["product"]["data_caducitat"] == "2026-02-09"
    assert rice_body["product"]["data_caducitat"] != other_body["product"]["data_caducitat"]


@pytest.mark.parametrize("barcode", ["99999999", "12345678901234"])
def test_barcode_preview_invalid_or_not_found_does_not_return_fake_estimation(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
    barcode,
):
    headers = shared_home_setup["owner_headers"]

    def fake_lookup_barcode_enriched(_barcode):
        return {
            "found": False,
            "barcode": _barcode,
        }

    monkeypatch.setattr(
        app_modules["inventory_routes"],
        "lookup_barcode_enriched",
        fake_lookup_barcode_enriched,
    )

    response = client.get(
        f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["found"] is False
    assert body["code"] == "BARCODE_NOT_FOUND"
    assert body["product"] is None


def test_barcode_preview_does_not_persist_product_until_confirm(
    client,
    shared_home_setup,
    app_modules,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    barcode = "56789012"

    seeded = seed_local_catalog_product(
        app_modules,
        barcode=barcode,
        nom="Preview rice product",
        categoria_label="Arròs",
    )

    before_rows = list_inventory_products_db(app_modules, home_id)
    before_count = len(before_rows)

    with freeze_time("2026-01-10"):
        preview_response = client.get(
            f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}",
            headers=headers,
        )

    assert preview_response.status_code == 200, preview_response.text

    after_preview_rows = list_inventory_products_db(app_modules, home_id)
    assert len(after_preview_rows) == before_count

    confirm_payload = {
        "barcode": barcode,
        "nom": "Preview rice product",
        "categoria": "RICE",
        "preu": "2.50",
        "quantitat": 1,
        "data_compra": "2026-01-10",
        "data_caducitat": "2027-01-10",
        "id_propietaris_privats": [],
    }

    with freeze_time("2026-01-10"):
        confirm_response = client.post(
            BARCODE_CONFIRM_ENDPOINT,
            json=confirm_payload,
            headers=headers,
        )

    assert confirm_response.status_code == 201, confirm_response.text
    confirm_body = confirm_response.json()
    assert confirm_body["code"] == "PRODUCT_CREATED"
    assert confirm_body["producte"]["metode_registre"] == "barcode"
    assert confirm_body["producte"]["codi_barres"] == barcode
    assert confirm_body["producte"]["data_compra"] == "2026-01-10"
    assert confirm_body["producte"]["data_caducitat"] == "2027-01-10"

    after_confirm_rows = list_inventory_products_db(app_modules, home_id)
    assert len(after_confirm_rows) == before_count + 1

    created = next(
        (row for row in after_confirm_rows if row["catalog_id"] == seeded["id_producte_cataleg"]),
        None,
    )
    assert created is not None
    assert created["registration_method"] == "barcode"
    assert str(created["purchase_date"]) == "2026-01-10"
    assert str(created["expiration_date"]) == "2027-01-10"