import pytest

PRODUCT_NAME_MAX_LENGTH = 120
PRODUCT_CATEGORY_MAX_LENGTH = 64


def assert_backend_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "detail" in body


def test_can_add_new_product_manually(client, shared_home_setup, make_product_data, list_home_products_db):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_product_data(
        name="manual new product",
        price="2.50",
        category="dairy",
        quantity=3,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["message"] == "Producte creat correctament"
    assert body["product"]["name"] == product["name"]
    assert body["product"]["category"] == product["category"]
    assert body["product"]["quantity"] == product["quantity"]
    assert body["product"]["price"] == "2.50"
    assert body["product"]["owner_user_id"] is None
    assert body["product"]["is_private"] is False

    products = list_home_products_db(home_id)
    names = {item["name"] for item in products}
    assert product["name"] in names


@pytest.mark.parametrize(
    "field, value, expected_code",
    [
        ("name", None, "NAME_REQUIRED"),
        ("name", "", "NAME_REQUIRED"),
        ("name", "   ", "NAME_REQUIRED"),
        ("price", None, "PRICE_REQUIRED"),
        ("category", None, "CATEGORY_REQUIRED"),
        ("category", "", "CATEGORY_REQUIRED"),
        ("category", "   ", "CATEGORY_REQUIRED"),
        ("quantity", None, "QUANTITY_REQUIRED"),
    ],
)
def test_cannot_add_product_when_required_field_is_missing(
    client,
    shared_home_setup,
    make_product_data,
    field,
    value,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="product with missing field",
        price="2.50",
        category="dairy",
        quantity=3,
        owner_user_id=None,
    )
    product[field] = value

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 422, expected_code)


def test_added_product_is_persisted_in_home_products(
    client,
    shared_home_setup,
    make_product_data,
    list_home_products_db,
):
    headers = shared_home_setup["member1_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_product_data(
        name="persisted product",
        price="1.75",
        category="meat",
        quantity=2,
        owner_user_id=None,
    )

    add_response = client.post("/products/manual", json=product, headers=headers)
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    persisted = next((item for item in products if item["name"] == product["name"]), None)
    assert persisted is not None
    assert persisted["category"] == product["category"]
    assert persisted["quantity"] == product["quantity"]
    assert persisted["is_private"] is False


def test_added_product_is_shown_in_inventory(
    client,
    shared_home_setup,
    make_product_data,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_product_data(
        name="inventory visible product",
        price="4.20",
        category="vegetables",
        quantity=2,
        owner_user_id=None,
    )

    add_response = client.post("/products/manual", json=product, headers=headers)
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    shown_product = next((item for item in products if item["name"] == product["name"]), None)
    assert shown_product is not None
    assert shown_product["name"] == product["name"]
    assert shown_product["quantity"] == product["quantity"]


def test_can_add_product_with_name_at_max_length(
    client,
    shared_home_setup,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="a" * PRODUCT_NAME_MAX_LENGTH,
        price="3.20",
        category="vegetables",
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["product"]["name"] == "a" * PRODUCT_NAME_MAX_LENGTH


def test_cannot_add_product_with_name_longer_than_max_length(
    client,
    shared_home_setup,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="a" * (PRODUCT_NAME_MAX_LENGTH + 1),
        price="3.20",
        category="vegetables",
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 422, "NAME_TOO_LONG")


def test_can_add_product_with_category_at_max_length(
    client,
    shared_home_setup,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="milk",
        price="2.10",
        category="c" * PRODUCT_CATEGORY_MAX_LENGTH,
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["product"]["category"] == "c" * PRODUCT_CATEGORY_MAX_LENGTH


def test_cannot_add_product_with_category_longer_than_max_length(
    client,
    shared_home_setup,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="milk",
        price="2.10",
        category="c" * (PRODUCT_CATEGORY_MAX_LENGTH + 1),
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 422, "CATEGORY_TOO_LONG")


def test_product_name_is_trimmed_on_create(
    client,
    shared_home_setup,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="  milk  ",
        price="2.20",
        category="dairy",
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["product"]["name"] == "milk"


def test_product_name_allows_internal_spaces(
    client,
    shared_home_setup,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="olive oil extra",
        price="5.30",
        category="oil",
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["product"]["name"] == "olive oil extra"


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
    make_product_data,
    name,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name=name,
        price="2.20",
        category="dairy",
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 400, "NAME_INVALID_CHARACTERS")


@pytest.mark.parametrize(
    "category",
    [
        "dairy\n",
        "dairy\t",
        "dairy\\n",
        "dairy\\t",
    ],
)
def test_cannot_add_product_with_invalid_characters_in_category(
    client,
    shared_home_setup,
    make_product_data,
    category,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="milk",
        price="2.20",
        category=category,
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 400, "CATEGORY_INVALID_CHARACTERS")


@pytest.mark.parametrize(
    "price, expected_code",
    [
        ("-1.00", "PRICE_INVALID"),
    ],
)
def test_cannot_add_product_with_invalid_price(
    client,
    shared_home_setup,
    make_product_data,
    price,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="milk",
        price=price,
        category="dairy",
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 422, expected_code)


@pytest.mark.parametrize(
    "quantity, expected_code",
    [
        (0, "QUANTITY_INVALID"),
        (-1, "QUANTITY_INVALID"),
    ],
)
def test_cannot_add_product_with_invalid_quantity(
    client,
    shared_home_setup,
    make_product_data,
    quantity,
    expected_code,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="milk",
        price="2.20",
        category="dairy",
        quantity=quantity,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 422, expected_code)


@pytest.mark.parametrize(
    "price",
    [
        "1,50",       # coma decimal
        "12.345",     # demasiados decimales
        "abc",        # no numérico
        "12.3.4",     # formato inválido
        "10 euros",   # texto mezclado
        "",           # vacío
        " ",          # solo espacios
    ],
)
def test_cannot_add_product_with_invalid_price_format(
    client,
    shared_home_setup,
    make_product_data,
    price,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="milk",
        price=price,
        category="dairy",
        quantity=1,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code in (400, 422), response.text
    body = response.json()

    if "code" in body:
        assert body["code"] in ("PRICE_INVALID", "PRICE_REQUIRED")