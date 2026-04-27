import pytest


def create_second_home(client, user_ctx):
    response = client.post(
        "/home/",
        json={"name": "Second Home"},
        headers=user_ctx["headers"],
    )

    assert response.status_code == 201, response.text
    second_home_body = response.json()
    assert second_home_body["code"] == "HOME_CREATED"

    second_home_id = second_home_body["home"]["id"]
    second_home_invite_code = second_home_body["home"]["invite_code"]
    second_home_owner = user_ctx["payload"]["username"]

    return second_home_id, second_home_invite_code, second_home_owner


def get_user_home_response(client, headers):
    return client.get("/home/", headers=headers)


def get_user_home_body(client, headers):
    response = get_user_home_response(client, headers)
    assert response.status_code == 200, response.text
    return response.json()


def get_home_member_count(client, headers):
    body = get_user_home_body(client, headers)
    return body["member_count"]


def test_join_home_exit_home_join_home_again_succeeds(client, outsider_user, shared_home_setup):
    home_invite_code = shared_home_setup["invite_code"]
    home_id = shared_home_setup["home_id"]
    headers = outsider_user["headers"]
    username = outsider_user["payload"]["username"]
    num_users_start = get_home_member_count(client, shared_home_setup["owner_headers"])

    # JOIN HOME
    response = client.post(
        "/home/join",
        json={"invite_code": home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["member_count"] == num_users_start + 1

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == home_id

    # LEAVE HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT"

    home_response = get_user_home_response(client, outsider_user["headers"])
    assert home_response.status_code == 404, home_response.text
    home_body = home_response.json()
    assert home_body["code"] == "NOT_IN_HOME"

    # JOIN HOME AGAIN
    response = client.post(
        "/home/join",
        json={"invite_code": home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == home_id
    assert body["home"]["member_count"] == num_users_start + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == home_id


def test_join_home_exit_home_and_join_different_home_succeeds(
    client,
    outsider_user,
    shared_home_setup,
    make_user,
):
    first_home_invite_code = shared_home_setup["invite_code"]
    first_home_id = shared_home_setup["home_id"]
    headers = outsider_user["headers"]
    username = outsider_user["payload"]["username"]
    num_users_start = get_home_member_count(client, shared_home_setup["owner_headers"])

    # JOIN FIRST HOME
    response = client.post(
        "/home/join",
        json={"invite_code": first_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == first_home_id
    assert body["home"]["member_count"] == num_users_start + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == first_home_id

    # LEAVE FIRST HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT"

    home_response = get_user_home_response(client, outsider_user["headers"])
    assert home_response.status_code == 404, home_response.text
    home_body = home_response.json()
    assert home_body["code"] == "NOT_IN_HOME"

    # CREATE SECOND HOME
    second_home_owner_ctx = make_user(
        username="secondhomeowner",
        email="secondhomeowner@example.com",
    )
    second_home_id, second_home_invite_code, second_home_owner = create_second_home(
        client,
        second_home_owner_ctx,
    )

    assert second_home_id != first_home_id

    # JOIN SECOND HOME
    response = client.post(
        "/home/join",
        json={"invite_code": second_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == second_home_id
    assert body["home"]["member_count"] == 2

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"
    assert joined_members[second_home_owner] == "owner"

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == second_home_id


def test_create_home_exit_home_join_different_home(
    client,
    outsider_user,
    shared_home_setup,
):
    second_home_invite_code = shared_home_setup["invite_code"]
    second_home_id = shared_home_setup["home_id"]
    headers = outsider_user["headers"]
    username = outsider_user["payload"]["username"]
    num_users_start = get_home_member_count(client, shared_home_setup["owner_headers"])

    # CREATE FIRST HOME
    first_home_id, first_home_invite_code, first_home_owner = create_second_home(client, outsider_user)
    assert first_home_owner == username
    assert first_home_invite_code != second_home_invite_code
    assert first_home_id != second_home_id

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == first_home_id

    # LEAVE HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT_AND_DISSOLVED"

    home_response = get_user_home_response(client, outsider_user["headers"])
    assert home_response.status_code == 404, home_response.text
    home_body = home_response.json()
    assert home_body["code"] == "NOT_IN_HOME"

    # JOIN SECOND HOME
    response = client.post(
        "/home/join",
        json={"invite_code": second_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == second_home_id
    assert body["home"]["member_count"] == num_users_start + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == second_home_id


def test_create_home_exit_home_create_home(
    client,
    outsider_user,
    shared_home_setup,
):
    headers = outsider_user["headers"]
    username = outsider_user["payload"]["username"]

    # CREATE FIRST HOME
    first_home_id, first_home_invite_code, first_home_owner = create_second_home(client, outsider_user)
    assert first_home_owner == username

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == first_home_id

    # LEAVE HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT_AND_DISSOLVED"

    home_response = get_user_home_response(client, outsider_user["headers"])
    assert home_response.status_code == 404, home_response.text
    home_body = home_response.json()
    assert home_body["code"] == "NOT_IN_HOME"

    # CREATE SECOND HOME
    second_home_id, second_home_invite_code, second_home_owner = create_second_home(client, outsider_user)
    assert second_home_owner == username
    assert second_home_invite_code != first_home_invite_code
    assert second_home_id != first_home_id

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == second_home_id


def test_join_home_exit_home_create_home(
    client,
    outsider_user,
    shared_home_setup,
):
    first_home_invite_code = shared_home_setup["invite_code"]
    first_home_id = shared_home_setup["home_id"]
    headers = outsider_user["headers"]
    username = outsider_user["payload"]["username"]
    num_users_start = get_home_member_count(client, shared_home_setup["owner_headers"])

    # JOIN HOME
    response = client.post(
        "/home/join",
        json={"invite_code": first_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == first_home_id
    assert body["home"]["member_count"] == num_users_start + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == first_home_id

    # LEAVE HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT"

    home_response = get_user_home_response(client, outsider_user["headers"])
    assert home_response.status_code == 404, home_response.text
    home_body = home_response.json()
    assert home_body["code"] == "NOT_IN_HOME"

    # CREATE HOME
    second_home_id, second_home_invite_code, second_home_owner = create_second_home(client, outsider_user)
    assert second_home_owner == username
    assert second_home_invite_code != first_home_invite_code
    assert second_home_id != first_home_id

    home_body = get_user_home_body(client, outsider_user["headers"])
    assert home_body["id"] == second_home_id


def test_join_home_leave_join_second_existing_home_leave_and_rejoin_first_home(
    client,
    outsider_user,
    shared_home_setup,
    make_user,
):
    first_home_invite_code = shared_home_setup["invite_code"]
    first_home_id = shared_home_setup["home_id"]
    headers = outsider_user["headers"]
    username = outsider_user["payload"]["username"]
    first_home_member_count = get_home_member_count(client, shared_home_setup["owner_headers"])

    # CREATE SECOND EXISTING HOME
    second_home_owner_ctx = make_user(
        username="userexample",
        email="userexample@example.com",
    )
    second_home_id, second_home_invite_code, second_home_owner = create_second_home(
        client,
        second_home_owner_ctx,
    )

    assert second_home_id != first_home_id

    # JOIN FIRST HOME
    response = client.post(
        "/home/join",
        json={"invite_code": first_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == first_home_id
    assert body["home"]["member_count"] == first_home_member_count + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, headers)
    assert home_body["id"] == first_home_id

    # LEAVE FIRST HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT"

    home_response = get_user_home_response(client, headers)
    assert home_response.status_code == 404, home_response.text
    assert home_response.json()["code"] == "NOT_IN_HOME"

    # JOIN SECOND HOME
    response = client.post(
        "/home/join",
        json={"invite_code": second_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == second_home_id
    assert body["home"]["member_count"] == 2

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"
    assert joined_members[second_home_owner] == "owner"

    home_body = get_user_home_body(client, headers)
    assert home_body["id"] == second_home_id

    # LEAVE SECOND HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT"

    home_response = get_user_home_response(client, headers)
    assert home_response.status_code == 404, home_response.text
    assert home_response.json()["code"] == "NOT_IN_HOME"

    # REJOIN FIRST HOME
    response = client.post(
        "/home/join",
        json={"invite_code": first_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == first_home_id
    assert body["home"]["member_count"] == first_home_member_count + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, headers)
    assert home_body["id"] == first_home_id


def test_join_home_leave_create_new_home_leave_and_rejoin_first_home(
    client,
    outsider_user,
    shared_home_setup,
):
    first_home_invite_code = shared_home_setup["invite_code"]
    first_home_id = shared_home_setup["home_id"]
    headers = outsider_user["headers"]
    username = outsider_user["payload"]["username"]
    first_home_member_count = get_home_member_count(client, shared_home_setup["owner_headers"])

    # JOIN FIRST HOME
    response = client.post(
        "/home/join",
        json={"invite_code": first_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == first_home_id
    assert body["home"]["member_count"] == first_home_member_count + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, headers)
    assert home_body["id"] == first_home_id

    # LEAVE FIRST HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT"

    home_response = get_user_home_response(client, headers)
    assert home_response.status_code == 404, home_response.text
    assert home_response.json()["code"] == "NOT_IN_HOME"

    # CREATE NEW HOME
    second_home_id, second_home_invite_code, second_home_owner = create_second_home(client, outsider_user)

    assert second_home_id != first_home_id
    assert second_home_owner == username

    home_body = get_user_home_body(client, headers)
    assert home_body["id"] == second_home_id

    # LEAVE SECOND HOME
    response = client.delete("/home/leave", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_LEFT_AND_DISSOLVED"

    home_response = get_user_home_response(client, headers)
    assert home_response.status_code == 404, home_response.text
    assert home_response.json()["code"] == "NOT_IN_HOME"

    # REJOIN FIRST HOME
    response = client.post(
        "/home/join",
        json={"invite_code": first_home_invite_code},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "HOME_JOINED"
    assert body["home"]["id"] == first_home_id
    assert body["home"]["member_count"] == first_home_member_count + 1

    joined_members = {
        member["username"]: member["role"] for member in body["home"]["members"]
    }
    assert joined_members[username] == "member"

    home_body = get_user_home_body(client, headers)
    assert home_body["id"] == first_home_id