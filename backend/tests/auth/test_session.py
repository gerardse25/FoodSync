def test_verify_requires_valid_token(client):
    response = client.get("/auth/verify")
    assert response.status_code in (401, 403)


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
