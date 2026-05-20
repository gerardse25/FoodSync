from datetime import date, timedelta

import pytest

SCAN_NOTIFICATIONS_ENDPOINT = "/notifications/scan"
LIST_NOTIFICATIONS_ENDPOINT = "/notifications"
PREFERENCES_ENDPOINT = "/notifications/preferences"


def scan_notifications_request(client, headers):
    return client.post(SCAN_NOTIFICATIONS_ENDPOINT, headers=headers)


def list_notifications_request(client, headers):
    return client.get(LIST_NOTIFICATIONS_ENDPOINT, headers=headers)


def update_preferences_request(
    client, headers, notifications_enabled, expiration_notice_days
):
    return client.patch(
        PREFERENCES_ENDPOINT,
        headers=headers,
        json={
            "notifications_enabled": notifications_enabled,
            "expiration_notice_days": expiration_notice_days,
        },
    )


def test_user_in_home_can_scan_notifications_and_create_expiring_notification(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner_headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="expiring_rice_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=2),
        owner_user_ids=[],
    )

    response = scan_notifications_request(client, owner_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATIONS_SCAN_COMPLETED"
    assert body["created_count"] >= 1


def test_scan_notifications_creates_notifications_for_all_members_on_public_product(
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
        name="public_expiring_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[],
    )

    scan_response = scan_notifications_request(client, owner_headers)
    assert scan_response.status_code == 200, scan_response.text
    assert scan_response.json()["code"] == "NOTIFICATIONS_SCAN_COMPLETED"

    owner_notifications = list_notifications_request(
        client, shared_home_setup["owner_headers"]
    )
    member1_notifications = list_notifications_request(
        client, shared_home_setup["member1_headers"]
    )
    member2_notifications = list_notifications_request(
        client, shared_home_setup["member2_headers"]
    )

    assert owner_notifications.status_code == 200, owner_notifications.text
    assert member1_notifications.status_code == 200, member1_notifications.text
    assert member2_notifications.status_code == 200, member2_notifications.text

    owner_names = {
        n["nom_producte"] for n in owner_notifications.json()["notifications"]
    }
    member1_names = {
        n["nom_producte"] for n in member1_notifications.json()["notifications"]
    }
    member2_names = {
        n["nom_producte"] for n in member2_notifications.json()["notifications"]
    }

    assert "public_expiring_product" in owner_names
    assert "public_expiring_product" in member1_names
    assert "public_expiring_product" in member2_names


def test_scan_notifications_creates_private_product_notification_only_for_owner(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner_headers = shared_home_setup["owner_headers"]
    owner_ctx = shared_home_setup["owner"]
    owner_id = shared_home_setup["owner"]["user"]["id"]
    home_id = shared_home_setup["home_id"]

    seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="private_expiring_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[owner_id],
    )

    scan_response = scan_notifications_request(client, owner_headers)
    assert scan_response.status_code == 200, scan_response.text
    assert scan_response.json()["code"] == "NOTIFICATIONS_SCAN_COMPLETED"

    owner_notifications = list_notifications_request(
        client, shared_home_setup["owner_headers"]
    )
    member1_notifications = list_notifications_request(
        client, shared_home_setup["member1_headers"]
    )

    assert owner_notifications.status_code == 200, owner_notifications.text
    assert member1_notifications.status_code == 200, member1_notifications.text

    owner_names = {
        n["nom_producte"] for n in owner_notifications.json()["notifications"]
    }
    member1_names = {
        n["nom_producte"] for n in member1_notifications.json()["notifications"]
    }

    assert "private_expiring_product" in owner_names
    assert "private_expiring_product" not in member1_names


def test_scan_notifications_does_not_create_notifications_for_far_future_products(
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
        name="far_future_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=10),
        owner_user_ids=[],
    )

    response = scan_notifications_request(client, owner_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATIONS_SCAN_COMPLETED"
    assert body["created_count"] == 0


def test_scan_notifications_does_not_duplicate_existing_notifications(
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
        name="duplicate_scan_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[],
    )

    first_response = scan_notifications_request(client, owner_headers)
    assert first_response.status_code == 200, first_response.text
    first_body = first_response.json()
    assert first_body["code"] == "NOTIFICATIONS_SCAN_COMPLETED"
    assert first_body["created_count"] >= 1

    second_response = scan_notifications_request(client, owner_headers)
    assert second_response.status_code == 200, second_response.text
    second_body = second_response.json()
    assert second_body["code"] == "NOTIFICATIONS_SCAN_COMPLETED"
    assert second_body["created_count"] == 0


def test_scan_notifications_respects_disabled_preferences(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    owner_ctx = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]

    pref_response = update_preferences_request(
        client,
        member1_headers,
        notifications_enabled=False,
        expiration_notice_days=3,
    )
    assert pref_response.status_code == 200, pref_response.text
    assert pref_response.json()["code"] == "NOTIFICATION_PREFERENCES_UPDATED"

    seed_product_db(
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="disabled_pref_product",
        category="RICE",
        quantity=1,
        expiration_date=date.today() + timedelta(days=1),
        owner_user_ids=[],
    )

    scan_response = scan_notifications_request(client, owner_headers)
    assert scan_response.status_code == 200, scan_response.text
    assert scan_response.json()["code"] == "NOTIFICATIONS_SCAN_COMPLETED"

    owner_notifications = list_notifications_request(client, owner_headers)
    member1_notifications = list_notifications_request(client, member1_headers)

    owner_names = {
        n["nom_producte"] for n in owner_notifications.json()["notifications"]
    }
    member1_names = {
        n["nom_producte"] for n in member1_notifications.json()["notifications"]
    }

    assert "disabled_pref_product" in owner_names
    assert "disabled_pref_product" not in member1_names


def test_user_not_in_home_cannot_scan_notifications(client, outsider_user):
    response = scan_notifications_request(client, outsider_user["headers"])

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_scan_notifications(client, headers):
    response = scan_notifications_request(client, headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"
