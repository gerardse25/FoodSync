import uuid
from datetime import date

import pytest

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
                    "registration_method": row.metode_registre,
                    "owner_user_ids": owner_ids,
                }
            )
        return result


def test_lookup_barcode_finds_product_in_local_catalog(
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
        quantitat_envas="500 g",
        nutriscore_grade="a",
        imatge_url="https://example.com/local-rice.jpg",
    )

    response = client.get(
        f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}", headers=headers
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["found"] is True
    assert body["barcode"] == barcode
    assert body["source"] == "local_catalog"
    assert body["code"] == "BARCODE_FOUND_LOCAL"
    assert body["product"]["nom"] == "Local rice"
    assert body["product"]["categoria"] == "RICE"
    assert body["product"]["marca"] == "LocalBrand"
    assert body["product"]["quantitat_envas"] == "500 g"
    assert body["product"]["nutriscore"] == "a"
    assert body["product"]["imatge_url"] == "https://example.com/local-rice.jpg"


def test_lookup_barcode_finds_product_in_open_food_facts_when_not_in_local_catalog(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
):
    headers = shared_home_setup["owner_headers"]
    barcode = "23456789"

    def fake_lookup_barcode_enriched(_barcode):
        return {
            "found": True,
            "barcode": _barcode,
            "name": "OFF pasta",
            "category": "PASTA",
            "brand": "OFFBrand",
            "package_quantity_label": "1 kg",
            "nutriscore_grade": "b",
            "image_url": "https://example.com/off-pasta.jpg",
        }

    monkeypatch.setattr(
        app_modules["inventory_routes"],
        "lookup_barcode_enriched",
        fake_lookup_barcode_enriched,
    )

    response = client.get(
        f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}", headers=headers
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["found"] is True
    assert body["barcode"] == barcode
    assert body["source"] == "open_food_facts"
    assert body["code"] == "BARCODE_FOUND_OFF"
    assert body["product"]["nom"] == "OFF pasta"
    assert body["product"]["categoria"] == "PASTA"
    assert body["product"]["marca"] == "OFFBrand"
    assert body["product"]["quantitat_envas"] == "1 kg"
    assert body["product"]["nutriscore"] == "b"
    assert body["product"]["imatge_url"] == "https://example.com/off-pasta.jpg"


def test_lookup_barcode_returns_not_found_when_product_does_not_exist_anywhere(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
):
    headers = shared_home_setup["owner_headers"]
    barcode = "34567890"

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
        f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}", headers=headers
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["found"] is False
    assert body["barcode"] == barcode
    assert body["source"] == "open_food_facts"
    assert body["code"] == "BARCODE_NOT_FOUND"
    assert body["message"] == "Producte no trobat. Pots afegir-lo manualment."
    assert body["product"] is None


def test_lookup_barcode_returns_service_unavailable_when_off_service_fails(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
):
    headers = shared_home_setup["owner_headers"]
    barcode = "45678901"

    def fake_lookup_barcode_enriched(_barcode):
        return None

    monkeypatch.setattr(
        app_modules["inventory_routes"],
        "lookup_barcode_enriched",
        fake_lookup_barcode_enriched,
    )

    response = client.get(
        f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}", headers=headers
    )
    assert response.status_code == 503, response.text

    body = response.json()
    assert body["code"] == "BARCODE_SERVICE_UNAVAILABLE"


