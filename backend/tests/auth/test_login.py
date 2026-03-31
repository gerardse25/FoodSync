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


def test_login_rejects_deleted_user(client, registered_user, auth_headers):
    delete_response = client.delete("/auth/delete", headers=auth_headers)
    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Passw0rd"},
    )

    assert delete_response.status_code == 200
    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Credencials incorrectes"
