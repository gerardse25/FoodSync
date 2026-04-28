import pytest

INVENTORY_OWNERS_ENDPOINT = "/inventory/owners"
MODIFY_ENDPOINT = "/inventory_modify"


def delete_product_request(client, product_id, headers):
    return client.request(
        "DELETE",
        "/inventory_delete_product",
        json={"id_producte": str(product_id)},
        headers=headers,
    )


def modify_owner_product_request(client, product_id, owner_ids, headers):
    return client.patch(
        INVENTORY_OWNERS_ENDPOINT,
        json={
            "id_producte": str(product_id),
            "owner_user_ids": owner_ids,
        },
        headers=headers,
    )


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


def test_can_delete_existing_product(
    client, shared_home_with_products, list_home_products_db
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]
    target_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"][
        "name"
    ]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(client, target_id, headers)
    assert delete_response.status_code == 200, delete_response.text

    body = delete_response.json()
    assert body["code"] == "PRODUCT_DELETED"

    after_products = list_home_products_db(home_id)
    assert all(product["name"] != target_name for product in after_products)


def test_can_delete_only_product_in_inventory(
    client, shared_home_with_single_product, list_home_products_db
):
    headers = shared_home_with_single_product["owner_headers"]
    home_id = shared_home_with_single_product["home_id"]
    only_product_id = shared_home_with_single_product["products"]["only_product"]["db"][
        "id"
    ]
    only_product_name = shared_home_with_single_product["products"]["only_product"][
        "payload"
    ]["name"]

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


def test_deleting_product_with_non_numeric_id_returns_error(
    client, shared_home_with_products
):
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
    target_name = shared_home_with_products["products"]["owner_private"]["payload"][
        "name"
    ]

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
    target_name = shared_home_with_products["products"]["public_product"]["payload"][
        "name"
    ]

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
    target_name = shared_home_with_products["products"]["public_product"]["payload"][
        "name"
    ]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(
        client, target_id, outsider_user["headers"]
    )
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
    target_name = shared_home_with_products["products"]["public_product"]["payload"][
        "name"
    ]

    before_products = list_home_products_db(home_id)
    assert any(product["name"] == target_name for product in before_products)

    delete_response = delete_product_request(client, target_id, headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "PRODUCT_DELETED"

    after_products = list_home_products_db(home_id)
    assert all(product["name"] != target_name for product in after_products)


def test_can_delete_product_with_multiple_owners(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    owner_headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["public_product"]["db"][
        "name"
    ]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    member1_id = shared_home_with_products["member1"]["user"]["id"]

    # Primero convertimos el producto en privado con dos owners
    update_response = modify_owner_product_request(
        client,
        target_product_id,
        [owner_id, member1_id],
        owner_headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["code"] == "PRODUCT_OWNERS_UPDATED"

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_product_name)
    assert before_product is not None
    assert before_product["owner_user_ids"] == [owner_id, member1_id]
    assert before_product["is_private"] is True

    delete_response = delete_product_request(client, target_product_id, owner_headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "PRODUCT_DELETED"

    after_products = list_home_products_db(home_id)
    assert get_product_by_name(after_products, target_product_name) is None


def test_owner_can_delete_own_private_product(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_product_id = shared_home_with_products["products"]["owner_private"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["owner_private"]["db"][
        "name"
    ]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_product_name)
    assert before_product is not None
    assert before_product["owner_user_ids"] != []

    delete_response = delete_product_request(client, target_product_id, headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "PRODUCT_DELETED"

    after_products = list_home_products_db(home_id)
    assert get_product_by_name(after_products, target_product_name) is None


def test_deleted_product_detail_returns_not_found(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]

    delete_response = delete_product_request(client, target_product_id, headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "PRODUCT_DELETED"

    detail_response = client.get(f"/inventory/{target_product_id}", headers=headers)
    assert detail_response.status_code == 404, detail_response.text

    body = detail_response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"


def test_deleted_product_cannot_be_modified_after_delete(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]

    delete_response = delete_product_request(client, target_product_id, headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "PRODUCT_DELETED"

    modify_response = modify_product_request(client, target_product_id, -1, headers)
    assert modify_response.status_code == 404, modify_response.text

    body = modify_response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"
