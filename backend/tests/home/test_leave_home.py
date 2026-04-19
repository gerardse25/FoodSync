import types

import pytest


def test_member_leaves_home(client, shared_home_member_setup, shared_home_setup):
    response = client.delete("/home/leave", headers=shared_home_member_setup["headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT"

    home_response = client.get("/home/", headers=shared_home_setup["owner_headers"])
    home_body = home_response.json()
    usernames = {member["username"] for member in home_body["members"]}
    assert shared_home_member_setup["user"]["user"]["username"] not in usernames


def test_owner_leaving_shared_home_transfers_ownership_to_oldest_member(
    client, shared_home_owner_setup
):
    response = client.delete("/home/leave", headers=shared_home_owner_setup["headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT_OWNER_TRANSFERRED"

    owner_get = client.get("/home/", headers=shared_home_owner_setup["headers"])
    oldest_get = client.get(
        "/home/", headers=shared_home_owner_setup["oldest_member_ctx"]["headers"]
    )
    newest_get = client.get(
        "/home/", headers=shared_home_owner_setup["newer_member_ctx"]["headers"]
    )

    assert owner_get.status_code == 404, owner_get.text
    assert oldest_get.status_code == 200, oldest_get.text
    assert newest_get.status_code == 200, newest_get.text

    oldest_body = oldest_get.json()
    roles = {member["username"]: member["role"] for member in oldest_body["members"]}
    assert roles[shared_home_owner_setup["oldest_member"]["username"]] == "owner"
    assert roles[shared_home_owner_setup["newer_member"]["username"]] == "member"


def test_leaving_private_home_deletes_it(client, private_home_setup):
    leave_response = client.delete("/home/leave", headers=private_home_setup["headers"])
    sync_response = client.get("/home/sync", headers=private_home_setup["headers"])

    assert leave_response.status_code == 200, leave_response.text
    body = leave_response.json()
    assert body["code"] == "HOME_LEFT_AND_DISSOLVED"
    assert sync_response.status_code == 404, sync_response.text


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_leave_home_requires_authentication(client, headers):
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_non_member_cannot_leave_home(client, outsider_user):
    response = client.delete("/home/leave", headers=outsider_user["headers"])

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


@pytest.mark.parametrize("who", ["owner", "member"])
def test_leave_non_existing_home_returns_error(client, shared_home_setup, who):
    headers = (
        shared_home_setup["owner_headers"]
        if who == "owner"
        else shared_home_setup["member1_headers"]
    )

    first_leave = client.delete("/home/leave", headers=headers)
    second_leave = client.delete("/home/leave", headers=headers)

    assert first_leave.status_code == 200, first_leave.text
    assert second_leave.status_code == 404, second_leave.text
    body = second_leave.json()
    assert body["code"] == "NOT_IN_HOME"


def test_sync_reflects_member_count_after_member_leaves(client, shared_home_setup):
    leave_response = client.delete(
        "/home/leave", headers=shared_home_setup["member1_headers"]
    )
    sync_response = client.get("/home/sync", headers=shared_home_setup["owner_headers"])

    assert leave_response.status_code == 200, leave_response.text
    assert sync_response.status_code == 200, sync_response.text
    sync_body = sync_response.json()
    assert sync_body["code"] == "HOME_SYNC_OK"
    assert sync_body["member_count"] == 2


@pytest.mark.parametrize("role", ["owner", "member"])
def test_leave_home_handles_repository_failure(unsafe_client, role):
    home_routes = unsafe_client.app_modules["home_routes"]
    auth = unsafe_client.app_modules["auth"]

    fake_user = types.SimpleNamespace(id="fake-user-id")
    fake_membership = types.SimpleNamespace(
        role=role, home_id="fake-home-id", is_active=True
    )
    fake_home = types.SimpleNamespace(id="fake-home-id", is_active=True)

    def override_current_user():
        return fake_user, None

    class QueryResult:
        def __init__(self, model_name):
            self.model_name = model_name

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            if self.model_name == "memberships_for_dissolve":
                raise RuntimeError("dissolve lookup failed")
            return []

        def first(self):
            if self.model_name == "membership":
                return fake_membership
            if self.model_name == "home":
                return fake_home
            raise RuntimeError("leave lookup failed")

    class BrokenDB:
        query_calls = 0

        def query(self, model, *args, **kwargs):
            self.query_calls += 1
            if self.query_calls == 1:
                return QueryResult("membership")
            if self.query_calls == 2:
                return QueryResult("home")
            return QueryResult("memberships_for_dissolve")

        def commit(self):
            raise RuntimeError("leave commit failed")

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[auth.get_current_user] = (
        override_current_user
    )
    unsafe_client.app.dependency_overrides[home_routes.get_db] = override_get_db

    response = unsafe_client.delete(
        "/home/leave", headers={"Authorization": "Bearer anything"}
    )

    assert response.status_code == 500


###SRINT 3



@pytest.mark.parametrize("who", ["owner", "member"])
def test_user_leaving_home_makes_private_products_public(
    client,
    shared_home_with_products,
    who,
    list_home_products_db,
):
    if who == "owner":
        leave_headers = shared_home_with_products["owner_headers"]
        target_product_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
        other_private_product_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]
    else:
        leave_headers = shared_home_with_products["member1_headers"]
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

    old_other_product = next(
        (product for product in old_products if product["name"] == other_private_product_name),
        None,
    )
    assert old_other_product is not None
    assert old_other_product["is_private"] is True

    old_public_product_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]
    old_public_product = next(
        (product for product in old_products if product["name"] == old_public_product_name),
        None,
    )
    assert old_public_product is not None
    assert old_public_product["is_private"] is False

    leave_response = client.delete("/home/leave", headers=leave_headers)
    assert leave_response.status_code == 200, leave_response.text

    if who == "owner":
        assert leave_response.json()["code"] == "HOME_LEFT_OWNER_TRANSFERRED"
    else:
        assert leave_response.json()["code"] == "HOME_LEFT"

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

    new_public_product = next(
        (product for product in new_products if product["name"] == old_public_product_name),
        None,
    )
    assert new_public_product is not None
    assert new_public_product["is_private"] is False