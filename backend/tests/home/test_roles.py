import types

import pytest


def test_owner_can_view_invitation_code(client, shared_home_setup):
    response = client.get("/home/invite-code", headers=shared_home_setup["owner_headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "INVITE_CODE_RETRIEVED"
    assert body["invite_code"] == shared_home_setup["invite_code"]
    assert body["home_id"] == shared_home_setup["home_id"]


def test_member_cannot_view_invitation_code(client, shared_home_setup):
    response = client.get("/home/invite-code", headers=shared_home_setup["member1_headers"])

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "OWNER_PERMISSION_REQUIRED"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_invitation_code_requires_authentication(client, headers):
    response = client.get("/home/invite-code", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_owner_can_regenerate_invitation_code(client, shared_home_setup):
    old_code = shared_home_setup["invite_code"]
    response = client.post("/home/invite-code/regenerate", headers=shared_home_setup["owner_headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "INVITE_CODE_REGENERATED"
    assert body["invite_code"] != old_code


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_regenerate_invitation_code_requires_authentication(client, headers):
    response = client.post("/home/invite-code/regenerate", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("headers_key", ["member1_headers", "member2_headers"])
def test_member_cannot_regenerate_invitation_code(client, shared_home_setup, headers_key):
    response = client.post("/home/invite-code/regenerate", headers=shared_home_setup[headers_key])

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "OWNER_PERMISSION_REQUIRED"


def test_owner_can_remove_member(client, shared_home_setup):
    member_id = shared_home_setup["member1"]["user"]["id"]
    response = client.request(
        "DELETE",
        "/home/kick",
        json={"user_id": member_id},
        headers=shared_home_setup["owner_headers"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "MEMBER_KICKED"

    kicked_get = client.get("/home/", headers=shared_home_setup["member1_headers"])
    assert kicked_get.status_code == 404, kicked_get.text


def test_member_cannot_remove_other_member(client, shared_home_setup):
    member_id = shared_home_setup["member2"]["user"]["id"]
    response = client.request(
        "DELETE",
        "/home/kick",
        json={"user_id": member_id},
        headers=shared_home_setup["member1_headers"],
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "OWNER_PERMISSION_REQUIRED"


def test_owner_cannot_remove_self(client, shared_home_setup):
    owner_id = shared_home_setup["owner"]["user"]["id"]
    response = client.request(
        "DELETE",
        "/home/kick",
        json={"user_id": owner_id},
        headers=shared_home_setup["owner_headers"],
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["code"] == "CANNOT_KICK_SELF"


def test_remove_non_existing_member_returns_error(client, shared_home_setup):
    response = client.request(
        "DELETE",
        "/home/kick",
        json={"user_id": "00000000-0000-0000-0000-000000000099"},
        headers=shared_home_setup["owner_headers"],
    )

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "TARGET_USER_NOT_IN_HOME"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_remove_member_requires_authentication(client, headers):
    response = client.request(
        "DELETE",
        "/home/kick",
        json={"user_id": "00000000-0000-0000-0000-000000000099"},
        headers=headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_regenerate_invitation_code_handles_repository_failure(unsafe_client):
    home_routes = unsafe_client.app_modules["home_routes"]
    auth = unsafe_client.app_modules["auth"]

    fake_user = types.SimpleNamespace(id="fake-user-id")

    def override_current_user():
        return fake_user, None

    class BrokenQueryResult:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            raise RuntimeError("invite code lookup failed")

    class BrokenDB:
        def query(self, *args, **kwargs):
            return BrokenQueryResult()

        def commit(self):
            return None

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[auth.get_current_user] = override_current_user
    unsafe_client.app.dependency_overrides[home_routes.get_db] = override_get_db

    response = unsafe_client.post("/home/invite-code/regenerate", headers={"Authorization": "Bearer anything"})

    assert response.status_code == 500
