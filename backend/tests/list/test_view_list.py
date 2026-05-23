import uuid

import pytest


SHOPPING_LIST_GET_ENDPOINT = "/shopping-list"
SHOPPING_LIST_ADD_ENDPOINT = "/shopping-list"


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


def get_list(client, home_id, headers):
    return client.get(f"{SHOPPING_LIST_GET_ENDPOINT}/{home_id}", headers=headers)


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


def test_owner_can_view_empty_shopping_list(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = get_list(client, home_id, headers)

    body = assert_success_response(response, 200, "LIST_RETRIEVED")
    assert body["message"] == "Llista de la compra obtinguda correctament."
    assert body["items"] == []


def test_member_can_view_empty_shopping_list(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["member1_headers"]

    response = get_list(client, home_id, headers)

    body = assert_success_response(response, 200, "LIST_RETRIEVED")
    assert body["items"] == []


def test_owner_can_view_shopping_list_with_existing_items(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    add_response_1 = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
        notes="semi-skimmed",
    )
    assert_success_response(add_response_1, 201, "PRODUCT_ADDED_TO_LIST")

    add_response_2 = add_item(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )
    assert_success_response(add_response_2, 201, "PRODUCT_ADDED_TO_LIST")

    response = get_list(client, home_id, headers)

    body = assert_success_response(response, 200, "LIST_RETRIEVED")
    assert len(body["items"]) == 2

    items_by_name = {item["product_name"]: item for item in body["items"]}

    assert items_by_name["Milk"]["quantity"] == 2
    assert items_by_name["Milk"]["notes"] == "semi-skimmed"

    assert items_by_name["Bread"]["quantity"] == 1
    assert items_by_name["Bread"]["notes"] == "whole grain"


def test_member_can_view_shopping_list_with_existing_items(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    owner_headers = shared_home_setup["owner_headers"]
    member_headers = shared_home_setup["member1_headers"]

    add_response = add_item(
        client,
        home_id,
        owner_headers,
        product_name="Eggs",
        quantity=6,
        notes="free-range",
    )
    assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")

    response = get_list(client, home_id, member_headers)

    body = assert_success_response(response, 200, "LIST_RETRIEVED")
    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Eggs"
    assert body["items"][0]["quantity"] == 6
    assert body["items"][0]["notes"] == "free-range"


def test_view_shopping_list_reflects_accumulated_quantity_after_add_merge(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_add = add_item(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=2,
    )
    assert_success_response(first_add, 201, "PRODUCT_ADDED_TO_LIST")

    second_add = add_item(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=3,
    )
    assert_success_response(second_add, 200, "LIST_ITEM_UPDATED")

    response = get_list(client, home_id, headers)

    body = assert_success_response(response, 200, "LIST_RETRIEVED")
    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Rice"
    assert body["items"][0]["quantity"] == 5


def test_view_shopping_list_returns_notes_when_present(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="Tomato",
        quantity=4,
        notes="for salad",
    )
    assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")

    response = get_list(client, home_id, headers)

    body = assert_success_response(response, 200, "LIST_RETRIEVED")
    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Tomato"
    assert body["items"][0]["notes"] == "for salad"


def test_view_shopping_list_returns_null_notes_when_not_present(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="Banana",
        quantity=3,
    )
    assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")

    response = get_list(client, home_id, headers)

    body = assert_success_response(response, 200, "LIST_RETRIEVED")
    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Banana"
    assert body["items"][0]["notes"] is None


def test_user_without_authentication_cannot_view_shopping_list(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]

    response = get_list(client, home_id, {})

    assert_auth_required(response)


def test_user_with_invalid_token_cannot_view_shopping_list(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]

    response = get_list(
        client,
        home_id,
        {"Authorization": "Bearer invalid-token"},
    )

    assert_auth_required(response)


def test_user_not_in_home_cannot_view_shopping_list(client, shared_home_setup, outsider_user):
    home_id = shared_home_setup["home_id"]

    response = get_list(client, home_id, outsider_user["headers"])

    assert_not_in_home(response)


def test_user_from_other_home_cannot_view_foreign_shopping_list(
    client,
    shared_home_setup,
    private_home_setup,
):
    foreign_home_id = shared_home_setup["home_id"]
    headers = private_home_setup["headers"]

    response = get_list(client, foreign_home_id, headers)

    assert_not_in_home(response)


def test_cannot_view_shopping_list_of_non_existing_home(client, registered_user):
    fake_home_id = str(uuid.uuid4())

    response = get_list(client, fake_home_id, registered_user["headers"])

    assert_home_not_found(response)


def test_cannot_view_shopping_list_of_inactive_home(client, private_home_setup):
    home_id = private_home_setup["home_id"]
    headers = private_home_setup["headers"]

    deactivate_home(client, home_id)

    response = get_list(client, home_id, headers)

    assert_home_not_found(response)


def test_view_shopping_list_only_returns_items_from_requested_home(
    client,
    shared_home_setup,
    private_home_setup,
):
    shared_home_id = shared_home_setup["home_id"]
    shared_headers = shared_home_setup["owner_headers"]

    private_home_id = private_home_setup["home_id"]
    private_headers = private_home_setup["headers"]

    shared_add = add_item(
        client,
        shared_home_id,
        shared_headers,
        product_name="Shared item",
        quantity=2,
    )
    assert_success_response(shared_add, 201, "PRODUCT_ADDED_TO_LIST")

    private_add = add_item(
        client,
        private_home_id,
        private_headers,
        product_name="Private item",
        quantity=1,
    )
    assert_success_response(private_add, 201, "PRODUCT_ADDED_TO_LIST")

    shared_response = get_list(client, shared_home_id, shared_headers)
    shared_body = assert_success_response(shared_response, 200, "LIST_RETRIEVED")

    assert len(shared_body["items"]) == 1
    assert shared_body["items"][0]["product_name"] == "Shared item"

    private_response = get_list(client, private_home_id, private_headers)
    private_body = assert_success_response(private_response, 200, "LIST_RETRIEVED")

    assert len(private_body["items"]) == 1
    assert private_body["items"][0]["product_name"] == "Private item"


def test_view_shopping_list_reflects_newly_added_item_without_needing_other_actions(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_view = get_list(client, home_id, headers)
    first_body = assert_success_response(first_view, 200, "LIST_RETRIEVED")
    assert first_body["items"] == []

    add_response = add_item(
        client,
        home_id,
        headers,
        product_name="Yogurt",
        quantity=2,
    )
    assert_success_response(add_response, 201, "PRODUCT_ADDED_TO_LIST")

    second_view = get_list(client, home_id, headers)
    second_body = assert_success_response(second_view, 200, "LIST_RETRIEVED")

    assert len(second_body["items"]) == 1
    assert second_body["items"][0]["product_name"] == "Yogurt"
    assert second_body["items"][0]["quantity"] == 2