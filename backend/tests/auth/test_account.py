def test_delete_account_invalidates_all_sessions(
    client, registered_user, second_session
):
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
    assert (
        delete_response.json()["message"]
        == "El teu compte s'ha desactivat correctament"
    )
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
