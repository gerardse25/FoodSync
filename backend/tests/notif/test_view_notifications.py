from datetime import date, timedelta

import pytest

SCAN_NOTIFICATIONS_ENDPOINT = "/notifications/scan"
LIST_NOTIFICATIONS_ENDPOINT = "/notifications"


def scan_notifications_request(client, headers):
    return client.post(SCAN_NOTIFICATIONS_ENDPOINT, headers=headers)


def list_notifications_request(client, headers):
    return client.get(LIST_NOTIFICATIONS_ENDPOINT, headers=headers)


def mark_notification_as_read_request(client, notification_id, headers):
    return client.patch(f"/notifications/{notification_id}/read", headers=headers)


def test_list_notifications_returns_empty_list_when_user_has_no_notifications(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]

    response = list_notifications_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATIONS_RETRIEVED"
    assert body["notifications"] == []


def test_list_notifications_returns_created_notifications_for_user(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner_headers = shared_home_setup["owner_headers"]
    owner_ctx = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]

    seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="list_notifications_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[],
    )

    scan_response = scan_notifications_request(client, owner_headers)
    assert scan_response.status_code == 200, scan_response.text
    assert scan_response.json()["code"] == "NOTIFICATIONS_SCAN_COMPLETED"

    response = list_notifications_request(client, owner_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATIONS_RETRIEVED"
    assert len(body["notifications"]) >= 1

    notification = body["notifications"][0]
    assert "id" in notification
    assert "tipus" in notification
    assert "id_producte" in notification
    assert "nom_producte" in notification
    assert "data_caducitat" in notification
    assert "title" in notification
    assert "message" in notification
    assert "delivery_channel" in notification
    assert "delivery_status" in notification
    assert "is_read" in notification
    assert "created_at" in notification


def test_list_notifications_returns_only_notifications_of_authenticated_user(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    owner_ctx = shared_home_setup["owner"]
    owner_id = shared_home_setup["owner"]["user"]["id"]
    home_id = shared_home_setup["home_id"]

    seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="owner_private_notification_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[owner_id],
    )

    scan_response = scan_notifications_request(client, owner_headers)
    assert scan_response.status_code == 200, scan_response.text
    assert scan_response.json()["code"] == "NOTIFICATIONS_SCAN_COMPLETED"

    owner_list = list_notifications_request(client, owner_headers)
    member1_list = list_notifications_request(client, member1_headers)

    assert owner_list.status_code == 200, owner_list.text
    assert member1_list.status_code == 200, member1_list.text

    owner_names = {n["nom_producte"] for n in owner_list.json()["notifications"]}
    member1_names = {n["nom_producte"] for n in member1_list.json()["notifications"]}

    assert "owner_private_notification_product" in owner_names
    assert "owner_private_notification_product" not in member1_names


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_list_notifications(client, headers):
    response = list_notifications_request(client, headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_mark_notification_as_read_succeeds(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner_headers = shared_home_setup["owner_headers"]
    owner_ctx = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]

    seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="mark_read_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[],
    )

    scan_response = scan_notifications_request(client, owner_headers)
    assert scan_response.status_code == 200, scan_response.text

    list_response = list_notifications_request(client, owner_headers)
    assert list_response.status_code == 200, list_response.text
    notifications = list_response.json()["notifications"]
    assert len(notifications) >= 1

    target_notification = notifications[0]

    mark_response = mark_notification_as_read_request(
        client,
        target_notification["id"],
        owner_headers,
    )

    assert mark_response.status_code == 200, mark_response.text
    body = mark_response.json()
    assert body["code"] == "NOTIFICATION_MARKED_AS_READ"

    updated_list_response = list_notifications_request(client, owner_headers)
    assert updated_list_response.status_code == 200, updated_list_response.text
    updated_notifications = updated_list_response.json()["notifications"]

    updated_target = next(
        (n for n in updated_notifications if n["id"] == target_notification["id"]),
        None,
    )
    assert updated_target is not None
    assert updated_target["is_read"] is True


def test_mark_notification_as_read_with_invalid_id_returns_error(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]

    response = mark_notification_as_read_request(client, "invalid-id", headers)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATION_ID_INVALID"


def test_mark_notification_as_read_with_unknown_id_returns_error(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]

    response = mark_notification_as_read_request(
        client,
        "11111111-1111-1111-1111-111111111111",
        headers,
    )

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATION_NOT_FOUND"


def test_user_cannot_mark_notification_of_another_user_as_read(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    owner_ctx = shared_home_setup["owner"]
    owner_id = shared_home_setup["owner"]["user"]["id"]
    home_id = shared_home_setup["home_id"]

    seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="private_notification_for_owner_only",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[owner_id],
    )

    scan_response = scan_notifications_request(client, owner_headers)
    assert scan_response.status_code == 200, scan_response.text

    owner_list = list_notifications_request(client, owner_headers)
    assert owner_list.status_code == 200, owner_list.text
    owner_notifications = owner_list.json()["notifications"]
    assert len(owner_notifications) >= 1

    target_notification_id = owner_notifications[0]["id"]

    response = mark_notification_as_read_request(
        client,
        target_notification_id,
        member1_headers,
    )

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATION_NOT_FOUND"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_mark_notification_as_read(client, headers):
    response = mark_notification_as_read_request(
        client,
        "11111111-1111-1111-1111-111111111111",
        headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"
