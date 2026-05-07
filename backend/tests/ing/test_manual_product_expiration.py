import pytest

from freezegun import freeze_time


MANUAL_ENTRY_ENDPOINT = "/inventory/manual"
PRODUCT_NAME_MAX_LENGTH = 100
CATEGORY_EXAMPLE = "RICE"


def make_manual_inventory_payload(
    *,
    nom: str | None = "manual product",
    preu: str | int | float | None = "2.50",
    categoria: str | None = CATEGORY_EXAMPLE,
    quantitat: int | None = 1,
    data_compra: str | None = None,
    data_caducitat: str | None = None,
    id_propietaris_privats: list[str] | None = None,
):
    return {
        "nom": nom,
        "preu": preu,
        "categoria": categoria,
        "quantitat": quantitat,
        "data_compra": data_compra,
        "data_caducitat": data_caducitat,
        "id_propietaris_privats": id_propietaris_privats or [],
    }


def assert_backend_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "error" in body


def test_add_product_manually_with_expiration_date(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
            data_caducitat="2027-01-10"
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    
    created = body["producte"]
    assert created["data_caducitat"] == product["data_caducitat"]

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names

def test_add_product_manually_with_expiration_date_different_to_backend_rules(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
            data_caducitat="2026-02-10"
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    
    created = body["producte"]
    assert created["data_caducitat"] == product["data_caducitat"]

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names


def test_add_product_manually_with_buy_date(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
            data_compra="2026-01-10"
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    
    created = body["producte"]
    assert created["data_compra"] == product["data_compra"]
    assert created["data_caducitat"] == "2027-01-10"

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names


def test_add_product_manually_with_buy_date_and_different_category(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-01"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria="OTHER",
            quantitat=3,
            data_compra="2026-01-01"
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    
    created = body["producte"]
    assert created["data_compra"] == product["data_compra"]
    assert created["data_caducitat"] == "2026-01-31"

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names


def test_add_product_manually_with_expiration_and_buy_date(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
            data_compra="2026-01-10",
            data_caducitat="2027-01-10",
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    
    created = body["producte"]
    assert created["data_compra"] == product["data_compra"]
    assert created["data_caducitat"] == product["data_caducitat"]

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names


def test_add_product_manually_with_expiration_and_buy_date_different_to_backend_rules(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
            data_compra="2026-01-10",
            data_caducitat="2026-05-10",
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    
    created = body["producte"]
    assert created["data_compra"] == product["data_compra"]
    assert created["data_caducitat"] == product["data_caducitat"]

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names


def test_add_product_manually_with_no_date(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    
    created = body["producte"]
    assert created["data_compra"] is None
    assert created["data_caducitat"] == "2027-01-10"

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names


@pytest.mark.parametrize(
    "date, expected_code",
    [
        ("2025-01-09", "PURCHASE_DATE_TOO_OLD"),
        ("2026-01-11", "PURCHASE_DATE_IN_FUTURE"),
    ],
)
def test_add_product_manually_with_invalid_date(
    client,
    shared_home_setup,
    list_home_products_db,
    date,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
            data_compra=date,
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["code"] == expected_code

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] not in names


@pytest.mark.parametrize(
    "purchase_date, expected_expiration_date",
    [
        ("2025-01-10", "2026-01-10"),
        ("2025-01-11", "2026-01-11"),
    ],
)
def test_add_product_manually_with_limit_valid_date(
    client,
    shared_home_setup,
    list_home_products_db,
    purchase_date,
    expected_expiration_date,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_manual_inventory_payload(
            nom="manual new product",
            preu="2.50",
            categoria=CATEGORY_EXAMPLE,
            quantitat=3,
            data_compra=purchase_date,
        )
        response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    created = body["producte"]
    assert created["data_compra"] == product["data_compra"]
    assert created["data_caducitat"] == expected_expiration_date

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names

