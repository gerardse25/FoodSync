import uuid

import pytest


SHOPPING_LIST_ADD_ENDPOINT = "/shopping-list"
SHOPPING_LIST_DELETE_ENDPOINT = "/shopping-list"


def deactivate_home(client, home_id):
    db = client.db_session_factory()
    try:
        home_models = client.app_modules["home_models"]
        Home = home_models.Home

        row = db.query(Home).filter(Home.id == uuid.UUID(str(home_id))).first()
        assert row is not None
        row.is_active = False
        db.commit()
    finally:
        db.close()


def list_shopping_items_db(client, home_id):
    db = client.db_session_factory()
    try:
        shopping_models = client.app_modules["shopping_list_models"]
        ShoppingListItem = shopping_models.ShoppingListItem

        rows = (
            db.query(ShoppingListItem)
            .filter(ShoppingListItem.home_id == uuid.UUID(str(home_id)))
            .all()
        )

        return [
            {
                "id": str(row.id),
                "home_id": str(row.home_id),
                "product_name": row.product_name,
                "quantity": row.quantity,
                "notes": row.notes,
            }
            for row in rows
        ]
    finally:
        db.close()


def add_item(client, home_id, headers, *, product_name, quantity, notes=None):
    return client.post(
        f"{SHOPPING_LIST_ADD_ENDPOINT}/{home_id}",
        json={
            "product_name": product_name,
            "quantity": quantity,
            "notes": notes,
        },
        headers=headers,
    )


def delete_item(client, home_id, item_id, headers):
    return client.delete(
        f"{SHOPPING_LIST_DELETE_ENDPOINT}/{home_id}/{item_id}",
        headers=headers,
    )


def create_item_and_get_id(client, home_id, headers, *, product_name, quantity, notes=None):
    response = add_item(
        client,
        home_id,
        headers,
        product_name=product_name,
        quantity=quantity,
        notes=notes,
    )
    body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")
    return body["data"]["id"]


def assert_success_response(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    return body


def assert_auth_required(response):
    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def assert_not_in_home(response):
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


def assert_home_not_found(response):
    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "HOME_NOT_FOUND"


def assert_item_not_found(response):
    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "LIST_ITEM_NOT_FOUND"


def test_owner_can_delete_existing_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
        notes="semi-skimmed",
    )

    response = delete_item(client, home_id, item_id, headers)

    body = assert_success_response(response, 200, "LIST_ITEM_DELETED")
    assert body["message"] == "Producte eliminat de la llista de la compra."
    assert body["data"]["id"] == item_id

    items = list_shopping_items_db(client, home_id)
    assert items == []


def test_member_can_delete_existing_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]
    member_headers = shared_home_setup["member1_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Eggs",
        quantity=6,
        notes="free-range",
    )

    response = delete_item(client, home_id, item_id, member_headers)

    body = assert_success_response(response, 200, "LIST_ITEM_DELETED")
    assert body["data"]["id"] == item_id

    items = list_shopping_items_db(client, home_id)
    assert items == []


def test_deleting_one_item_keeps_other_items_unchanged(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id_to_delete = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
        notes="semi-skimmed",
    )

    other_item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )

    response = delete_item(client, home_id, item_id_to_delete, headers)

    body = assert_success_response(response, 200, "LIST_ITEM_DELETED")
    assert body["data"]["id"] == item_id_to_delete

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["id"] == other_item_id
    assert items[0]["product_name"] == "Bread"
    assert items[0]["quantity"] == 1
    assert items[0]["notes"] == "whole grain"


def test_deleting_last_item_leaves_shopping_list_empty(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=3,
    )

    delete_response = delete_item(client, home_id, item_id, headers)
    assert_success_response(delete_response, 200, "LIST_ITEM_DELETED")

    items = list_shopping_items_db(client, home_id)
    assert items == []


def test_deleted_item_cannot_be_deleted_twice(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Tomato",
        quantity=4,
    )

    first_response = delete_item(client, home_id, item_id, headers)
    assert_success_response(first_response, 200, "LIST_ITEM_DELETED")

    second_response = delete_item(client, home_id, item_id, headers)
    assert_item_not_found(second_response)


def test_user_without_authentication_cannot_delete_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )

    response = delete_item(client, home_id, item_id, {})

    assert_auth_required(response)


def test_user_with_invalid_token_cannot_delete_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )

    response = delete_item(
        client,
        home_id,
        item_id,
        {"Authorization": "Bearer invalid-token"},
    )

    assert_auth_required(response)


def test_user_not_in_home_cannot_delete_item(client, shared_home_setup, outsider_user):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )

    response = delete_item(client, home_id, item_id, outsider_user["headers"])

    assert_not_in_home(response)


def test_user_from_other_home_cannot_delete_foreign_item(
    client,
    shared_home_setup,
    private_home_setup,
):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )

    response = delete_item(client, home_id, item_id, private_home_setup["headers"])

    assert_not_in_home(response)


def test_cannot_delete_non_existing_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]
    fake_item_id = str(uuid.uuid4())

    response = delete_item(client, home_id, fake_item_id, headers)

    assert_item_not_found(response)


def test_cannot_delete_item_when_home_is_inactive(client, private_home_setup):
    home_id = private_home_setup["home_id"]
    headers = private_home_setup["headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
    )

    deactivate_home(client, home_id)

    response = delete_item(client, home_id, item_id, headers)

    assert_home_not_found(response)


def test_delete_item_removes_correct_item_when_multiple_items_exist(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    milk_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
    )

    eggs_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Eggs",
        quantity=6,
    )

    bread_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
    )

    response = delete_item(client, home_id, eggs_id, headers)

    body = assert_success_response(response, 200, "LIST_ITEM_DELETED")
    assert body["data"]["id"] == eggs_id

    items = list_shopping_items_db(client, home_id)
    item_ids = {item["id"] for item in items}

    assert item_ids == {milk_id, bread_id}
    assert eggs_id not in item_ids


def test_delete_item_does_not_affect_items_from_other_home(
    client,
    shared_home_setup,
    private_home_setup,
):
    shared_home_id = shared_home_setup["home_id"]
    shared_headers = shared_home_setup["owner_headers"]

    private_home_id = private_home_setup["home_id"]
    private_headers = private_home_setup["headers"]

    shared_item_id = create_item_and_get_id(
        client,
        shared_home_id,
        shared_headers,
        product_name="Shared item",
        quantity=2,
    )

    private_item_id = create_item_and_get_id(
        client,
        private_home_id,
        private_headers,
        product_name="Private item",
        quantity=1,
    )

    response = delete_item(client, shared_home_id, shared_item_id, shared_headers)
    assert_success_response(response, 200, "LIST_ITEM_DELETED")

    shared_items = list_shopping_items_db(client, shared_home_id)
    private_items = list_shopping_items_db(client, private_home_id)

    assert shared_items == []
    assert len(private_items) == 1
    assert private_items[0]["id"] == private_item_id
    assert private_items[0]["product_name"] == "Private item"


def test_delete_item_reflects_change_in_database(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Apple",
        quantity=5,
        notes="green",
    )

    before_items = list_shopping_items_db(client, home_id)
    assert len(before_items) == 1
    assert before_items[0]["id"] == item_id

    response = delete_item(client, home_id, item_id, headers)

    body = assert_success_response(response, 200, "LIST_ITEM_DELETED")
    assert body["data"]["id"] == item_id

    after_items = list_shopping_items_db(client, home_id)
    assert after_items == []