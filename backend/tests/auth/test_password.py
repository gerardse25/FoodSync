from datetime import datetime, timedelta


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


def test_change_password_rejects_same_password(client, auth_headers):
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": "Passw0rd", "new_password": "Passw0rd"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "La nova contrasenya no pot ser igual que l'actual"
    )


def test_forgot_password_creates_reset_token_and_returns_generic_message(
    client, registered_user
):
    response = client.post("/auth/forgot-password", json={"email": "user@example.com"})

    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "Si el correu existeix, rebràs instruccions per restablir la contrasenya"
    )
    assert len(client.sent_emails) == 1
    assert client.sent_emails[0]["to_email"] == "user@example.com"


def test_reset_password_invalidates_existing_sessions(client, registered_user):
    forgot_response = client.post(
        "/auth/forgot-password", json={"email": "user@example.com"}
    )
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
        token_row = (
            session.query(client.models.PasswordResetToken)
            .filter_by(token=token)
            .first()
        )
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
