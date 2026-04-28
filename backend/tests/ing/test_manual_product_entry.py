import uuid

import pytest

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


def test_can_add_new_product_manually(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

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
    assert body["missatge"] == "Producte manual afegit correctament a l'inventari."

    created = body["producte"]
    assert created["nom"] == product["nom"]
    assert created["quantitat"] == product["quantitat"]
    assert created["preu"] == "2.50"
    assert created["metode_registre"] == "manual"
    assert created["codi_barres"] is None

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["nom"] in names


@pytest.mark.parametrize(
    "field, value, expected_code",
    [
        ("nom", None, "NAME_REQUIRED"),
        ("nom", "", "NAME_REQUIRED"),
        ("nom", "   ", "NAME_REQUIRED"),
        ("preu", None, "PRICE_REQUIRED"),
        ("categoria", None, "CATEGORY_REQUIRED"),
        ("quantitat", None, "QUANTITY_REQUIRED"),
    ],
)
def test_cannot_add_product_when_required_field_is_missing(
    client,
    shared_home_setup,
    field,
    value,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="product with missing field",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
    )
    product[field] = value

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 422, expected_code)


def test_added_product_is_persisted_in_home_products(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["member1_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_manual_inventory_payload(
        nom="persisted product",
        preu="1.75",
        categoria=CATEGORY_EXAMPLE,
        quantitat=2,
    )

    add_response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    persisted = next((item for item in products if item["name"] == product["nom"]), None)
    assert persisted is not None
    assert persisted["quantity"] == product["quantitat"]


def test_added_product_is_shown_in_inventory(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_manual_inventory_payload(
        nom="inventory visible product",
        preu="4.20",
        categoria=CATEGORY_EXAMPLE,
        quantitat=2,
    )

    add_response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    shown_product = next((item for item in products if item["name"] == product["nom"]), None)
    assert shown_product is not None
    assert shown_product["name"] == product["nom"]
    assert shown_product["quantity"] == product["quantitat"]


def test_can_add_product_with_name_at_max_length(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="a" * PRODUCT_NAME_MAX_LENGTH,
        preu="3.20",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["producte"]["nom"] == "a" * PRODUCT_NAME_MAX_LENGTH


def test_cannot_add_product_with_name_longer_than_max_length(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="a" * (PRODUCT_NAME_MAX_LENGTH + 1),
        preu="3.20",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 422, "NAME_TOO_LONG")


def test_product_name_is_trimmed_on_create(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="  milk  ",
        preu="2.20",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["producte"]["nom"] == "milk"


def test_product_name_allows_internal_spaces(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="olive oil extra",
        preu="5.30",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["producte"]["nom"] == "olive oil extra"


@pytest.mark.parametrize(
    "name",
    [
        "milk\n",
        "milk\t",
        "milk\r",
        "milk\\n",
        "milk\\t",
    ],
)
def test_cannot_add_product_with_invalid_characters_in_name(
    client,
    shared_home_setup,
    name,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom=name,
        preu="2.20",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 400, "NAME_INVALID_CHARACTERS")


def test_cannot_add_product_with_invalid_price(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="milk",
        preu="-1.00",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 422, "PRICE_INVALID")


@pytest.mark.parametrize("quantity", [0, -1])
def test_cannot_add_product_with_invalid_quantity(
    client,
    shared_home_setup,
    quantity,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="milk",
        preu="2.20",
        categoria=CATEGORY_EXAMPLE,
        quantitat=quantity,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 422, "QUANTITY_INVALID")


def test_cannot_add_product_with_quantity_over_99(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="milk",
        preu="2.20",
        categoria=CATEGORY_EXAMPLE,
        quantitat=100,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 422, "QUANTITY_TOO_HIGH")


@pytest.mark.parametrize(
    "price",
    [
        "1,50",
        "12.345",
        "abc",
        "12.3.4",
        "10 euros",
        "",
        " ",
    ],
)
def test_cannot_add_product_with_invalid_price_format(
    client,
    shared_home_setup,
    price,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="milk",
        preu=price,
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 422, response.text


def test_can_add_private_product_assigned_to_specific_member(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    member1_id = shared_home_setup["member1"]["user"]["id"]

    product = make_manual_inventory_payload(
        nom="member1 assigned private product",
        preu="2.40",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
        id_propietaris_privats=[member1_id],
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    created_product = next((item for item in products if item["name"] == product["nom"]), None)
    assert created_product is not None
    assert created_product["owner_user_ids"] == [member1_id]
    assert created_product["owner_user_id"] == member1_id
    assert created_product["is_private"] is True


def test_can_add_product_without_specific_owner_as_public(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_manual_inventory_payload(
        nom="public product without owner",
        preu="1.10",
        categoria=CATEGORY_EXAMPLE,
        quantitat=2,
        id_propietaris_privats=[],
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    created_product = next((item for item in products if item["name"] == product["nom"]), None)
    assert created_product is not None
    assert created_product["owner_user_ids"] == []
    assert created_product["owner_user_id"] is None
    assert created_product["is_private"] is False


def test_cannot_assign_product_to_user_who_is_not_member_of_home(
    client,
    shared_home_setup,
    outsider_user,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="product assigned to outsider",
        preu="2.00",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
        id_propietaris_privats=[outsider_user["user"]["id"]],
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 400, "OWNER_NOT_IN_HOME")


def test_cannot_assign_product_to_non_existing_user(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="product assigned to non existing user",
        preu="2.00",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
        id_propietaris_privats=[str(uuid.uuid4())],
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 400, "OWNER_NOT_IN_HOME")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_assign_product_owner(
    client,
    shared_home_setup,
    headers,
):
    member1_id = shared_home_setup["member1"]["user"]["id"]

    product = make_manual_inventory_payload(
        nom="unauthenticated assigned product",
        preu="2.00",
        categoria=CATEGORY_EXAMPLE,
        quantitat=1,
        id_propietaris_privats=[member1_id],
    )

    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"