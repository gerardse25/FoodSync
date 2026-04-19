import pytest


def delete_product_request(client, product_id, headers):
    return client.request(
        "DELETE",
        "/inventory_delete_product",
        json={"id_producte": str(product_id)},
        headers=headers,
    )


def test_can_delete_existing_product(client, shared_home_with_products, list_home_products_db):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(client, target_id, headers)
    assert delete_response.status_code == 200, delete_response.text

    body = delete_response.json()
    assert body["code"] == "PRODUCT_DELETED"

    after_products = list_home_products_db(home_id)
    assert all(product["name"] != target_name for product in after_products)


def test_can_delete_only_product_in_inventory(client, shared_home_with_single_product, list_home_products_db):
    headers = shared_home_with_single_product["owner_headers"]
    home_id = shared_home_with_single_product["home_id"]
    only_product_id = shared_home_with_single_product["products"]["only_product"]["db"]["id"]
    only_product_name = shared_home_with_single_product["products"]["only_product"]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    assert len(before_products) == 1
    assert before_products[0]["name"] == only_product_name

    delete_response = delete_product_request(client, only_product_id, headers)
    assert delete_response.status_code == 200, delete_response.text

    body = delete_response.json()
    assert body["code"] == "PRODUCT_DELETED"

    after_products = list_home_products_db(home_id)
    assert after_products == []


def test_deleting_non_existing_product_returns_error(client, shared_home_with_products):
    headers = shared_home_with_products["owner_headers"]

    delete_response = delete_product_request(client, 999999, headers)
    assert delete_response.status_code == 404, delete_response.text

    body = delete_response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"


def test_deleting_product_with_non_numeric_id_returns_error(client, shared_home_with_products):
    headers = shared_home_with_products["owner_headers"]

    delete_response = delete_product_request(client, "abc", headers)
    assert delete_response.status_code == 400, delete_response.text

    body = delete_response.json()
    assert body["code"] == "PRODUCT_ID_INVALID"


def test_cannot_delete_private_product_owned_by_another_user(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["member1_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["owner_private"]["db"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(client, target_id, headers)
    assert delete_response.status_code == 403, delete_response.text

    body = delete_response.json()
    assert body["code"] == "PRODUCT_DELETE_FORBIDDEN"

    after_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in after_products)


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_delete_product(
    client,
    shared_home_with_products,
    headers,
    list_home_products_db,
):
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(client, target_id, headers)
    assert delete_response.status_code in (401, 403), delete_response.text

    body = delete_response.json()
    assert body["code"] == "AUTH_REQUIRED"

    after_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in after_products)


def test_non_member_cannot_delete_product(
    client,
    shared_home_with_products,
    outsider_user,
    list_home_products_db,
):
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(client, target_id, outsider_user["headers"])
    assert delete_response.status_code == 404, delete_response.text

    body = delete_response.json()
    assert body["code"] == "NOT_IN_HOME"

    after_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in after_products)


def test_deleted_product_is_removed_from_persisted_home_state(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(client, target_id, headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "PRODUCT_DELETED"

    after_products = list_home_products_db(home_id)
    assert all(product["name"] != target_name for product in after_products)

