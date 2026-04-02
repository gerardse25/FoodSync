def test_verify_requires_valid_token(client):
    response = client.get("/auth/verify")
    assert response.status_code in (401, 403)


def test_valid_session_allows_retrieving_authenticated_user(client, auth_headers):
    response = client.get("/auth/verify", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert "user" in body
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["username"] == "validuser"


def test_session_remains_valid_across_multiple_checks(client, auth_headers):
    first_response = client.get("/auth/verify", headers=auth_headers)
    second_response = client.get("/auth/verify", headers=auth_headers)
    third_response = client.get("/auth/verify", headers=auth_headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 200


def test_logout_without_active_session_returns_auth_error(client):
    response = client.post("/auth/logout")

    assert response.status_code in (401, 403)


def test_get_current_user_with_invalid_session_returns_auth_error(client):
    invalid_token = "this.is.not.a.valid.jwt"

    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 401


def test_two_simultaneous_sessions_for_same_user_can_coexist(
    client, registered_user, second_session
):
    first_verify = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    second_verify = client.get(
        "/auth/verify",
        headers=second_session["headers"],
    )

    assert first_verify.status_code == 200
    assert second_verify.status_code == 200


def test_closing_one_session_does_not_invalidate_other_active_sessions(
    client, registered_user, second_session
):
    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    first_verify = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    second_verify = client.get(
        "/auth/verify",
        headers=second_session["headers"],
    )

    assert logout_response.status_code == 200
    assert first_verify.status_code == 401
    assert second_verify.status_code == 200


def test_logout_invalidates_current_session_only(
    client, registered_user, second_session
):
    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    first_verify = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    second_verify = client.get("/auth/verify", headers=second_session["headers"])

    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Sessió tancada correctament"
    assert first_verify.status_code == 401
    assert second_verify.status_code == 200


def test_refresh_returns_new_access_token_for_active_session(client, registered_user):
    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]
    verify_response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )

    assert verify_response.status_code == 200


def test_get_current_user_handles_session_storage_failure(
    unsafe_client, registered_user
):
    routes = unsafe_client.app_modules["routes"]

    class BrokenSessionLookup:
        def filter(self, *args, **kwargs):
            raise RuntimeError("session lookup failed")

    class BrokenDB:
        def query(self, *args, **kwargs):
            return BrokenSessionLookup()

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )

    assert response.status_code == 500


def test_logout_handles_session_storage_failure(unsafe_client, registered_user):
    routes = unsafe_client.app_modules["routes"]

    class BrokenSessionLookup:
        def filter(self, *args, **kwargs):
            raise RuntimeError("session storage failure")

    class BrokenDB:
        def query(self, *args, **kwargs):
            return BrokenSessionLookup()

    def override_get_db():
        yield BrokenDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )

    assert response.status_code == 500
