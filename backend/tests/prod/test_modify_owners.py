import pytest

INVENTORY_OWNERS_ENDPOINT = "/inventory/owners"


def modify_owner_product_request(client, product_id, owner_ids, headers):
    return client.patch(
        INVENTORY_OWNERS_ENDPOINT,
        json={
            "id_producte": str(product_id),
            "owner_user_ids": owner_ids,
        },
        headers=headers,
    )


def get_product_by_name(products, target_name):
    return next(
        (product for product in products if product["name"] == target_name), None
    )


def assert_owner_state(after_product, expected_owner_ids):
    assert after_product is not None
    assert after_product["owner_user_ids"] == expected_owner_ids
    assert after_product["is_private"] is bool(expected_owner_ids)

    if len(expected_owner_ids) == 1:
        assert after_product["owner_user_id"] == expected_owner_ids[0]
        assert after_product["owner"] == expected_owner_ids[0]
    else:
        assert after_product["owner_user_id"] is None
        assert after_product["owner"] is None


@pytest.mark.parametrize(
    "who, target_headers",
    [
        ("owner", "owner_headers"),
        ("member2", "member2_headers"),
    ],
)
def test_user_can_assign_owner_to_public_product(
    client,
    shared_home_with_products,
    who,
    target_headers,
    list_home_products_db,
):
    headers = shared_home_with_products[target_headers]
    owner_user_ids = [shared_home_with_products[who]["user"]["id"]]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["public_product"]["db"][
        "name"
    ]
    home_id = shared_home_with_products["home_id"]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_product_name)
    assert before_product is not None
    assert before_product["owner_user_ids"] == []
    assert before_product["owner_user_id"] is None
    assert before_product["owner"] is None
    assert before_product["is_private"] is False

    response = modify_owner_product_request(
        client, target_product_id, owner_user_ids, headers
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert_owner_state(after_product, owner_user_ids)


def test_user_can_assign_another_user_as_owner_to_public_product(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    owner_user_ids = [shared_home_with_products["member1"]["user"]["id"]]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["public_product"]["db"][
        "name"
    ]
    home_id = shared_home_with_products["home_id"]

    response = modify_owner_product_request(
        client, target_product_id, owner_user_ids, headers
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert_owner_state(after_product, owner_user_ids)


def test_user_can_assign_another_user_as_owner_to_private_product(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    member1_id = shared_home_with_products["member1"]["user"]["id"]

    target_product_id = shared_home_with_products["products"]["owner_private"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["owner_private"]["db"][
        "name"
    ]
    home_id = shared_home_with_products["home_id"]

    response = modify_owner_product_request(
        client, target_product_id, [owner_id, member1_id], headers
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert_owner_state(after_product, [owner_id, member1_id])


def test_owner_can_remove_self_as_owner_and_leave_other_owner(
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

    member1_id = shared_home_with_products["member1"]["user"]["id"]

    response = modify_owner_product_request(
        client,
        target_product_id,
        [member1_id],
        headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert_owner_state(after_product, [member1_id])


def test_product_with_two_owners_can_be_reduced_to_one_owner(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["public_product"]["db"][
        "name"
    ]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    member1_id = shared_home_with_products["member1"]["user"]["id"]

    first_response = modify_owner_product_request(
        client,
        target_product_id,
        [owner_id, member1_id],
        headers,
    )
    assert first_response.status_code == 200, first_response.text
    assert first_response.json()["code"] == "PRODUCT_OWNERS_UPDATED"

    second_response = modify_owner_product_request(
        client,
        target_product_id,
        [owner_id],
        headers,
    )
    assert second_response.status_code == 200, second_response.text

    body = second_response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert_owner_state(after_product, [owner_id])


def test_current_owner_can_replace_self_with_new_owner_in_single_request(
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

    current_owner_id = shared_home_with_products["owner"]["user"]["id"]
    new_owner_id = shared_home_with_products["member2"]["user"]["id"]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_product_name)
    assert before_product is not None
    assert before_product["owner_user_ids"] == [current_owner_id]
    assert before_product["owner_user_id"] == current_owner_id
    assert before_product["owner"] == current_owner_id
    assert before_product["is_private"] is True

    response = modify_owner_product_request(
        client,
        target_product_id,
        [new_owner_id],
        headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert_owner_state(after_product, [new_owner_id])


def test_old_owner_cannot_modify_product_after_being_replaced(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    old_owner_headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_product_id = shared_home_with_products["products"]["owner_private"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["owner_private"]["db"][
        "name"
    ]

    old_owner_id = shared_home_with_products["owner"]["user"]["id"]
    new_owner_id = shared_home_with_products["member2"]["user"]["id"]

    first_response = modify_owner_product_request(
        client,
        target_product_id,
        [new_owner_id],
        old_owner_headers,
    )
    assert first_response.status_code == 200, first_response.text
    assert first_response.json()["code"] == "PRODUCT_OWNERS_UPDATED"

    second_response = modify_owner_product_request(
        client,
        target_product_id,
        [old_owner_id, new_owner_id],
        old_owner_headers,
    )
    assert second_response.status_code == 403, second_response.text

    body = second_response.json()
    assert body["code"] == "PRODUCT_OWNERSHIP_FORBIDDEN"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert_owner_state(after_product, [new_owner_id])


def test_non_owner_cannot_add_another_owner_to_private_product(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["member2_headers"]
    home_id = shared_home_with_products["home_id"]

    target_product_id = shared_home_with_products["products"]["owner_private"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["owner_private"]["db"][
        "name"
    ]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    member2_id = shared_home_with_products["member2"]["user"]["id"]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_product_name)
    assert before_product is not None
    initial_owner_ids = before_product["owner_user_ids"]

    response = modify_owner_product_request(
        client,
        target_product_id,
        [owner_id, member2_id],
        headers,
    )
    assert response.status_code == 403, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERSHIP_FORBIDDEN"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert after_product["owner_user_ids"] == initial_owner_ids


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_update_product_owners(
    client,
    shared_home_with_products,
    headers,
):
    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    response = modify_owner_product_request(
        client,
        target_product_id,
        [owner_id],
        headers,
    )
    assert response.status_code in (401, 403), response.text

    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_non_member_cannot_update_product_owners(
    client,
    shared_home_with_products,
    outsider_user,
):
    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    response = modify_owner_product_request(
        client,
        target_product_id,
        [owner_id],
        outsider_user["headers"],
    )
    assert response.status_code in (403, 404), response.text

    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


def test_cannot_assign_non_member_as_owner(
    client,
    shared_home_with_products,
    outsider_user,
):
    headers = shared_home_with_products["owner_headers"]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]

    response = modify_owner_product_request(
        client,
        target_product_id,
        [outsider_user["user"]["id"]],
        headers,
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "OWNER_NOT_IN_HOME"


def test_cannot_update_owners_of_non_existing_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    response = modify_owner_product_request(
        client,
        999999,
        [owner_id],
        headers,
    )
    assert response.status_code == 404, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"


def test_cannot_update_owners_with_non_numeric_product_id(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    response = modify_owner_product_request(
        client,
        "abc",
        [owner_id],
        headers,
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_ID_INVALID"


def test_owner_can_make_private_product_public_by_removing_all_owners(
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

    response = modify_owner_product_request(
        client,
        target_product_id,
        [],
        headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert after_product is not None
    assert after_product["owner_user_ids"] == []
    assert after_product["owner_user_id"] is None
    assert after_product["owner"] is None
    assert after_product["is_private"] is False


def test_owner_updating_product_owners_with_duplicate_ids_has_defined_behavior(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["public_product"]["db"][
        "name"
    ]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    response = modify_owner_product_request(
        client,
        target_product_id,
        [owner_id, owner_id],
        headers,
    )

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert after_product is not None

    # Si backend rechaza duplicados:
    if response.status_code in (400, 422):
        body = response.json()
        assert body["code"] in (
            "DUPLICATE_OWNER_IDS",
            "OWNER_IDS_INVALID",
            "OWNER_NOT_IN_HOME",
        )
        assert after_product["owner_user_ids"] == []

    # Si backend deduplica automáticamente:
    elif response.status_code == 200:
        body = response.json()
        assert body["code"] == "PRODUCT_OWNERS_UPDATED"
        assert after_product["owner_user_ids"] == [owner_id]
        assert after_product["owner_user_id"] == owner_id
        assert after_product["owner"] == owner_id
        assert after_product["is_private"] is True

    else:
        pytest.fail(
            f"Unexpected status code for duplicate owner ids: {response.status_code} - {response.text}"
        )


def test_setting_empty_owner_list_on_already_public_product_keeps_it_public(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_product_id = shared_home_with_products["products"]["public_product"]["db"][
        "id"
    ]
    target_product_name = shared_home_with_products["products"]["public_product"]["db"][
        "name"
    ]

    before_products = list_home_products_db(home_id)
    before_product = get_product_by_name(before_products, target_product_name)
    assert before_product is not None
    assert before_product["owner_user_ids"] == []
    assert before_product["owner_user_id"] is None
    assert before_product["owner"] is None
    assert before_product["is_private"] is False

    response = modify_owner_product_request(
        client,
        target_product_id,
        [],
        headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_OWNERS_UPDATED"

    after_products = list_home_products_db(home_id)
    after_product = get_product_by_name(after_products, target_product_name)
    assert after_product is not None
    assert after_product["owner_user_ids"] == []
    assert after_product["owner_user_id"] is None
    assert after_product["owner"] is None
    assert after_product["is_private"] is False
