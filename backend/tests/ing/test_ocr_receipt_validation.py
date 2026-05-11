import pytest


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


def test_preliminary_ocr_list_can_be_sent_to_final_confirmation_successfully(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    before_products = list_home_products_db(home_id)

    productes = [
        make_confirm_ticket_product(
            nom="Llet",
            categoria="MILK",
            quantitat=1,
            preu="1.25",
        ),
        make_confirm_ticket_product(
            nom="Galetes",
            categoria="OTHER",
            quantitat=2,
            preu="2.10",
        ),
    ]

    response = post_ticket_confirm(client, headers, productes)

    body = assert_confirm_success(response, expected_count=2)

    assert body["productes_guardats"][0]["nom"] == "Llet"
    assert body["productes_guardats"][1]["nom"] == "Galetes"

    after_products = list_home_products_db(home_id)
    assert len(after_products) == len(before_products) + 2

    saved_names = {p["name"] for p in after_products}
    assert "Llet" in saved_names
    assert "Galetes" in saved_names


def test_ocr_product_edited_in_frontend_is_validated_correctly_on_confirm(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    # Simula un producto detectado por OCR que el usuario corrige en frontend
    edited_product = make_confirm_ticket_product(
        nom="Llet sencera",
        categoria="MILK",
        quantitat=3,
        preu="2.40",
        data_compra="2026-01-10",
        data_caducitat="2026-01-17",
    )

    response = post_ticket_confirm(client, headers, [edited_product])

    body = assert_confirm_success(response, expected_count=1)
    saved_product = body["productes_guardats"][0]

    assert saved_product["nom"] == "Llet sencera"
    assert saved_product["quantitat"] == 3

    after_products = list_home_products_db(home_id)
    persisted = next((p for p in after_products if p["name"] == "Llet sencera"), None)
    assert persisted is not None
    assert persisted["quantity"] == 3


def test_product_removed_in_frontend_before_confirm_is_not_saved(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    before_products = list_home_products_db(home_id)

    # Simulamos que OCR detectó 2, pero frontend elimina uno antes de confirmar.
    productes_confirmed = [
        make_confirm_ticket_product(
            nom="Llet",
            categoria="MILK",
            quantitat=1,
            preu="1.25",
        )
    ]

    response = post_ticket_confirm(client, headers, productes_confirmed)

    body = assert_confirm_success(response, expected_count=1)
    assert body["productes_guardats"][0]["nom"] == "Llet"

    after_products = list_home_products_db(home_id)
    assert len(after_products) == len(before_products) + 1

    saved_names = {p["name"] for p in after_products}
    assert "Llet" in saved_names
    assert "Galetes" not in saved_names


@pytest.mark.parametrize(
    "field, value, expected_code",
    [
        ("nom", "", "NAME_REQUIRED"),
        ("nom", "   ", "NAME_REQUIRED"),
        ("categoria", None, "CATEGORY_REQUIRED"),
        ("quantitat", None, "QUANTITY_REQUIRED"),
        ("preu", None, "PRICE_REQUIRED"),
    ],
)
def test_confirm_returns_same_error_as_manual_flow_when_required_field_is_missing(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    field,
    value,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]

    product = make_confirm_ticket_product(
        nom="Llet",
        categoria="MILK",
        quantitat=1,
        preu="1.25",
    )
    product[field] = value

    response = post_ticket_confirm(client, headers, [product])

    assert_confirm_error(response, 422, expected_code)


@pytest.mark.parametrize(
    "field, value, expected_status, expected_code",
    [
        ("preu", "-1.00", 422, "PRICE_INVALID"),
        ("quantitat", 0, 422, "QUANTITY_INVALID"),
        ("quantitat", -1, 422, "QUANTITY_INVALID"),
        ("nom", "A" * 121, 422, "NAME_TOO_LONG"),
        ("nom", "Llet\n", 400, "NAME_INVALID_CHARACTERS"),
    ],
)
def test_invalid_data_after_ocr_is_rejected_with_same_validation_as_manual_or_barcode(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    field,
    value,
    expected_status,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]

    product = make_confirm_ticket_product(
        nom="Llet",
        categoria="MILK",
        quantitat=1,
        preu="1.25",
    )
    product[field] = value

    response = post_ticket_confirm(client, headers, [product])

    assert_confirm_error(response, expected_status, expected_code)


def test_mixed_ocr_and_manual_products_all_follow_same_validation_rules(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    before_products = list_home_products_db(home_id)

    productes = [
        # Producto venido de OCR y aceptado/corregido
        make_confirm_ticket_product(
            nom="Llet",
            categoria="MILK",
            quantitat=1,
            preu="1.25",
        ),
        # Producto añadido manualmente desde el flujo OCR
        make_confirm_ticket_product(
            nom="Arròs",
            categoria="RICE",
            quantitat=2,
            preu="2.30",
        ),
    ]

    response = post_ticket_confirm(client, headers, productes)

    body = assert_confirm_success(response, expected_count=2)

    saved_names = {p["nom"] for p in body["productes_guardats"]}
    assert saved_names == {"Llet", "Arròs"}

    after_products = list_home_products_db(home_id)
    assert len(after_products) == len(before_products) + 2

    persisted_names = {p["name"] for p in after_products}
    assert "Llet" in persisted_names
    assert "Arròs" in persisted_names


def test_mixed_ocr_and_manual_products_fail_confirmation_if_one_product_is_invalid(
    client,
    shared_home_setup,
    make_confirm_ticket_product,
    list_home_products_db,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    before_products = list_home_products_db(home_id)

    productes = [
        make_confirm_ticket_product(
            nom="Llet",
            categoria="MILK",
            quantitat=1,
            preu="1.25",
        ),
        make_confirm_ticket_product(
            nom="Arròs",
            categoria="RICE",
            quantitat=0,
            preu="2.30",
        ),
    ]

    response = post_ticket_confirm(client, headers, productes)

    assert_confirm_error(response, 422, "QUANTITY_INVALID")

    # Importante: si uno es inválido, no debería guardarse ninguno
    after_products = list_home_products_db(home_id)
    assert after_products == before_products