@pytest.mark.parametrize("barcode", ["abc", "12 34", "1234567", "123456789012345"])
def test_lookup_barcode_rejects_invalid_barcode_format(
    client,
    shared_home_setup,
    barcode,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/{barcode}", headers=headers
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "BARCODE_INVALID_FORMAT"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_lookup_barcode(
    client,
    headers,
):
    response = client.get(f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/12345678", headers=headers)
    assert response.status_code in (401, 403), response.text

    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_user_without_home_cannot_lookup_barcode(
    client,
    outsider_user,
):
    response = client.get(
        f"{BARCODE_LOOKUP_ENDPOINT_PREFIX}/12345678",
        headers=outsider_user["headers"],
    )
    assert response.status_code == 404, response.text

    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


def test_confirm_barcode_product_from_local_catalog_creates_inventory_product(
    client,
    shared_home_setup,
    app_modules,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    barcode = "56789012"

    local_catalog = seed_local_catalog_product(
        app_modules,
        barcode=barcode,
        nom="Local lentils",
        categoria_label="Llegums",
        marca="SeedBrand",
        quantitat_envas="400 g",
        nutriscore_grade="a",
        imatge_url="https://example.com/lentils.jpg",
        off_last_synced_at=date.today(),
    )

    payload = {
        "barcode": barcode,
        "preu": "3.50",
        "quantitat": 2,
        "data_compra": "2026-04-10",
        "data_caducitat": "2026-05-10",
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert (
        body["missatge"]
        == "Producte amb codi de barres afegit correctament a l'inventari."
    )
    assert body["producte"]["nom"] == "Local lentils"
    assert body["producte"]["quantitat"] == 2
    assert body["producte"]["categoria"] == "Llegums"
    assert body["producte"]["preu"] == "3.50"
    assert body["producte"]["data_compra"] == "2026-04-10"
    assert body["producte"]["data_caducitat"] == "2026-05-10"
    assert body["producte"]["codi_barres"] == barcode
    assert body["producte"]["metode_registre"] == "barcode"
    assert body["producte"]["id_producte_cataleg"] == str(
        local_catalog["id_producte_cataleg"]
    )

    inventory_rows = list_inventory_products_db(app_modules, home_id)
    assert len(inventory_rows) == 1
    assert inventory_rows[0]["catalog_id"] == local_catalog["id_producte_cataleg"]
    assert inventory_rows[0]["quantity"] == 2
    assert inventory_rows[0]["price"] == "3.50"
    assert inventory_rows[0]["registration_method"] == "barcode"
    assert inventory_rows[0]["owner_user_ids"] == []


def test_confirm_barcode_product_from_off_creates_catalog_and_inventory_product(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    barcode = "67890123"

    def fake_lookup_barcode_enriched(_barcode):
        return {
            "found": True,
            "barcode": _barcode,
            "name": "OFF cereals",
            "category": "BREAKFAST_CEREALS",
            "brand": "OFFBrand",
            "package_quantity_label": "375 g",
            "nutriscore_grade": "b",
            "image_url": "https://example.com/cereals.jpg",
            "ingredients_text": "oats",
            "allergens_text": "gluten",
            "nutriments_per_100g": {"energy-kcal_100g": 350},
        }

    monkeypatch.setattr(
        app_modules["inventory_routes"],
        "lookup_barcode_enriched",
        fake_lookup_barcode_enriched,
    )

    payload = {
        "barcode": barcode,
        "preu": "4.10",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["producte"]["nom"] == "OFF cereals"
    assert body["producte"]["categoria"] == "Cereals d'esmorzar"
    assert body["producte"]["preu"] == "4.10"
    assert body["producte"]["codi_barres"] == barcode
    assert body["producte"]["metode_registre"] == "barcode"

    inventory_rows = list_inventory_products_db(app_modules, home_id)
    assert len(inventory_rows) == 1
    assert inventory_rows[0]["quantity"] == 1
    assert inventory_rows[0]["registration_method"] == "barcode"
    assert inventory_rows[0]["owner_user_ids"] == []


def test_confirm_barcode_product_allows_manual_name_and_category_when_barcode_not_found(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    barcode = "78901234"

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

    payload = {
        "barcode": barcode,
        "nom": "Manual fallback product",
        "categoria": "RICE",
        "preu": "2.25",
        "quantitat": 3,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["producte"]["nom"] == "Manual fallback product"
    assert body["producte"]["categoria"] == "Arròs"
    assert body["producte"]["codi_barres"] == barcode

    inventory_rows = list_inventory_products_db(app_modules, home_id)
    assert len(inventory_rows) == 1
    assert inventory_rows[0]["quantity"] == 3


def test_confirm_barcode_product_can_create_private_product_for_specific_member(
    client,
    shared_home_setup,
    app_modules,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    member1_id = shared_home_setup["member1"]["user"]["id"]
    barcode = "89012345"

    seed_local_catalog_product(
        app_modules,
        barcode=barcode,
        nom="Private barcode product",
        categoria_label="Arròs",
        off_last_synced_at=date.today(),
    )

    payload = {
        "barcode": barcode,
        "preu": "1.95",
        "quantitat": 1,
        "id_propietaris_privats": [member1_id],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    inventory_rows = list_inventory_products_db(app_modules, home_id)
    assert len(inventory_rows) == 1
    assert inventory_rows[0]["owner_user_ids"] == [member1_id]


def test_confirm_barcode_requires_name_when_cannot_be_resolved(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
):
    headers = shared_home_setup["owner_headers"]
    barcode = "90123456"

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

    payload = {
        "barcode": barcode,
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert body["code"] == "NAME_REQUIRED"


def test_confirm_barcode_requires_category_when_cannot_be_resolved(
    client,
    shared_home_setup,
    app_modules,
    monkeypatch,
):
    headers = shared_home_setup["owner_headers"]
    barcode = "01234567"

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

    payload = {
        "barcode": barcode,
        "nom": "Manual name only",
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert body["code"] == "CATEGORY_REQUIRED"


@pytest.mark.parametrize("barcode", ["abc", "12 34", "1234567", "123456789012345"])
def test_confirm_barcode_rejects_invalid_barcode_format(
    client,
    shared_home_setup,
    barcode,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": barcode,
        "nom": "Any product",
        "categoria": "RICE",
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "BARCODE_INVALID_FORMAT"


def test_confirm_barcode_rejects_missing_price(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": "11112222",
        "nom": "Any product",
        "categoria": "RICE",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert body["code"] == "PRICE_REQUIRED"


def test_confirm_barcode_rejects_missing_quantity(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": "22223333",
        "nom": "Any product",
        "categoria": "RICE",
        "preu": "2.00",
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert body["code"] == "QUANTITY_REQUIRED"


@pytest.mark.parametrize("price", ["-1.00", "12.345"])
def test_confirm_barcode_rejects_invalid_price(
    client,
    shared_home_setup,
    price,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": "33334444",
        "nom": "Any product",
        "categoria": "RICE",
        "preu": price,
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert body["code"] == "PRICE_INVALID"


@pytest.mark.parametrize(
    "quantity, expected_code",
    [(0, "QUANTITY_INVALID"), (-1, "QUANTITY_INVALID"), (100, "QUANTITY_TOO_HIGH")],
)
def test_confirm_barcode_rejects_invalid_quantity(
    client,
    shared_home_setup,
    quantity,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": "44445555",
        "nom": "Any product",
        "categoria": "RICE",
        "preu": "2.00",
        "quantitat": quantity,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert body["code"] == expected_code


def test_confirm_barcode_rejects_owner_not_in_home(
    client,
    shared_home_setup,
    outsider_user,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": "55556666",
        "nom": "Any product",
        "categoria": "RICE",
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [outsider_user["user"]["id"]],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "OWNER_NOT_IN_HOME"


def test_confirm_barcode_rejects_invalid_characters_in_manual_name(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": "66667777",
        "nom": "milk\n",
        "categoria": "RICE",
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "NAME_INVALID_CHARACTERS"


def test_confirm_barcode_rejects_manual_name_too_long(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    payload = {
        "barcode": "77778888",
        "nom": "a" * 101,
        "categoria": "RICE",
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert body["code"] == "NAME_TOO_LONG"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_confirm_barcode_product(
    client,
    headers,
):
    payload = {
        "barcode": "88889999",
        "nom": "Any product",
        "categoria": "RICE",
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(BARCODE_CONFIRM_ENDPOINT, json=payload, headers=headers)
    assert response.status_code in (401, 403), response.text

    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_user_without_home_cannot_confirm_barcode_product(
    client,
    outsider_user,
):
    payload = {
        "barcode": "99990000",
        "nom": "Any product",
        "categoria": "RICE",
        "preu": "2.00",
        "quantitat": 1,
        "id_propietaris_privats": [],
    }

    response = client.post(
        BARCODE_CONFIRM_ENDPOINT, json=payload, headers=outsider_user["headers"]
    )
    assert response.status_code == 404, response.text

    body = response.json()
    assert body["code"] == "NOT_IN_HOME"
