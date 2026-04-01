import pytest


def test_delete_account_invalidates_all_sessions(client, registered_user, second_session):
    delete_response = client.delete(
        "/auth/delete",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    verify_first = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    verify_second = client.get("/auth/verify", headers=second_session["headers"])
    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "El teu compte s'ha desactivat correctament"
    assert verify_first.status_code == 401
    assert verify_second.status_code == 401
    assert login_response.status_code == 401


def test_deleted_email_can_be_registered_again(client, registered_user, auth_headers):
    delete_response = client.delete("/auth/delete", headers=auth_headers)
    register_again = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "user@example.com",
            "password": "Passw0rd",
        },
    )

    assert delete_response.status_code == 200
    assert register_again.status_code == 201


def test_delete_account_requires_authenticated_session(client):
    response = client.delete("/auth/delete")

    assert response.status_code in (401, 403)


def test_delete_account_when_authenticated_user_no_longer_exists_returns_auth_error(
    client, registered_user
):
    session = client.db_session_factory()
    try:
        user = (
            session.query(client.models.User)
            .filter_by(email_normalized="user@example.com")
            .first()
        )
        session.delete(user)
        session.commit()
    finally:
        session.close()

    response = client.delete(
        "/auth/delete",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] in ("No autoritzat", "Sessió caducada")


def test_delete_account_handles_session_lookup_failure(unsafe_client, registered_user):
    routes = unsafe_client.app_modules["routes"]

    class BrokenQueryResult:
        def filter(self, *args, **kwargs):
            raise RuntimeError("session lookup failed")

    class BrokenDB:
        def query(self, *args, **kwargs):
            return BrokenQueryResult()

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.delete(
        "/auth/delete",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )

    assert response.status_code == 500


def test_delete_account_handles_repository_failure_after_user_lookup(
    unsafe_client, registered_user
):
    routes = unsafe_client.app_modules["routes"]

    class QueryResult:
        def __init__(self, user_obj):
            self.user_obj = user_obj

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.user_obj

    class FakeUser:
        id = "fake-user-id"
        is_active = True
        email = "user@example.com"
        email_normalized = "user@example.com"

    class BrokenDB:
        def __init__(self):
            self.user = FakeUser()
            self.query_calls = 0

        def query(self, *args, **kwargs):
            self.query_calls += 1
            return QueryResult(self.user)

        def commit(self):
            raise RuntimeError("delete commit failed")

        def refresh(self, obj):
            return None

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.delete(
        "/auth/delete",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )

    assert response.status_code == 500