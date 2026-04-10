import types

import pytest


VALID_CREATE_CODES = {"HOME_CREATED"}


def assert_home_created(response):
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] in VALID_CREATE_CODES
    assert body["home"] is not None
    return body


@pytest.mark.parametrize("name", ["My Home", "Home 01", "A1"])
def test_create_home_with_valid_data_succeeds(client, owner_user, name):
    response = client.post("/home/", json={"name": name}, headers=owner_user["headers"])

    body = assert_home_created(response)
    assert body["message"]
    assert body["home"]["name"] == name.strip()
    assert body["home"]["owner_id"] == owner_user["user"]["id"]
    assert body["home"]["invite_code"]
    assert body["home"]["member_count"] == 1
    assert len(body["home"]["members"]) == 1
    assert body["home"]["members"][0]["role"] == "owner"
    assert body["home"]["members"][0]["username"] == owner_user["user"]["username"]


@pytest.mark.parametrize(
    "name, expected_code",
    [
        ("", "HOME_NAME_INVALID_LENGTH"),
        (" ", "HOME_NAME_INVALID_LENGTH"),
        ("A", "HOME_NAME_INVALID_LENGTH"),
        ("A" * 21, "HOME_NAME_INVALID_LENGTH"),
    ],
    ids=["empty", "spaces_only", "too_short", "too_long"],
)
def test_create_home_rejects_invalid_name_length(client, owner_user, name, expected_code):
    response = client.post("/home/", json={"name": name}, headers=owner_user["headers"])

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == expected_code


@pytest.mark.parametrize(
    "name, expected_code",
    [
        ("Kitchen\nHome", "HOME_NAME_INVALID_CHARACTERS"),
        ("Kitchen\tHome", "HOME_NAME_INVALID_CHARACTERS"),
        ("Kitchen@Home", "HOME_NAME_INVALID_CHARACTERS"),
        ("Kitchen/Home", "HOME_NAME_INVALID_CHARACTERS"),
        ("My  Home", "HOME_NAME_INVALID_SPACES"),
    ],
)
def test_create_home_rejects_invalid_name_characters_and_spaces(client, owner_user, name, expected_code):
    response = client.post("/home/", json={"name": name}, headers=owner_user["headers"])

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == expected_code


def test_create_home_trims_name(client, owner_user):
    response = client.post("/home/", json={"name": "  My Home  "}, headers=owner_user["headers"])

    body = assert_home_created(response)
    assert body["home"]["name"] == "My Home"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_create_home_requires_authentication(client, headers):
    response = client.post("/home/", json={"name": "My Home"}, headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_create_home_fails_if_user_already_has_home(client, owner_home):
    response = client.post(
        "/home/",
        json={"name": "Another Home"},
        headers=owner_home["owner"]["headers"],
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "USER_ALREADY_HAS_HOME"


@pytest.mark.parametrize("name", ["MyHome", "CasaNova"])
def test_create_home_generates_unique_unused_code(client, owner_home, make_user, name):
    another_user = make_user(username="freshhome", email="freshhome@example.com")
    response = client.post("/home/", json={"name": name}, headers=another_user["headers"])

    body = assert_home_created(response)
    assert body["home"]["invite_code"] != owner_home["invite_code"]


def test_user_can_create_new_home_after_leaving_previous_one(client, private_home_setup):
    leave_response = client.delete("/home/leave", headers=private_home_setup["headers"])
    create_response = client.post(
        "/home/",
        json={"name": "Brand New Home"},
        headers=private_home_setup["headers"],
    )

    assert leave_response.status_code == 200, leave_response.text
    assert create_response.status_code == 201, create_response.text
    body = create_response.json()
    assert body["code"] == "HOME_CREATED"


@pytest.mark.parametrize(
    "payload, expected_code",
    [
        ({}, "REQUIRED_FIELDS_MISSING"),
        ({"name": None}, "REQUIRED_FIELDS_MISSING"),
    ],
)
def test_create_home_requires_name_field(client, owner_user, payload, expected_code):
    response = client.post("/home/", json=payload, headers=owner_user["headers"])

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == expected_code


def test_create_home_handles_repository_failure(unsafe_client):
    home_routes = unsafe_client.app_modules["home_routes"]
    auth = unsafe_client.app_modules["auth"]

    fake_user = types.SimpleNamespace(id="fake-user-id")

    def override_current_user():
        return fake_user, None

    class BrokenQueryResult:
        def filter(self, *args, **kwargs):
            raise RuntimeError("home lookup failed")

    class BrokenDB:
        def query(self, *args, **kwargs):
            return BrokenQueryResult()

        def add(self, obj):
            return None

        def flush(self):
            return None

        def commit(self):
            return None

        def refresh(self, obj):
            return None

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[auth.get_current_user] = override_current_user
    unsafe_client.app.dependency_overrides[home_routes.get_db] = override_get_db

    response = unsafe_client.post("/home/", json={"name": "My Home"}, headers={"Authorization": "Bearer anything"})

    assert response.status_code == 500
