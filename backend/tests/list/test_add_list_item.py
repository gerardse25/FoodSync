import uuid

import pytest

SHOPPING_LIST_ADD_ENDPOINT = "/shopping-list"


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


def assert_validation_error(response, expected_code):
    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == expected_code
    return body


def test_owner_can_add_new_item_to_shopping_list(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
    )

    body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")

    assert body["message"] == "Producte afegit a la llista de la compra"
    assert body["data"]["product_name"] == "Milk"
    assert body["data"]["quantity"] == 2
    assert body["data"]["is_new"] is True

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Milk"
    assert items[0]["quantity"] == 2
    assert items[0]["notes"] is None


def test_member_can_add_new_item_to_shopping_list(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["member1_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Eggs",
        quantity=1,
    )

    body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")

    assert body["data"]["product_name"] == "Eggs"
    assert body["data"]["quantity"] == 1
    assert body["data"]["is_new"] is True

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Eggs"
    assert items[0]["quantity"] == 1


def test_adding_existing_item_increments_quantity_instead_of_creating_duplicate(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_response = add_item(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=2,
    )
    assert_success_response(first_response, 201, "PRODUCT_ADDED_TO_LIST")

    second_response = add_item(
        client,
        home_id,
        headers,
        product_name="Rice",
        quantity=3,
    )

    body = assert_success_response(second_response, 200, "LIST_ITEM_UPDATED")

    assert body["data"]["product_name"] == "Rice"
    assert body["data"]["quantity"] == 5
    assert body["data"]["is_new"] is False

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Rice"
    assert items[0]["quantity"] == 5


def test_adding_existing_item_is_case_insensitive(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
    )
    assert_success_response(first_response, 201, "PRODUCT_ADDED_TO_LIST")

    second_response = add_item(
        client,
        home_id,
        headers,
        product_name="milk",
        quantity=1,
    )

    body = assert_success_response(second_response, 200, "LIST_ITEM_UPDATED")

    assert body["data"]["quantity"] == 3
    assert body["data"]["is_new"] is False

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["quantity"] == 3


def test_adding_existing_item_updates_product_name_casing_to_latest_value(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_response = add_item(
        client,
        home_id,
        headers,
        product_name="milk",
        quantity=1,
    )
    assert_success_response(first_response, 201, "PRODUCT_ADDED_TO_LIST")

    second_response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=2,
    )

    body = assert_success_response(second_response, 200, "LIST_ITEM_UPDATED")

    assert body["data"]["product_name"] == "Milk"
    assert body["data"]["quantity"] == 3

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Milk"
    assert items[0]["quantity"] == 3


def test_add_item_stores_notes_on_create(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
        notes="whole grain",
    )

    body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")

    assert body["data"]["product_name"] == "Bread"
    assert body["data"]["quantity"] == 1

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Bread"
    assert items[0]["notes"] == "whole grain"


def test_adding_existing_item_with_notes_updates_notes(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_response = add_item(
        client,
        home_id,
        headers,
        product_name="Tomato",
        quantity=1,
        notes="old notes",
    )
    assert_success_response(first_response, 201, "PRODUCT_ADDED_TO_LIST")

    second_response = add_item(
        client,
        home_id,
        headers,
        product_name="Tomato",
        quantity=2,
        notes="new notes",
    )
    body = assert_success_response(second_response, 200, "LIST_ITEM_UPDATED")

    assert body["data"]["quantity"] == 3

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["quantity"] == 3
    assert items[0]["notes"] == "new notes"


def test_adding_existing_item_without_notes_keeps_previous_notes(
    client, shared_home_setup
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_response = add_item(
        client,
        home_id,
        headers,
        product_name="Apple",
        quantity=1,
        notes="buy green ones",
    )
    assert_success_response(first_response, 201, "PRODUCT_ADDED_TO_LIST")

    second_response = add_item(
        client,
        home_id,
        headers,
        product_name="Apple",
        quantity=2,
    )
    body = assert_success_response(second_response, 200, "LIST_ITEM_UPDATED")

    assert body["data"]["quantity"] == 3

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["quantity"] == 3
    assert items[0]["notes"] == "buy green ones"


def test_user_without_authentication_cannot_add_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]

    response = add_item(
        client,
        home_id,
        {},
        product_name="Milk",
        quantity=1,
    )

    assert_auth_required(response)


def test_user_with_invalid_token_cannot_add_item(client, shared_home_setup):
    home_id = shared_home_setup["home_id"]

    response = add_item(
        client,
        home_id,
        {"Authorization": "Bearer invalid-token"},
        product_name="Milk",
        quantity=1,
    )

    assert_auth_required(response)


def test_user_not_in_home_cannot_add_item(client, shared_home_setup, outsider_user):
    home_id = shared_home_setup["home_id"]

    response = add_item(
        client,
        home_id,
        outsider_user["headers"],
        product_name="Milk",
        quantity=1,
    )

    assert_not_in_home(response)


def test_user_from_other_home_cannot_add_item_to_foreign_home(
    client,
    shared_home_setup,
    private_home_setup,
):
    foreign_home_id = shared_home_setup["home_id"]
    headers = private_home_setup["headers"]

    response = add_item(
        client,
        foreign_home_id,
        headers,
        product_name="Milk",
        quantity=1,
    )

    assert_not_in_home(response)


def test_cannot_add_item_to_non_existing_home(client, registered_user):
    fake_home_id = str(uuid.uuid4())

    response = add_item(
        client,
        fake_home_id,
        registered_user["headers"],
        product_name="Milk",
        quantity=1,
    )

    assert_home_not_found(response)


def test_cannot_add_item_to_inactive_home(client, private_home_setup):
    home_id = private_home_setup["home_id"]
    headers = private_home_setup["headers"]

    deactivate_home(client, home_id)

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
    )

    assert_home_not_found(response)


@pytest.mark.parametrize("invalid_name", [""])
def test_cannot_add_item_with_invalid_product_name(
    client,
    shared_home_setup,
    invalid_name,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name=invalid_name,
        quantity=1,
    )

    assert_validation_error(response, "NAME_REQUIRED")


@pytest.mark.parametrize("invalid_quantity", [0, -1])
def test_cannot_add_item_with_invalid_quantity(
    client,
    shared_home_setup,
    invalid_quantity,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=invalid_quantity,
    )

    assert_validation_error(response, "INVALID_QUANTITY")


@pytest.mark.parametrize(
    "invalid_name",
    [
        "Milk\n",
        "Milk\t",
        "Milk\r",
        "Mil\x7fk",
    ],
)
def test_cannot_add_item_with_control_characters_in_name(
    client,
    shared_home_setup,
    invalid_name,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name=invalid_name,
        quantity=1,
    )

    assert_validation_error(response, "INVALID_NAME")


@pytest.mark.parametrize(
    "invalid_notes",
    [
        "buy\nmilk",
        "buy\tmilk",
        "buy\rmilk",
        "buy\x7fmilk",
    ],
)
def test_cannot_add_item_with_control_characters_in_notes(
    client,
    shared_home_setup,
    invalid_notes,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
        notes=invalid_notes,
    )

    assert_validation_error(response, "INVALID_NOTES")


@pytest.mark.parametrize(
    "product_name,should_pass",
    [
        ("a" * 100, True),
        ("a" * 101, False),
        ("a" * 150, False),
    ],
)
def test_add_item_validates_max_product_name_length(
    client,
    shared_home_setup,
    product_name,
    should_pass,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name=product_name,
        quantity=1,
    )

    if should_pass:
        body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")
        assert body["data"]["product_name"] == product_name
    else:
        assert_validation_error(response, "NAME_TOO_LONG")


@pytest.mark.parametrize(
    "notes,should_pass",
    [
        ("a" * 100, True),
        ("a" * 300, True),
        ("a" * 301, False),
        ("a" * 350, False),
    ],
)
def test_add_item_validates_max_notes_length(
    client,
    shared_home_setup,
    notes,
    should_pass,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
        notes=notes,
    )

    if should_pass:
        body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")
        assert body["data"]["product_name"] == "Milk"
        items = list_shopping_items_db(client, home_id)
        assert len(items) == 1
        assert items[0]["notes"] == notes
    else:
        assert_validation_error(response, "NOTES_TOO_LONG")


@pytest.mark.parametrize(
    "malicious_name",
    [
        "SELECT * FROM users",
        "DROP TABLE shopping_list",
        "'; DELETE FROM shopping_list; --",
        "<script>alert(1)</script>",
    ],
)
def test_cannot_add_item_with_query_like_content_in_name(
    client,
    shared_home_setup,
    malicious_name,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name=malicious_name,
        quantity=1,
    )

    assert_validation_error(response, "INVALID_NAME")


@pytest.mark.parametrize(
    "malicious_notes",
    [
        "SELECT * FROM users",
        "DROP TABLE shopping_list",
        "'; DELETE FROM shopping_list; --",
        "<script>alert(1)</script>",
    ],
)
def test_cannot_add_item_with_query_like_content_in_notes(
    client,
    shared_home_setup,
    malicious_notes,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
        notes=malicious_notes,
    )

    assert_validation_error(response, "INVALID_NOTES")


def test_add_item_normalizes_leading_and_trailing_spaces_in_name(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="   Milk   ",
        quantity=1,
    )

    body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")

    assert body["data"]["product_name"] == "Milk"

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Milk"


def test_add_item_normalizes_leading_and_trailing_spaces_in_notes(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Bread",
        quantity=1,
        notes="   whole grain please   ",
    )

    assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["notes"] == "whole grain please"


def test_add_item_normalizes_spaces_before_matching_existing_item_name(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
    )
    assert_success_response(first_response, 201, "PRODUCT_ADDED_TO_LIST")

    second_response = add_item(
        client,
        home_id,
        headers,
        product_name="   Milk   ",
        quantity=2,
    )
    body = assert_success_response(second_response, 200, "LIST_ITEM_UPDATED")

    assert body["data"]["product_name"] == "Milk"
    assert body["data"]["quantity"] == 3

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["product_name"] == "Milk"
    assert items[0]["quantity"] == 3


def test_cannot_add_item_without_product_name_field(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        f"{SHOPPING_LIST_ADD_ENDPOINT}/{home_id}",
        json={
            "quantity": 1,
            "notes": "optional notes",
        },
        headers=headers,
    )

    assert_validation_error(response, "NAME_REQUIRED")


def test_cannot_add_item_without_quantity_field(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        f"{SHOPPING_LIST_ADD_ENDPOINT}/{home_id}",
        json={
            "product_name": "Milk",
            "notes": "optional notes",
        },
        headers=headers,
    )

    assert_validation_error(response, "QUANTITY_REQUIRED")


def test_cannot_add_item_without_name_andquantity_field(
    client,
    shared_home_setup,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        f"{SHOPPING_LIST_ADD_ENDPOINT}/{home_id}",
        json={
            "notes": "optional notes",
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == "QUANTITY_REQUIRED"


@pytest.mark.parametrize("notes_value", ["", " "])
def test_add_item_accepts_empty_or_blank_notes_and_stores_them_as_empty_string(
    client,
    shared_home_setup,
    notes_value,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    response = add_item(
        client,
        home_id,
        headers,
        product_name="Milk",
        quantity=1,
        notes=notes_value,
    )

    body = assert_success_response(response, 201, "PRODUCT_ADDED_TO_LIST")

    assert body["data"]["product_name"] == "Milk"
    assert body["data"]["quantity"] == 1
    assert body["data"]["notes"] == ""

    items = list_shopping_items_db(client, home_id)
    assert len(items) == 1
    assert items[0]["notes"] == ""
