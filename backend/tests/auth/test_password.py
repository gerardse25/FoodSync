from datetime import datetime, timedelta

import pytest


def assert_validation_error(response):
    assert response.status_code in (400, 422), response.text


def test_change_password_updates_credentials(client, auth_headers):
    change_response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": "Passw0rd", "new_password": "NewPass1"},
    )
    old_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )
    new_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "NewPass1"},
    )

    assert change_response.status_code == 200
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_change_password_persists_new_password_and_old_one_stops_working(client, auth_headers):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": "Passw0rd", "new_password": "Recovered1"},
    )
    old_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )
    new_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Recovered1"},
    )

    assert response.status_code == 200
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_change_password_requires_authenticated_session(client):
    response = client.post(
        "/auth/change-password",
        json={"current_password": "Passw0rd", "new_password": "NewPass1"},
    )

    assert response.status_code in (401, 403)


def test_change_password_rejects_same_password(client, auth_headers):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": "Passw0rd", "new_password": "Passw0rd"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "La nova contrasenya no pot ser igual que l'actual"


@pytest.mark.parametrize(
    "current_password, new_password",
    [
        ("", "NewPass1"),
        ("Passw0rd", ""),
        ("", ""),
    ],
    ids=["empty_current_password", "empty_new_password", "both_empty"],
)
def test_change_password_with_empty_fields_returns_error(client, auth_headers, current_password, new_password):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": current_password, "new_password": new_password},
    )

    assert_validation_error(response)


@pytest.mark.parametrize(
    "new_password, expected",
    [
        ("123", False),
        ("abcde", False),
        ("abcdef", True),
        ("abcdefg", True),
        ("ValidP4ss", True),
        ("a" * 31, True),
        ("a" * 32, True),
        ("a" * 33, False),
    ],
    ids=[
        "too_short",
        "below_min",
        "min_boundary",
        "above_min",
        "valid",
        "below_max",
        "max_boundary",
        "above_max",
    ],
)
def test_change_password_length_validation(client, auth_headers, new_password, expected):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": "Passw0rd", "new_password": new_password},
    )

    if expected:
        assert response.status_code == 200, response.text
    else:
        assert_validation_error(response)


@pytest.mark.parametrize(
    "current_password, new_password",
    [
        ("Pass word", "NewPass1"),
        ("Passw0rd", "New Pass1"),
    ],
    ids=[
        "current_password_internal_space",
        "new_password_internal_space",
    ],
)
def test_change_password_rejects_internal_spaces(client, auth_headers, current_password, new_password):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": current_password, "new_password": new_password},
    )

    assert_validation_error(response)


@pytest.mark.parametrize(
    "current_password, new_password",
    [
        ("Pass\nword", "NewPass1"),
        ("Passw0rd", "New\nPass1"),
        ("Pass\tword", "NewPass1"),
        ("Passw0rd", "New\tPass1"),
    ],
    ids=[
        "current_password_newline",
        "new_password_newline",
        "current_password_tab",
        "new_password_tab",
    ],
)
def test_change_password_rejects_control_characters(client, auth_headers, current_password, new_password):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": current_password, "new_password": new_password},
    )

    assert_validation_error(response)


@pytest.mark.parametrize(
    "current_password, new_password",
    [
        (" Passw0rd", "NewPass1"),
        ("Passw0rd ", "NewPass1"),
        ("Passw0rd", " NewPass1"),
        ("Passw0rd", "NewPass1 "),
    ],
    ids=[
        "current_password_leading_space",
        "current_password_trailing_space",
        "new_password_leading_space",
        "new_password_trailing_space",
    ],
)
def test_change_password_trims_leading_and_trailing_spaces(client, auth_headers, current_password, new_password):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": current_password, "new_password": new_password},
    )

    assert response.status_code == 200, response.text

    old_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )
    new_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "NewPass1"},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_change_password_handles_session_lookup_failure(unsafe_client, registered_user):
    routes = unsafe_client.app_modules["routes"]

    class BrokenQueryResult:
        def filter(self, *args, **kwargs):
            raise RuntimeError("session lookup failed")

    class BrokenLookupDB:
        def query(self, *args, **kwargs):
            return BrokenQueryResult()

    def override_get_db():
        yield BrokenLookupDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        json={"current_password": "Passw0rd", "new_password": "NewPass1"},
    )

    assert response.status_code == 500


def test_change_password_handles_password_update_failure(unsafe_client, registered_user):
    routes = unsafe_client.app_modules["routes"]

    class FakeUser:
        password_hash = "fake-hash"

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return FakeUser()

    class BrokenUpdateDB:
        def query(self, *args, **kwargs):
            return FakeQuery()

        def commit(self):
            raise RuntimeError("update failed")

        def refresh(self, obj):
            return None

    def override_get_db():
        yield BrokenUpdateDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    auth = unsafe_client.app_modules["auth"]
    original_get_current_user = auth.get_current_user
    original_verify_password = auth.verify_password
    original_hash_password = auth.hash_password

    def fake_get_current_user():
        return {"sub": str(registered_user["user"]["id"])}

    unsafe_client.app.dependency_overrides[original_get_current_user] = fake_get_current_user

    try:
        auth.verify_password = lambda plain, hashed: True
        auth.hash_password = lambda plain: "new-fake-hash"

        response = unsafe_client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"},
            json={"current_password": "Passw0rd", "new_password": "NewPass1"},
        )
    finally:
        auth.verify_password = original_verify_password
        auth.hash_password = original_hash_password
        unsafe_client.app.dependency_overrides.pop(original_get_current_user, None)

    assert response.status_code == 500


def test_forgot_password_creates_reset_token_and_returns_generic_message(client, registered_user):
    response = client.post("/auth/forgot-password", json={"email": "user@example.com"})

    assert response.status_code == 200
    assert response.json()["message"] == "Si el correu existeix, rebràs instruccions per restablir la contrasenya"
    assert len(client.sent_emails) == 1
    assert client.sent_emails[0]["to_email"] == "user@example.com"


def test_reset_password_invalidates_existing_sessions(client, registered_user):
    forgot_response = client.post("/auth/forgot-password", json={"email": "user@example.com"})
    token = client.sent_emails[0]["token"]

    reset_response = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "Recovered1"},
    )
    verify_old_session = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    login_new_password = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Recovered1"},
    )

    assert forgot_response.status_code == 200
    assert reset_response.status_code == 200
    assert verify_old_session.status_code == 401
    assert login_new_password.status_code == 200


def test_reset_password_rejects_expired_token(client, registered_user):
    client.post("/auth/forgot-password", json={"email": "user@example.com"})
    token = client.sent_emails[0]["token"]

    session = client.db_session_factory()
    try:
        token_row = session.query(client.models.PasswordResetToken).filter_by(token=token).first()
        token_row.expires_at = datetime.utcnow() - timedelta(minutes=1)
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "Recovered1"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Token invàlid o caducat"