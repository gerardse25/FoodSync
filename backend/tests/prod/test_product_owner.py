import pytest
import uuid


def assert_backend_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "detail" in body


def test_can_add_private_product_assigned_to_specific_member(
    client,
    shared_home_setup,
    make_product_data,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    member1_id = shared_home_setup["member1"]["user"]["id"]

    product = make_product_data(
        name="member1 assigned private product",
        price="2.40",
        category="dairy",
        quantity=1,
        owner_user_id=member1_id,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["product"]["owner_user_id"] == member1_id
    assert body["product"]["is_private"] is True

    products = list_home_products_db(home_id)
    created_product = next((item for item in products if item["name"] == product["name"]), None)
    assert created_product is not None
    assert created_product["owner_user_id"] == member1_id
    assert created_product["is_private"] is True


def test_can_add_product_without_specific_owner_as_public(
    client,
    shared_home_setup,
    make_product_data,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_product_data(
        name="public product without owner",
        price="1.10",
        category="vegetables",
        quantity=2,
        owner_user_id=None,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"
    assert body["product"]["owner_user_id"] is None
    assert body["product"]["is_private"] is False

    products = list_home_products_db(home_id)
    created_product = next((item for item in products if item["name"] == product["name"]), None)
    assert created_product is not None
    assert created_product["owner_user_id"] is None
    assert created_product["is_private"] is False


def test_cannot_assign_product_to_user_who_is_not_member_of_home(
    client,
    shared_home_setup,
    outsider_user,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="product assigned to outsider",
        price="2.00",
        category="dairy",
        quantity=1,
        owner_user_id=outsider_user["user"]["id"],
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 400, "OWNER_NOT_IN_HOME")


def test_cannot_assign_product_to_non_existing_user(
    client,
    shared_home_setup,
    make_product_data,
):
    headers = shared_home_setup["owner_headers"]

    product = make_product_data(
        name="product assigned to non existing user",
        price="2.00",
        category="dairy",
        quantity=1,
        owner_user_id=str(uuid.uuid4()),
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert_backend_error(response, 400, "OWNER_NOT_IN_HOME")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_assign_product_owner(
    client,
    shared_home_setup,
    make_product_data,
    headers,
):
    member1_id = shared_home_setup["member1"]["user"]["id"]

    product = make_product_data(
        name="unauthenticated assigned product",
        price="2.00",
        category="dairy",
        quantity=1,
        owner_user_id=member1_id,
    )

    response = client.post("/products/manual", json=product, headers=headers)

    assert response.status_code in (401, 403), response.text