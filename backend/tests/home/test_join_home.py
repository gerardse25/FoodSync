import types

import pytest


def test_join_home_with_valid_code_succeeds(client, owner_home, member1_user):
    response = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=member1_user["headers"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == owner_home["home_id"]
    assert body["home"]["member_count"] == 2
    joined_members = {member["username"]: member["role"] for member in body["home"]["members"]}
    assert joined_members[member1_user["user"]["username"]] == "member"


def test_join_home_trims_invite_code(client, owner_home, member2_user):
    response = client.post(
        "/home/join",
        json={"invite_code": f"  {owner_home['invite_code']}  "},
        headers=member2_user["headers"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    usernames = {member["username"] for member in body["home"]["members"]}
    assert member2_user["user"]["username"] in usernames


@pytest.mark.parametrize(
    "invite_code, expected_status, expected_code",
    [
        ("", 422, "INVITE_CODE_REQUIRED"),
        ("   ", 422, "INVITE_CODE_REQUIRED"),
        ("BADCODE", 404, "INVITE_CODE_INVALID_OR_EXPIRED"),
        ("BAD\nCODE", 400, "INVITE_CODE_INVALID_FORMAT"),
    ],
    ids=["empty", "spaces_only", "invalid_code", "control_character"],
)
def test_join_home_rejects_invalid_code(client, member1_user, invite_code, expected_status, expected_code):
    response = client.post(
        "/home/join",
        json={"invite_code": invite_code},
        headers=member1_user["headers"],
    )

    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_join_home_requires_authentication(client, owner_home, headers):
    response = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_join_home_fails_if_user_is_already_in_same_home(client, owner_home):
    response = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=owner_home["owner"]["headers"],
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] in {"USER_ALREADY_HAS_HOME", "USER_ALREADY_IN_HOME", "CANNOT_JOIN_OWN_HOME"}


@pytest.mark.parametrize("user_fixture", ["private_home_setup"])
def test_join_home_fails_if_user_already_belongs_to_another_home(client, owner_home, request, user_fixture):
    user_ctx = request.getfixturevalue(user_fixture)
    response = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=user_ctx["headers"],
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "USER_ALREADY_HAS_HOME"


def test_join_home_rejects_when_capacity_reached(client, home_capacity_setup, make_user):
    extra_user = make_user(username="extra10", email="extra10@example.com")
    response = client.post(
        "/home/join",
        json={"invite_code": home_capacity_setup["invite_code"]},
        headers=extra_user["headers"],
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "HOME_MEMBER_LIMIT_REACHED"


@pytest.mark.parametrize("invite_code", ["missing01", "ZZZZZZZZ"])
def test_join_home_rejects_non_existing_home_code(client, member1_user, invite_code):
    response = client.post(
        "/home/join",
        json={"invite_code": invite_code},
        headers=member1_user["headers"],
    )

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "INVITE_CODE_INVALID_OR_EXPIRED"


def test_user_can_join_new_home_after_leaving_previous_one(client, private_home_setup, owner_home):
    leave_response = client.delete("/home/leave", headers=private_home_setup["headers"])
    join_response = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=private_home_setup["headers"],
    )

    assert leave_response.status_code == 200, leave_response.text
    assert join_response.status_code == 200, join_response.text
    body = join_response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == owner_home["home_id"]


def test_join_home_handles_repository_failure(unsafe_client):
    home_routes = unsafe_client.app_modules["home_routes"]
    auth = unsafe_client.app_modules["auth"]

    fake_user = types.SimpleNamespace(id="fake-user-id")

    def override_current_user():
        return fake_user, None

    class BrokenQueryResult:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            raise RuntimeError("join home lookup failed")

    class BrokenDB:
        def query(self, *args, **kwargs):
            return BrokenQueryResult()

        def add(self, obj):
            return None

        def commit(self):
            return None

        def refresh(self, obj):
            return None

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[auth.get_current_user] = override_current_user
    unsafe_client.app.dependency_overrides[home_routes.get_db] = override_get_db

    response = unsafe_client.post(
        "/home/join",
        json={"invite_code": "JOINHOME"},
        headers={"Authorization": "Bearer anything"},
    )

    assert response.status_code == 500
