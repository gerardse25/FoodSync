import pytest
from freezegun import freeze_time


OCR_CONFIRM_ENDPOINT = "/inventory/ticket/confirm"
CATEGORY_EXAMPLE = "RICE"

# TODO: Quitar cuando el backend del ocr tenga acoplado el de caducidad
pytestmark = pytest.mark.xfail(
    reason="La integració de caducitat al flux OCR encara no està implementada",
    strict=False,
)

def assert_confirm_success(response, expected_count):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "TICKET_CONFIRMED"
    assert "productes_guardats" in body
    assert len(body["productes_guardats"]) == expected_count
    return body


def assert_confirm_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "error" in body or "detail" in body
    return body

def post_ticket_confirm(client, headers, productes):
    return client.post(
        "/inventory/ticket/confirm",
        headers=headers,
        json={"productes": productes},
    )


def find_product_in_db(products, target_name):
    return next((item for item in products if item["name"] == target_name), None)


def test_confirm_ocr_product_with_expiration_date_keeps_manual_expiration(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="ocr product with expiration date",
            categoria=CATEGORY_EXAMPLE,
            quantitat=1,
            preu="2.50",
            data_caducitat="2027-01-10",
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["nom"] == product["nom"]
    assert saved["data_caducitat"] == product["data_caducitat"]

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, product["nom"])
    assert persisted is not None
    assert persisted["expiration_date"] == "2027-01-10"


def test_confirm_ocr_product_with_expiration_date_different_to_backend_rules_keeps_manual_value(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="ocr product custom expiration",
            categoria=CATEGORY_EXAMPLE,
            quantitat=1,
            preu="2.50",
            data_caducitat="2026-02-10",
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["data_caducitat"] == "2026-02-10"

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, product["nom"])
    assert persisted is not None
    assert persisted["expiration_date"] == "2026-02-10"


def test_confirm_ocr_product_with_purchase_date_estimates_expiration(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="ocr product with purchase date",
            categoria="RICE",
            quantitat=1,
            preu="2.50",
            data_compra="2026-01-10",
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["data_compra"] == "2026-01-10"
    assert saved["data_caducitat"] == "2027-01-10"

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, product["nom"])
    assert persisted is not None
    assert persisted["purchase_date"] == "2026-01-10"
    assert persisted["expiration_date"] == "2027-01-10"


def test_confirm_ocr_product_with_purchase_date_and_different_category_estimates_different_expiration(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-01"):
        product = make_confirm_ticket_product(
            nom="ocr other category product",
            categoria="OTHER",
            quantitat=1,
            preu="2.50",
            data_compra="2026-01-01",
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["data_compra"] == "2026-01-01"
    assert saved["data_caducitat"] == "2026-01-31"

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, product["nom"])
    assert persisted is not None
    assert persisted["purchase_date"] == "2026-01-01"
    assert persisted["expiration_date"] == "2026-01-31"


def test_confirm_ocr_product_with_purchase_and_expiration_dates_keeps_both_values(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="ocr product with both dates",
            categoria="RICE",
            quantitat=1,
            preu="2.50",
            data_compra="2026-01-10",
            data_caducitat="2027-01-10",
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["data_compra"] == "2026-01-10"
    assert saved["data_caducitat"] == "2027-01-10"

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, product["nom"])
    assert persisted is not None
    assert persisted["purchase_date"] == "2026-01-10"
    assert persisted["expiration_date"] == "2027-01-10"


def test_confirm_ocr_product_with_purchase_and_expiration_dates_different_to_backend_rules_keeps_manual_expiration(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="ocr product with custom both dates",
            categoria="RICE",
            quantitat=1,
            preu="2.50",
            data_compra="2026-01-10",
            data_caducitat="2026-05-10",
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["data_compra"] == "2026-01-10"
    assert saved["data_caducitat"] == "2026-05-10"

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, product["nom"])
    assert persisted is not None
    assert persisted["purchase_date"] == "2026-01-10"
    assert persisted["expiration_date"] == "2026-05-10"


def test_confirm_ocr_product_with_no_dates_sets_system_purchase_date_and_estimated_expiration(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="ocr product with no dates",
            categoria="RICE",
            quantitat=1,
            preu="2.50",
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["data_compra"] == "2026-01-10"
    assert saved["data_caducitat"] == "2027-01-10"

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, product["nom"])
    assert persisted is not None
    assert persisted["purchase_date"] == "2026-01-10"
    assert persisted["expiration_date"] == "2027-01-10"


def test_confirm_ocr_rejects_expiration_date_before_purchase_date(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    before_products = list_home_products_db(home_id)

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="ocr invalid expiration order",
            categoria="RICE",
            quantitat=1,
            preu="2.50",
            data_compra="2026-01-10",
            data_caducitat="2026-01-09",
        )
        response = post_ticket_confirm(client, headers, [product])

    assert_confirm_error(response, 422, "EXPIRATION_BEFORE_PURCHASE_DATE")

    after_products = list_home_products_db(home_id)
    assert after_products == before_products


@pytest.mark.parametrize(
    "purchase_date, expected_code",
    [
        ("2025-01-09", "PURCHASE_DATE_TOO_OLD"),
        ("2026-01-11", "PURCHASE_DATE_IN_FUTURE"),
    ],
)
def test_confirm_ocr_rejects_invalid_purchase_dates(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
    purchase_date,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    before_products = list_home_products_db(home_id)

    with freeze_time("2026-01-10 12:00:00"):
        product = make_confirm_ticket_product(
            nom="product",
            categoria="RICE",
            quantitat=1,
            preu="2.50",
            data_compra=purchase_date,
        )
        response = post_ticket_confirm(client, headers, [product])

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == expected_code

    after_products = list_home_products_db(home_id)
    assert after_products == before_products


@pytest.mark.parametrize(
    "purchase_date, expected_expiration_date",
    [
        ("2025-01-10", "2026-01-10"),
        ("2025-01-11", "2026-01-11"),
    ],
)
def test_confirm_ocr_accepts_limit_valid_purchase_dates_and_estimates_expiration(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
    purchase_date,
    expected_expiration_date,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    with freeze_time("2026-01-10"):
        product = make_confirm_ticket_product(
            nom="product",
            categoria="RICE",
            quantitat=1,
            preu="2.50",
            data_compra=purchase_date,
        )
        response = post_ticket_confirm(client, headers, [product])

    body = assert_confirm_success(response, expected_count=1)

    saved = body["productes_guardats"][0]
    assert saved["data_compra"] == purchase_date
    assert saved["data_caducitat"] == expected_expiration_date

    products = list_home_products_db(home_id)
    persisted = find_product_in_db(products, "product")
    assert persisted is not None
    assert persisted["purchase_date"] == purchase_date
    assert persisted["expiration_date"] == expected_expiration_date