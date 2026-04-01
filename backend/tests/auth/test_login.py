import pytest


def assert_validation_error(response):
    assert response.status_code in (400, 422), response.text


def test_login_with_valid_credentials_returns_tokens(client, registered_user):
    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Inici de sessió exitós"
    assert body["user"]["email"] == "user@example.com"
    assert isinstance(body["access_token"], str)
    assert isinstance(body["refresh_token"], str)


def test_login_with_invalid_password_returns_generic_error(client, registered_user):
    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "WrongPass123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credencials incorrectes"


def test_login_with_non_existing_email_returns_error(client):
    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "Passw0rd"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credencials incorrectes"


def test_login_email_is_case_insensitive(client):
    register_response = client.post(
        "/auth/register",
        json={
            "username": "validuser",
            "email": "registered@example.com",
            "password": "Passw0rd",
        },
    )
    assert register_response.status_code == 201, register_response.text

    response = client.post(
        "/auth/login",
        json={"email": "REGISTERED@EXAMPLE.COM", "password": "Passw0rd"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "registered@example.com"


@pytest.mark.parametrize(
    "email, password",
    [
        ("", "Passw0rd"),
        ("registered@example.com", ""),
        ("", ""),
    ],
    ids=["empty_email", "empty_password", "all_empty"],
)
def test_login_with_empty_fields_returns_error(client, email, password):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert_validation_error(response)


@pytest.mark.parametrize(
    "invalid_email",
    [
        "plainaddress",
        "missingatsign.com",
        "@missinglocal.com",
        "user@",
        "user@domain",
        "user@.com",
        "user@com",
    ],
    ids=[
        "missing_at_symbol",
        "missing_at_and_domain",
        "missing_local_part",
        "missing_domain_name",
        "missing_top_level_domain",
        "domain_starts_with_dot",
        "missing_dot_in_domain",
    ],
)
def test_login_with_invalid_email_format_returns_validation_error(client, invalid_email):
    response = client.post(
        "/auth/login",
        json={"email": invalid_email, "password": "Passw0rd"},
    )

    assert_validation_error(response)


@pytest.mark.parametrize(
    "email, password",
    [
        ("user @example.com", "Passw0rd"),
        ("user@ example.com", "Passw0rd"),
        ("user@example.com", "Pass word"),
    ],
    ids=[
        "email_space_before_at",
        "email_space_after_at",
        "password_internal_space",
    ],
)
def test_login_rejects_internal_spaces(client, email, password):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert_validation_error(response)


@pytest.mark.parametrize(
    "email, password",
    [
        ("user\n@example.com", "Passw0rd"),
        ("user\t@example.com", "Passw0rd"),
        ("user@example.com", "Pass\nw0rd"),
        ("user@example.com", "Pass\tw0rd"),
    ],
    ids=[
        "email_newline",
        "email_tab",
        "password_newline",
        "password_tab",
    ],
)
def test_login_rejects_control_characters(client, email, password):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert_validation_error(response)


@pytest.mark.parametrize(
    "email, password",
    [
        (" registered@example.com", "Passw0rd"),
        ("registered@example.com ", "Passw0rd"),
        (" registered@example.com ", "Passw0rd"),
        ("registered@example.com", " Passw0rd"),
        ("registered@example.com", "Passw0rd "),
    ],
    ids=[
        "email_leading_space",
        "email_trailing_space",
        "email_both_sides",
        "password_leading_space",
        "password_trailing_space",
    ],
)
def test_login_trims_leading_and_trailing_spaces(client, email, password):
    register_response = client.post(
        "/auth/register",
        json={
            "username": "validuser",
            "email": "registered@example.com",
            "password": "Passw0rd",
        },
    )
    assert register_response.status_code == 201, register_response.text

    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["email"] == "registered@example.com"


def test_login_does_not_reveal_if_email_exists(client, registered_user):
    missing_email_response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "Passw0rd"},
    )
    wrong_password_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "WrongPass123"},
    )

    assert missing_email_response.status_code == 401
    assert wrong_password_response.status_code == 401
    assert missing_email_response.json()["detail"] == "Credencials incorrectes"
    assert wrong_password_response.json()["detail"] == "Credencials incorrectes"


def test_login_handles_repository_user_lookup_failure(unsafe_client):
    routes = unsafe_client.app_modules["routes"]

    class BrokenLookupResult:
        def filter(self, *args, **kwargs):
            raise RuntimeError("lookup failed")

    class BrokenLookupDB:
        def query(self, *args, **kwargs):
            return BrokenLookupResult()

    def override_get_db():
        yield BrokenLookupDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )

    assert response.status_code == 500


def test_login_handles_session_creation_failure(unsafe_client):
    routes = unsafe_client.app_modules["routes"]
    auth = unsafe_client.app_modules["auth"]

    class LookupResult:
        def __init__(self, user):
            self.user = user

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.user

    class BrokenSaveDB:
        def __init__(self, user):
            self.user = user

        def query(self, *args, **kwargs):
            return LookupResult(self.user)

        def add(self, obj):
            return None

        def commit(self):
            raise RuntimeError("session creation failed")

        def refresh(self, obj):
            return None

    class FakeUser:
        def __init__(self):
            self.id = "11111111-1111-1111-1111-111111111111"
            self.username = "validuser"
            self.email = "user@example.com"
            self.password_hash = auth.hash_password("Passw0rd")
            self.is_active = True

    def override_get_db():
        yield BrokenSaveDB(FakeUser())

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )

    assert response.status_code == 500


def test_login_rejects_deleted_user(client, registered_user, auth_headers):
    delete_response = client.delete("/auth/delete", headers=auth_headers)
    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )

    assert delete_response.status_code == 200
    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Credencials incorrectes"
