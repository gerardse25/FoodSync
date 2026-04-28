import pytest

MODIFY_ENDPOINT = "/inventory_modify"
MAX_PRODUCT_QUANTITY = 99


def modify_product_request(client, product_id, modificacio, headers):
    return client.patch(
        MODIFY_ENDPOINT,
        json={
            "id_producte": str(product_id),
            "modificacio": modificacio,
        },
        headers=headers,
    )


def get_product_by_name(products, target_name):
    return next(
        (product for product in products if product["name"] == target_name), None
    )


@pytest.mark.parametrize(
    "who,target_key,modificacio",
    [
        ("member", "member1_private", -1),
        ("member", "member1_private", 1),
        ("member", "public_product", -1),
        ("member", "public_product", 1),
        ("owner", "owner_private", -1),
        ("owner", "owner_private", 1),
        ("owner", "public_product", -1),
        ("owner", "public_product", 1),
    ],
)
def test_user_can_modify_allowed_product_quantities(
    client,
    shared_home_with_products,
    list_home_products_db,
    who,
    target_key,
    modificacio,
):
    headers = (
        shared_home_with_products["owner_headers"]
        if who == "owner"
        else shared_home_with_products["member1_headers"]
    )

    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"][target_key]["db"]["id"]
    target_name = shared_home_with_products["products"][target_key]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_name)
    assert before_product is not None
    initial_quantity = before_product["quantity"]

    assert initial_quantity + modificacio >= 0

    response = modify_product_request(client, target_id, modificacio, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_QUANTITY_UPDATED"
    assert body["producte"]["id_producte"] == str(target_id)
    assert body["producte"]["nom"] == target_name
    assert body["producte"]["quantitat_restant"] == initial_quantity + modificacio

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_name)
    assert after_product is not None
    assert after_product["quantity"] == initial_quantity + modificacio


def test_zero_modification_keeps_same_quantity(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"][
        "name"
    ]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_name)
    assert before_product is not None
    initial_quantity = before_product["quantity"]

    response = modify_product_request(client, target_id, 0, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_QUANTITY_UPDATED"
    assert body["producte"]["quantitat_restant"] == initial_quantity

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_name)
    assert after_product is not None
    assert after_product["quantity"] == initial_quantity


@pytest.mark.parametrize(
    "who,target_key",
    [
        ("member", "owner_private"),
        ("owner", "member1_private"),
    ],
)
def test_user_cannot_modify_private_product_owned_by_another_user(
    client,
    shared_home_with_products,
    list_home_products_db,
    who,
    target_key,
):
    headers = (
        shared_home_with_products["owner_headers"]
        if who == "owner"
        else shared_home_with_products["member1_headers"]
    )

    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"][target_key]["db"]["id"]
    target_name = shared_home_with_products["products"][target_key]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_name)
    assert before_product is not None
    initial_quantity = before_product["quantity"]

    response = modify_product_request(client, target_id, -1, headers)
    assert response.status_code == 403, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_MODIFICATION_FORBIDDEN"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_name)
    assert after_product is not None
    assert after_product["quantity"] == initial_quantity


def test_decreasing_more_than_available_stock_returns_error(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(client, target_id, -10, headers)
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_INSUFFICIENT_STOCK"


def test_cannot_consume_product_when_it_is_already_out_of_stock(
    client,
    shared_home_with_single_product,
    list_home_products_db,
):
    headers = shared_home_with_single_product["owner_headers"]
    home_id = shared_home_with_single_product["home_id"]
    target_id = shared_home_with_single_product["products"]["only_product"]["db"]["id"]
    target_name = shared_home_with_single_product["products"]["only_product"][
        "payload"
    ]["name"]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_name)
    assert before_product is not None
    initial_quantity = before_product["quantity"]

    response_to_zero = modify_product_request(
        client, target_id, -initial_quantity, headers
    )
    assert response_to_zero.status_code == 200, response_to_zero.text
    assert response_to_zero.json()["code"] == "PRODUCT_QUANTITY_UPDATED"

    response = modify_product_request(client, target_id, -1, headers)
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OUT_OF_STOCK"


@pytest.mark.parametrize(
    "initial_quantity, modificacio, expected_quantity",
    [
        (98, 0, 98),
        (98, 1, 99),
        (99, 0, 99),
    ],
)
def test_quantity_up_to_max_99_is_allowed(
    client,
    shared_home_with_single_product,
    seed_product_db,
    list_home_products_db,
    initial_quantity,
    modificacio,
    expected_quantity,
):
    headers = shared_home_with_single_product["owner_headers"]
    home_id = shared_home_with_single_product["home_id"]
    owner_ctx = shared_home_with_single_product["owner"]

    seeded = seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name=f"quantity_limit_product_{initial_quantity}_{modificacio}",
        category="test",
        quantity=initial_quantity,
        price="1.00",
        owner_user_ids=[],
    )

    response = modify_product_request(client, seeded["id"], modificacio, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_QUANTITY_UPDATED"
    assert body["producte"]["quantitat_restant"] == expected_quantity

    products = list_home_products_db(home_id)
    product = get_product_by_name(products, seeded["name"])
    assert product is not None
    assert product["quantity"] == expected_quantity


def test_quantity_cannot_exceed_99_units(
    client,
    shared_home_with_single_product,
    seed_product_db,
    list_home_products_db,
):
    headers = shared_home_with_single_product["owner_headers"]
    home_id = shared_home_with_single_product["home_id"]
    owner_ctx = shared_home_with_single_product["owner"]

    seeded = seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="quantity_limit_product_overflow",
        category="test",
        quantity=99,
        price="1.00",
        owner_user_ids=[],
    )

    response = modify_product_request(client, seeded["id"], 1, headers)
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "QUANTITY_TOO_HIGH"

    products = list_home_products_db(home_id)
    product = get_product_by_name(products, seeded["name"])
    assert product is not None
    assert product["quantity"] == 99


def test_modifying_non_existing_product_returns_error(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = modify_product_request(client, 999999, -1, headers)
    assert response.status_code == 404, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"


def test_modifying_product_with_non_numeric_id_returns_error(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = modify_product_request(client, "abc", -1, headers)
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_ID_INVALID"


def test_non_member_cannot_modify_inventory_product(
    client,
    shared_home_with_products,
    outsider_user,
):
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(client, target_id, -1, outsider_user["headers"])
    assert response.status_code == 403, response.text

    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_modify_inventory_product(
    client,
    shared_home_with_products,
    headers,
):
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(client, target_id, -1, headers)
    assert response.status_code in (401, 403), response.text

    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_other_member_sees_updated_quantity_in_persisted_home_state(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    actor_headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"][
        "name"
    ]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_name)
    assert before_product is not None
    initial_quantity = before_product["quantity"]

    response = modify_product_request(client, target_id, -1, actor_headers)
    assert response.status_code == 200, response.text
    assert response.json()["code"] == "PRODUCT_QUANTITY_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_name)
    assert after_product is not None
    assert after_product["quantity"] == initial_quantity - 1
