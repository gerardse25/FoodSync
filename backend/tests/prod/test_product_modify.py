import pytest

MODIFY_PRODUCT_ENDPOINT_PREFIX = "/inventory_modify"
DETAIL_ENDPOINT_PREFIX = "/inventory"


def modify_product_request(client, product_id, payload, headers):
    return client.patch(
        f"{MODIFY_PRODUCT_ENDPOINT_PREFIX}/{product_id}",
        json=payload,
        headers=headers,
    )


def get_product_detail_request(client, product_id, headers):
    return client.get(f"{DETAIL_ENDPOINT_PREFIX}/{product_id}", headers=headers)


def get_product_by_id(products, target_id):
    return next((product for product in products if str(product["id"]) == str(target_id)), None)


def assert_backend_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "error" in body or "detail" in body


def assert_pydantic_validation_error(response):
    assert response.status_code == 422, response.text
    body = response.json()
    assert "detail" in body


def test_can_modify_product_basic_fields_and_changes_persist_in_db(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    payload = {
        "nom": "  updated rice product  ",
        "categoria": "MILK",
        "preu": "2.50",
        "data_caducitat": "2026-05-20",
    }

    response = modify_product_request(client, target_id, payload, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_UPDATED"
    assert body["producte"]["id_producte"] == str(target_id)
    assert body["producte"]["nom"] == "updated rice product"
    assert body["producte"]["categoria"] == "Llet"
    assert body["producte"]["preu"] == "2.50"
    assert body["producte"]["data_caducitat"] == "2026-05-20"

    products = list_home_products_db(home_id)
    updated_product = get_product_by_id(products, target_id)
    assert updated_product is not None
    assert updated_product["name"] == "updated rice product"
    assert updated_product["category"] == "Llet"
    assert updated_product["price"] == "2.50"
    assert updated_product["expiration_date"] == "2026-05-20"

    detail_response = get_product_detail_request(client, target_id, headers)
    assert detail_response.status_code == 200, detail_response.text
    detail_body = detail_response.json()
    assert detail_body["producte"]["nom"] == "updated rice product"
    assert detail_body["producte"]["categoria"] == "Llet"
    assert detail_body["producte"]["preu"] == "2.50"
    assert detail_body["producte"]["data_caducitat"] == "2026-05-20"


def test_modify_product_allows_internal_spaces_in_name_and_trims_edges(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    payload = {
        "nom": "  olive oil extra virgin  ",
    }

    response = modify_product_request(client, target_id, payload, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_UPDATED"
    assert body["producte"]["nom"] == "olive oil extra virgin"

    products = list_home_products_db(home_id)
    updated_product = get_product_by_id(products, target_id)
    assert updated_product is not None
    assert updated_product["name"] == "olive oil extra virgin"


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "   ",
    ],
)
def test_modify_product_rejects_empty_name(
    client,
    shared_home_with_products,
    invalid_name,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": invalid_name},
        headers,
    )

    assert_backend_error(response, 422, "NAME_REQUIRED")


@pytest.mark.parametrize(
    "invalid_name",
    [
        "milk\n",
        "milk\t",
        "milk\r",
        "milk\\n",
        "milk\\t",
    ],
)
def test_modify_product_rejects_control_or_escape_characters_in_name(
    client,
    shared_home_with_products,
    invalid_name,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": invalid_name},
        headers,
    )

    assert_backend_error(response, 400, "NAME_INVALID_CHARACTERS")


def test_modify_product_rejects_name_too_long(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": "a" * 101},
        headers,
    )

    assert_backend_error(response, 422, "NAME_TOO_LONG")


def test_modify_product_accepts_short_name_if_not_empty(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": "a"},
        headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_UPDATED"
    assert body["producte"]["nom"] == "a"

    products = list_home_products_db(home_id)
    updated_product = get_product_by_id(products, target_id)
    assert updated_product is not None
    assert updated_product["name"] == "a"


def test_modify_product_rejects_negative_price(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"preu": "-1.00"},
        headers,
    )

    assert_backend_error(response, 400, "PRICE_INVALID")


def test_modify_product_rejects_price_with_more_than_two_decimals(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"preu": "2.345"},
        headers,
    )

    assert_backend_error(response, 400, "PRICE_INVALID")


@pytest.mark.parametrize("invalid_price", ["1,50", "abc", "12.3.4", "10 euros"])
def test_modify_product_rejects_invalid_price_format_before_business_validation(
    client,
    shared_home_with_products,
    invalid_price,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"preu": invalid_price},
        headers,
    )

    assert_pydantic_validation_error(response)


def test_modify_product_rejects_invalid_category_enum(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"categoria": "NOT_A_REAL_CATEGORY"},
        headers,
    )

    assert_pydantic_validation_error(response)


def test_modify_product_rejects_invalid_expiration_date_format(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"data_caducitat": "31/12/2026"},
        headers,
    )

    assert_pydantic_validation_error(response)


def test_modifying_non_existing_product_returns_error(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = modify_product_request(
        client,
        999999,
        {"nom": "updated"},
        headers,
    )

    assert_backend_error(response, 404, "PRODUCT_NOT_FOUND")


def test_modifying_product_with_non_numeric_id_returns_error(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = modify_product_request(
        client,
        "abc",
        {"nom": "updated"},
        headers,
    )

    assert_backend_error(response, 400, "PRODUCT_ID_INVALID")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_modify_product_info(
    client,
    shared_home_with_products,
    headers,
):
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": "updated"},
        headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_non_member_cannot_modify_product_info(
    client,
    shared_home_with_products,
    outsider_user,
):
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": "updated"},
        outsider_user["headers"],
    )

    assert_backend_error(response, 403, "NOT_IN_HOME")


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

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_id(before_products, target_id)
    assert before_product is not None
    initial_name = before_product["name"]
    initial_price = before_product["price"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": "forbidden update", "preu": "9.99"},
        headers,
    )

    assert_backend_error(response, 403, "PRODUCT_MODIFICATION_FORBIDDEN")

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_id(after_products, target_id)
    assert after_product is not None
    assert after_product["name"] == initial_name
    assert after_product["price"] == initial_price


def test_owner_can_modify_own_private_product_info_and_changes_persist(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["owner_private"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": "owner private updated", "preu": "3.40"},
        headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_UPDATED"
    assert body["producte"]["nom"] == "owner private updated"
    assert body["producte"]["preu"] == "3.40"

    products = list_home_products_db(home_id)
    updated_product = get_product_by_id(products, target_id)
    assert updated_product is not None
    assert updated_product["name"] == "owner private updated"
    assert updated_product["price"] == "3.40"


def test_member_can_modify_own_private_product_info_and_changes_persist(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["member1_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["member1_private"]["db"]["id"]

    response = modify_product_request(
        client,
        target_id,
        {"nom": "member private updated", "preu": "4.20"},
        headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_UPDATED"
    assert body["producte"]["nom"] == "member private updated"
    assert body["producte"]["preu"] == "4.20"

    products = list_home_products_db(home_id)
    updated_product = get_product_by_id(products, target_id)
    assert updated_product is not None
    assert updated_product["name"] == "member private updated"
    assert updated_product["price"] == "4.20"