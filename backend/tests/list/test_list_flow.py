import uuid

import pytest


SHOPPING_LIST_ENDPOINT = "/shopping-list"


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
        f"{SHOPPING_LIST_ENDPOINT}/{home_id}",
        json={
            "product_name": product_name,
            "quantity": quantity,
            "notes": notes,
        },
        headers=headers,
    )


def get_list(client, home_id, headers):
    return client.get(f"{SHOPPING_LIST_ENDPOINT}/{home_id}", headers=headers)


def update_item(client, item_id, headers, *, quantity=None, extra_payload=None):
    payload = {}
    if quantity is not None:
        payload["quantity"] = quantity
    if extra_payload:
        payload.update(extra_payload)

    return client.put(
        f"{SHOPPING_LIST_ENDPOINT}/item/{item_id}",
        json=payload,
        headers=headers,
    )


def delete_item(client, item_id, headers):
    return client.delete(
        f"{SHOPPING_LIST_ENDPOINT}/item/{item_id}",
        headers=headers,
    )


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


def test_owner_can_add_view_update_and_delete_item_in_full_flow(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    initial_get = get_list(client, home_id, headers)
    initial_body = assert_success_response(initial_get, 200, "LIST_RETRIEVED")
    assert initial_body["items"] == []

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
        notes="semi-skimmed",
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    after_add = get_list(client, home_id, headers)
    after_add_body = assert_success_response(after_add, 200, "LIST_RETRIEVED")
    assert len(after_add_body["items"]) == 1
    assert after_add_body["items"][0]["id"] == item_id
    assert after_add_body["items"][0]["product_name"] == "Milk"
    assert after_add_body["items"][0]["quantity"] == 2
    assert after_add_body["items"][0]["notes"] == "semi-skimmed"

    update_response = update_item(
        client,
        item_id,
        headers,
        quantity=4,
    )
    update_body = assert_success_response(update_response, 200, "LIST_ITEM_UPDATED")
    assert update_body["data"]["id"] == item_id
    assert update_body["data"]["product_name"] == "Milk"
    assert update_body["data"]["quantity"] == 4
    assert update_body["data"]["notes"] == "semi-skimmed"

    after_update = get_list(client, home_id, headers)
    after_update_body = assert_success_response(after_update, 200, "LIST_RETRIEVED")
    assert len(after_update_body["items"]) == 1
    assert after_update_body["items"][0]["id"] == item_id
    assert after_update_body["items"][0]["product_name"] == "Milk"
    assert after_update_body["items"][0]["quantity"] == 4
    assert after_update_body["items"][0]["notes"] == "semi-skimmed"

    delete_response = delete_item(client, item_id, headers)
    delete_body = assert_success_response(delete_response, 200, "LIST_ITEM_DELETED")
    assert delete_body["data"]["id"] == item_id

    final_get = get_list(client, home_id, headers)
    final_body = assert_success_response(final_get, 200, "LIST_RETRIEVED")
    assert final_body["items"] == []


def test_member_can_see_and_modify_item_created_by_owner(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]
    member_headers = shared_home_setup["member1_headers"]

    add_response = add_item(
        client,
        home_id,
        owner_headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    get_response = get_list(client, home_id, member_headers)
    get_body = assert_success_response(get_response, 200, "LIST_RETRIEVED")
    assert len(get_body["items"]) == 1
    assert get_body["items"][0]["id"] == item_id
    assert get_body["items"][0]["product_name"] == "Bread"

    update_response = update_item(
        client,
        item_id,
        member_headers,
        quantity=2,
    )
    update_body = assert_success_response(update_response, 200, "LIST_ITEM_UPDATED")
    assert update_body["data"]["product_name"] == "Bread"
    assert update_body["data"]["quantity"] == 2
    assert update_body["data"]["notes"] == "whole grain"

    delete_response = delete_item(client, item_id, member_headers)
    delete_body = assert_success_response(delete_response, 200, "LIST_ITEM_DELETED")
    assert delete_body["data"]["id"] == item_id

    final_get = get_list(client, home_id, owner_headers)
    final_body = assert_success_response(final_get, 200, "LIST_RETRIEVED")
    assert final_body["items"] == []


def test_add_merge_view_update_then_delete_flow(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_add = add_item(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=2,
        notes="basmati",
    )
    first_add_body = assert_success_response(first_add, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = first_add_body["data"]["id"]

    second_add = add_item(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=3,
    )
    second_add_body = assert_success_response(second_add, 200, "LIST_ITEM_UPDATED")
    assert second_add_body["data"]["id"] == item_id
    assert second_add_body["data"]["quantity"] == 5

    after_merge = get_list(client, home_id, headers)
    after_merge_body = assert_success_response(after_merge, 200, "LIST_RETRIEVED")
    assert len(after_merge_body["items"]) == 1
    assert after_merge_body["items"][0]["id"] == item_id
    assert after_merge_body["items"][0]["product_name"] == "Rice"
    assert after_merge_body["items"][0]["quantity"] == 5
    assert after_merge_body["items"][0]["notes"] == "basmati"

    update_response = update_item(
        client,
        item_id,
        headers,
        quantity=7,
    )
    update_body = assert_success_response(update_response, 200, "LIST_ITEM_UPDATED")
    assert update_body["data"]["product_name"] == "Rice"
    assert update_body["data"]["quantity"] == 7
    assert update_body["data"]["notes"] == "basmati"

    after_update = get_list(client, home_id, headers)
    after_update_body = assert_success_response(after_update, 200, "LIST_RETRIEVED")
    assert len(after_update_body["items"]) == 1
    assert after_update_body["items"][0]["id"] == item_id
    assert after_update_body["items"][0]["product_name"] == "Rice"
    assert after_update_body["items"][0]["quantity"] == 7
    assert after_update_body["items"][0]["notes"] == "basmati"

    delete_response = delete_item(client, item_id, headers)
    assert_success_response(delete_response, 200, "LIST_ITEM_DELETED")

    final_get = get_list(client, home_id, headers)
    final_body = assert_success_response(final_get, 200, "LIST_RETRIEVED")
    assert final_body["items"] == []


def test_spaces_are_normalized_consistently_across_add_get_and_update(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="   Milk   ",
        quantity=1,
        notes="   semi-skimmed   ",
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    assert add_body["data"]["product_name"] == "Milk"
    assert add_body["data"]["notes"] == "semi-skimmed"

    get_response = get_list(client, home_id, headers)
    get_body = assert_success_response(get_response, 200, "LIST_RETRIEVED")
    assert len(get_body["items"]) == 1
    assert get_body["items"][0]["product_name"] == "Milk"
    assert get_body["items"][0]["notes"] == "semi-skimmed"

    update_response = update_item(
        client,
        item_id,
        headers,
        quantity=3,
    )
    update_body = assert_success_response(update_response, 200, "LIST_ITEM_UPDATED")

    assert update_body["data"]["product_name"] == "Milk"
    assert update_body["data"]["quantity"] == 3
    assert update_body["data"]["notes"] == "semi-skimmed"

    final_get = get_list(client, home_id, headers)
    final_body = assert_success_response(final_get, 200, "LIST_RETRIEVED")
    assert len(final_body["items"]) == 1
    assert final_body["items"][0]["product_name"] == "Milk"
    assert final_body["items"][0]["quantity"] == 3
    assert final_body["items"][0]["notes"] == "semi-skimmed"


@pytest.mark.parametrize("notes_value", ["", " "])
def test_empty_or_blank_notes_are_handled_consistently_across_add_update_and_get(
    client,
    shared_home_setup,
    notes_value,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="Apple",
        quantity=2,
        notes=notes_value,
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    assert add_body["data"]["notes"] == ""

    after_add = get_list(client, home_id, headers)
    after_add_body = assert_success_response(after_add, 200, "LIST_RETRIEVED")
    assert len(after_add_body["items"]) == 1
    assert after_add_body["items"][0]["notes"] == ""

    update_response = update_item(
        client,
        item_id,
        headers,
        quantity=5,
    )
    update_body = assert_success_response(update_response, 200, "LIST_ITEM_UPDATED")
    assert update_body["data"]["notes"] == ""

    final_get = get_list(client, home_id, headers)
    final_body = assert_success_response(final_get, 200, "LIST_RETRIEVED")
    assert len(final_body["items"]) == 1
    assert final_body["items"][0]["notes"] == ""


def test_item_cannot_be_updated_or_deleted_after_being_deleted(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="Banana",
        quantity=3,
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    delete_response = delete_item(client, item_id, headers)
    assert_success_response(delete_response, 200, "LIST_ITEM_DELETED")

    update_after_delete = update_item(
        client,
        item_id,
        headers,
        quantity=5,
    )
    assert_item_not_found(update_after_delete)

    delete_again = delete_item(client, item_id, headers)
    assert_item_not_found(delete_again)


def test_user_without_authentication_cannot_run_flow_operations(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    add_response = add_item(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    unauth_get = get_list(client, home_id, {})
    assert_auth_required(unauth_get)

    unauth_add = add_item(
        client,
        home_id,
        {},
        product_name="Bread",
        quantity=1,
    )
    assert_auth_required(unauth_add)

    unauth_update = update_item(
        client,
        item_id,
        {},
        quantity=3,
    )
    assert_auth_required(unauth_update)

    unauth_delete = delete_item(client, item_id, {})
    assert_auth_required(unauth_delete)


def test_outsider_cannot_run_flow_operations_on_foreign_home(client, shared_home_setup, outsider_user):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    add_response = add_item(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    outsider_get = get_list(client, home_id, outsider_user["headers"])
    assert_not_in_home(outsider_get)

    outsider_add = add_item(
        client,
        home_id,
        outsider_user["headers"],
        product_name="Bread",
        quantity=1,
    )
    assert_not_in_home(outsider_add)

    outsider_update = update_item(
        client,
        item_id,
        outsider_user["headers"],
        quantity=3,
    )
    assert_not_in_home(outsider_update)

    outsider_delete = delete_item(client, item_id, outsider_user["headers"])
    assert_not_in_home(outsider_delete)


def test_flow_operations_fail_when_home_becomes_inactive(client, private_home_setup):
    home_id = private_home_setup["home_id"]
    headers = private_home_setup["headers"]

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
    )
    add_body = assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")
    item_id = add_body["data"]["id"]

    deactivate_home(client, home_id)

    get_response = get_list(client, home_id, headers)
    assert_home_not_found(get_response)

    update_response = update_item(
        client,
        item_id,
        headers,
        quantity=3,
    )
    assert_home_not_found(update_response)

    delete_response = delete_item(client, item_id, headers)
    assert_home_not_found(delete_response)


def test_database_state_matches_full_flow_result(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    add_1 = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
        notes="semi-skimmed",
    )
    milk_body = assert_success_response(add_1, 201, "PRODUCT_ADDED_TO_LIST")
    milk_id = milk_body["data"]["id"]

    add_2 = add_item(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )
    bread_body = assert_success_response(add_2, 201, "PRODUCT_ADDED_TO_LIST")
    bread_id = bread_body["data"]["id"]

    update_response = update_item(
        client,
        milk_id,
        headers,
        quantity=3,
    )
    assert_success_response(update_response, 200, "LIST_ITEM_UPDATED")

    delete_response = delete_item(client, bread_id, headers)
    assert_success_response(delete_response, 200, "LIST_ITEM_DELETED")

    get_response = get_list(client, home_id, headers)
    get_body = assert_success_response(get_response, 200, "LIST_RETRIEVED")

    assert len(get_body["items"]) == 1
    assert get_body["items"][0]["id"] == milk_id
    assert get_body["items"][0]["product_name"] == "Milk"
    assert get_body["items"][0]["quantity"] == 3
    assert get_body["items"][0]["notes"] == "semi-skimmed"

    db_items = list_shopping_items_db(client, home_id)
    assert len(db_items) == 1
    assert db_items[0]["id"] == milk_id
    assert db_items[0]["product_name"] == "Milk"
    assert db_items[0]["quantity"] == 3
    assert db_items[0]["notes"] == "semi-skimmed"