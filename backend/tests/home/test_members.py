import types

import pytest


def _member_map(home_payload):
    return {member["username"]: member["role"] for member in home_payload["members"]}


def test_owner_can_list_home_members(client, shared_home_setup):
    response = client.get("/home/", headers=shared_home_setup["owner_headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_RETRIEVED"
    assert len(body["members"]) == 3
    roles = _member_map(body)
    assert roles[shared_home_setup["owner"]["user"]["username"]] == "owner"
    assert roles[shared_home_setup["member1"]["user"]["username"]] == "member"
    assert roles[shared_home_setup["member2"]["user"]["username"]] == "member"


def test_member_can_list_home_members(client, shared_home_setup):
    response = client.get("/home/", headers=shared_home_setup["member1_headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_RETRIEVED"
    assert len(body["members"]) == 3


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_list_members_requires_authentication(client, headers):
    response = client.get("/home/", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_non_member_cannot_list_members(client, outsider_user):
    response = client.get("/home/", headers=outsider_user["headers"])

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


def test_list_members_does_not_include_duplicates(client, shared_home_setup):
    response = client.get("/home/", headers=shared_home_setup["owner_headers"])

    body = response.json()
    usernames = [member["username"] for member in body["members"]]
    assert len(usernames) == len(set(usernames))


def test_removed_member_no_longer_appears_in_members_list(client, shared_home_setup):
    member2_id = shared_home_setup["member2"]["user"]["id"]
    remove_response = client.request(
        "DELETE",
        "/home/kick",
        json={"user_id": member2_id},
        headers=shared_home_setup["owner_headers"],
    )
    assert remove_response.status_code == 200, remove_response.text

    response = client.get("/home/", headers=shared_home_setup["owner_headers"])
    body = response.json()
    usernames = {member["username"] for member in body["members"]}
    assert shared_home_setup["member2"]["user"]["username"] not in usernames
    assert len(usernames) == 2


def test_joined_member_appears_in_members_list(client, owner_home, outsider_user):
    join_response = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=outsider_user["headers"],
    )
    assert join_response.status_code == 200, join_response.text

    response = client.get("/home/", headers=owner_home["owner"]["headers"])
    body = response.json()
    usernames = {member["username"] for member in body["members"]}
    assert outsider_user["user"]["username"] in usernames


def test_list_members_handles_repository_failure(unsafe_client):
    home_routes = unsafe_client.app_modules["home_routes"]
    auth = unsafe_client.app_modules["auth"]

    fake_user = types.SimpleNamespace(id="fake-user-id")

    def override_current_user():
        return fake_user, None

    class BrokenQueryResult:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            raise RuntimeError("list members lookup failed")

    class BrokenDB:
        def query(self, *args, **kwargs):
            return BrokenQueryResult()

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[auth.get_current_user] = override_current_user
    unsafe_client.app.dependency_overrides[home_routes.get_db] = override_get_db

    response = unsafe_client.get("/home/", headers={"Authorization": "Bearer anything"})

    assert response.status_code == 500
