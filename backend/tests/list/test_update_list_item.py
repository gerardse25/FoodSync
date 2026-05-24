import uuid

import pytest


SHOPPING_LIST_ADD_ENDPOINT = "/shopping-list"
SHOPPING_LIST_UPDATE_ENDPOINT = "/shopping-list"


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


def update_item(client, home_id, item_id, headers, *, quantity=None, extra_payload=None):
    payload = {}
    if quantity is not None:
        payload["quantity"] = quantity
    if extra_payload:
        payload.update(extra_payload)

    return client.patch(
        f"/shopping-list/{home_id}/{item_id}",
        json=payload,
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


def assert_validation_error(response, expected_code):
    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == expected_code
    return body


def test_owner_can_update_item_quantity(client, shared_home_setup):
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

    response = update_item(
        client,
        home_id,
        item_id,
        headers,
        quantity=4,
    )

    body = assert_success_response(response, 200, "LIST_ITEM_UPDATED")

    assert body["data"]["id"] == item_id
    assert body["data"]["product_name"] == "Milk"
    assert body["data"]["quantity"] == 4
    assert body["data"]["notes"] == "semi-skimmed"

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Milk"
    assert items[0]["quantity"] == 4
    assert items[0]["notes"] == "semi-skimmed"


def test_member_can_update_shopping_list_item_quantity(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]
    member_headers = shared_home_setup["member1_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )

    response = update_item(
        client,
        home_id,
        item_id,
        member_headers,
        quantity=2,
    )

    body = assert_success_response(response, 200, "LIST_ITEM_UPDATED")
    assert body["data"]["product_name"] == "Bread"
    assert body["data"]["quantity"] == 2
    assert body["data"]["notes"] == "whole grain"


def test_update_quantity_keeps_product_name_and_notes(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Eggs",
        quantity=6,
        notes="free-range",
    )

    response = update_item(
        client,
        home_id,
        item_id,
        headers,
        quantity=12,
    )

    body = assert_success_response(response, 200, "LIST_ITEM_UPDATED")
    assert body["data"]["product_name"] == "Eggs"
    assert body["data"]["quantity"] == 12
    assert body["data"]["notes"] == "free-range"


@pytest.mark.parametrize("invalid_quantity", [0, -1])
def test_update_rejects_invalid_quantity(client, shared_home_setup, invalid_quantity):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
    )

    response = update_item(
        client,
        home_id,
        item_id,
        headers,
        quantity=invalid_quantity,
    )

    assert_validation_error(response, "INVALID_QUANTITY")


def test_update_rejects_payload_without_quantity(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
    )

    response = client.patch(
        f"{SHOPPING_LIST_UPDATE_ENDPOINT}/{home_id}/{item_id}",
        json={},
        headers=headers,
    )

    assert_validation_error(response, "NO_FIELDS_TO_UPDATE")


def test_update_rejects_payload_with_only_product_name(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
        notes="semi-skimmed",
    )

    response = client.patch(
        f"{SHOPPING_LIST_UPDATE_ENDPOINT}/{home_id}/{item_id}",
        json={"product_name": "Oat milk"},
        headers=headers,
    )

    assert_validation_error(response, "ONLY_QUANTITY_CAN_BE_UPDATED")


def test_update_rejects_payload_with_only_notes(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )

    response = client.patch(
        f"{SHOPPING_LIST_UPDATE_ENDPOINT}/{home_id}/{item_id}",
        json={"notes": "barista"},
        headers=headers,
    )

    assert_validation_error(response, "ONLY_QUANTITY_CAN_BE_UPDATED")


def test_update_rejects_payload_with_quantity_and_product_name(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=2,
        notes="basmati",
    )

    response = client.patch(
        f"{SHOPPING_LIST_UPDATE_ENDPOINT}/{home_id}/{item_id}",
        json={"quantity": 5, "product_name": "Brown rice"},
        headers=headers,
    )

    assert_validation_error(response, "ONLY_QUANTITY_CAN_BE_UPDATED")


def test_update_rejects_payload_with_quantity_and_notes(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Tomato",
        quantity=3,
        notes="for salad",
    )

    response = client.patch(
        f"{SHOPPING_LIST_UPDATE_ENDPOINT}/{home_id}/{item_id}",
        json={"quantity": 4, "notes": "for pasta"},
        headers=headers,
    )

    assert_validation_error(response, "ONLY_QUANTITY_CAN_BE_UPDATED")


def test_update_rejects_payload_with_quantity_product_name_and_notes(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Apple",
        quantity=2,
        notes="green",
    )

    response = client.patch(
        f"{SHOPPING_LIST_UPDATE_ENDPOINT}/{home_id}/{item_id}",
        json={
            "quantity": 5,
            "product_name": "Green apple",
            "notes": "granny smith",
        },
        headers=headers,
    )

    assert_validation_error(response, "ONLY_QUANTITY_CAN_BE_UPDATED")


def test_user_without_authentication_cannot_update_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )

    response = update_item(
        client,
        home_id,
        item_id,
        {},
        quantity=3,
    )

    assert_auth_required(response)


def test_user_with_invalid_token_cannot_update_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )

    response = update_item(
        client,
        home_id,
        item_id,
        {"Authorization": "Bearer invalid-token"},
        quantity=3,
    )

    assert_auth_required(response)


def test_user_not_in_home_cannot_update_item(client, shared_home_setup, outsider_user):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        owner_headers,
        product_name="Milk",
        quantity=1,
    )

    response = update_item(
        client,
        home_id,
        item_id,
        outsider_user["headers"],
        quantity=3,
    )

    assert_not_in_home(response)


def test_user_from_other_home_cannot_update_foreign_item(
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

    response = update_item(
        client,
        home_id,
        item_id,
        private_home_setup["headers"],
        quantity=3,
    )

    assert_not_in_home(response)


def test_cannot_update_non_existing_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]
    fake_item_id = str(uuid.uuid4())

    response = update_item(
        client,
        home_id,
        fake_item_id,
        headers,
        quantity=3,
    )

    assert_item_not_found(response)


def test_cannot_update_item_when_home_is_inactive(client, private_home_setup):
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

    response = update_item(
        client,
        home_id,
        item_id,
        headers,
        quantity=3,
    )

    assert_home_not_found(response)


def test_update_without_notes_field_keeps_existing_notes(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )

    response = update_item(
        client,
        home_id,
        item_id,
        headers,
        quantity=3,
    )

    body = assert_success_response(response, 200, "LIST_ITEM_UPDATED")
    assert body["data"]["quantity"] == 3
    assert body["data"]["notes"] == "whole grain"


def test_update_item_reflects_quantity_change_in_database(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    item_id = create_item_and_get_id(
        client,
        home_id,
        headers,
        product_name="Apple",
        quantity=2,
        notes="green",
    )

    response = update_item(
        client,
        home_id,
        item_id,
        headers,
        quantity=5,
    )

    body = assert_success_response(response, 200, "LIST_ITEM_UPDATED")
    assert body["data"]["id"] == item_id
    assert body["data"]["product_name"] == "Apple"
    assert body["data"]["quantity"] == 5
    assert body["data"]["notes"] == "green"

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["id"] == item_id
    assert items[0]["product_name"] == "Apple"
    assert items[0]["quantity"] == 5
    assert items[0]["notes"] == "green"