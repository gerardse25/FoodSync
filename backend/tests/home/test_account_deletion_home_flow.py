import pytest


def test_delete_account_without_home_has_no_home_side_effects(client, registered_user):
    delete_response = client.delete("/auth/delete", headers=registered_user["headers"])

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_NO_HOME"


def test_delete_account_of_private_home_owner_dissolves_home(
    client, private_home_setup
):
    delete_response = client.delete(
        "/auth/delete", headers=private_home_setup["headers"]
    )
    owner_home_response = client.get("/home/", headers=private_home_setup["headers"])

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_AND_HOME_DISSOLVED"
    assert owner_home_response.status_code in (401, 403, 404), owner_home_response.text


def test_delete_account_of_shared_home_member_removes_home_access(
    client, shared_home_setup
):
    delete_response = client.delete(
        "/auth/delete", headers=shared_home_setup["member1_headers"]
    )
    owner_view = client.get("/home/", headers=shared_home_setup["owner_headers"])

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_AND_REMOVED_FROM_HOME"

    assert owner_view.status_code == 200, owner_view.text
    owner_body = owner_view.json()
    usernames = {member["username"] for member in owner_body["members"]}
    assert shared_home_setup["member1"]["user"]["username"] not in usernames


def test_delete_account_of_shared_home_owner_transfers_ownership_to_oldest_member(
    client, shared_home_owner_setup
):
    delete_response = client.delete(
        "/auth/delete", headers=shared_home_owner_setup["headers"]
    )
    old_owner_view = client.get("/home/", headers=shared_home_owner_setup["headers"])
    oldest_view = client.get(
        "/home/", headers=shared_home_owner_setup["oldest_member_ctx"]["headers"]
    )

    assert delete_response.status_code == 200, delete_response.text
    body = delete_response.json()
    assert body["code"] == "ACCOUNT_DELETED_AND_OWNER_TRANSFERRED"
    assert old_owner_view.status_code in (401, 403, 404), old_owner_view.text
    assert oldest_view.status_code == 200, oldest_view.text

    oldest_body = oldest_view.json()
    roles = {member["username"]: member["role"] for member in oldest_body["members"]}
    assert roles[shared_home_owner_setup["oldest_member"]["username"]] == "owner"


###SPRINT 3

@pytest.mark.parametrize("who", ["owner", "member"])
def test_user_deleting_account_makes_private_products_public(
    client,
    shared_home_with_products,
    who,
    list_home_products_db,
):
    if who == "owner":
        delete_headers = shared_home_with_products["owner_headers"]
        target_product_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
        other_private_product_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]
    else:
        delete_headers = shared_home_with_products["member1_headers"]
        target_product_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]
        other_private_product_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    home_id = shared_home_with_products["home_id"]

    old_products = list_home_products_db(home_id)

    old_target_product = next(
        (product for product in old_products if product["name"] == target_product_name),
        None,
    )
    assert old_target_product is not None
    assert old_target_product["is_private"] is True

    delete_response = client.delete("/auth/delete", headers=delete_headers)
    assert delete_response.status_code == 200, delete_response.text

    new_products = list_home_products_db(home_id)

    new_target_product = next(
        (product for product in new_products if product["name"] == target_product_name),
        None,
    )
    assert new_target_product is not None
    assert new_target_product["is_private"] is False
    assert new_target_product["owner_user_id"] is None

    new_other_product = next(
        (product for product in new_products if product["name"] == other_private_product_name),
        None,
    )
    assert new_other_product is not None
    assert new_other_product["is_private"] is True