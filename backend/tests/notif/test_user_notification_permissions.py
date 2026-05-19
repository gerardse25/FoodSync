import pytest

NOTIF_PREFIX = "/notifications"
NOTIF_PREFERENCES_ENDPOINT = NOTIF_PREFIX + "/preferences"

GET_PREFERENCES_CODE = "NOTIFICATION_PREFERENCES_RETRIEVED"
UPDATE_PREFERENCES_CODE = "NOTIFICATION_PREFERENCES_UPDATED"


def view_preferences_request(client, headers):
    return client.get(NOTIF_PREFERENCES_ENDPOINT, headers=headers)


def update_preferences_request(client, headers, notifications_enabled, expiration_notice_days):
    return client.patch(
        NOTIF_PREFERENCES_ENDPOINT,
        headers=headers,
        json={
            "notifications_enabled": notifications_enabled,
            "expiration_notice_days": expiration_notice_days,
        },
    )


def test_new_user_has_default_notifications(client, outsider_user):
    headers = outsider_user["headers"]
    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 3


def test_user_not_in_home_can_update_notification_preferences(client, outsider_user):
    headers = outsider_user["headers"]
    response = update_preferences_request(client, headers, True, 4)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == UPDATE_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 4


def test_user_in_home_can_update_notification_preferences(client, owner_home):
    headers = owner_home["owner"]["headers"]
    response = update_preferences_request(client, headers, True, 4)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == UPDATE_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 4


def test_user_not_in_home_can_view_notification_preferences(client, outsider_user):
    headers = outsider_user["headers"]
    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 3


def test_user_in_home_can_view_notification_preferences(client, owner_home):
    headers = owner_home["owner"]["headers"]
    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 3


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_view_notification_preferences(client, headers):
    response = view_preferences_request(client, headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_update_notification_preferences(client, headers):
    response = client.patch(
        NOTIF_PREFERENCES_ENDPOINT,
        headers=headers,
        json={"notifications_enabled": True, "expiration_notice_days": 4},
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("expiration_notice_days", [0, 1, 30])
def test_update_notification_preferences_with_valid_limit_notice_days(
    client,
    owner_home,
    expiration_notice_days,
):
    headers = owner_home["owner"]["headers"]
    response = update_preferences_request(client, headers, True, expiration_notice_days)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == UPDATE_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == expiration_notice_days


@pytest.mark.parametrize("expiration_notice_days", [-1, 31])
def test_update_notification_preferences_with_invalid_notice_days(
    client,
    owner_home,
    expiration_notice_days,
):
    headers = owner_home["owner"]["headers"]
    response = update_preferences_request(client, headers, True, expiration_notice_days)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATION_PREFERENCES_INVALID"



def test_update_notification_preferences_with_empty_expiration_notice_days_fails(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]
    response = client.patch(
        NOTIF_PREFERENCES_ENDPOINT,
        headers=headers,
        json={
            "notifications_enabled": True,
            "expiration_notice_days": "",
        },
    )

    assert response.status_code == 422, response.text


def test_update_notification_preferences_not_enabled_keeps_expiration_notice_days(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]
    response = update_preferences_request(client, headers, False, 4)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == UPDATE_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is False
    assert body["preferences"]["expiration_notice_days"] == 4


def test_user_joins_home_does_not_change_notification_preferences(
    client,
    outsider_user,
    owner_home,
):
    headers = outsider_user["headers"]
    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    before_notif_enabled_value = body["preferences"]["notifications_enabled"]
    before_notice_days_value = body["preferences"]["expiration_notice_days"]

    response = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] == before_notif_enabled_value
    assert body["preferences"]["expiration_notice_days"] == before_notice_days_value


def test_user_creates_home_does_not_change_notification_preferences(
    client,
    outsider_user,
):
    headers = outsider_user["headers"]
    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    before_notif_enabled_value = body["preferences"]["notifications_enabled"]
    before_notice_days_value = body["preferences"]["expiration_notice_days"]

    response = client.post("/home/", json={"name": "New Home"}, headers=headers)
    assert response.status_code == 201, response.text

    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] == before_notif_enabled_value
    assert body["preferences"]["expiration_notice_days"] == before_notice_days_value


def test_user_updated_notification_preferences_persist(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]
    response = update_preferences_request(client, headers, True, 4)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == UPDATE_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 4

    response = view_preferences_request(client, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 4


def test_update_only_notice_days_keeps_notifications_enabled_value(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]

    response = view_preferences_request(client, headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 3

    response = client.patch(
        NOTIF_PREFERENCES_ENDPOINT,
        headers=headers,
        json={
            "notifications_enabled": True,
            "expiration_notice_days": 4,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == UPDATE_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 4

    response = view_preferences_request(client, headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 4

def test_update_only_notifications_enabled_value_keeps_expiration_notice_days(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]

    response = view_preferences_request(client, headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is True
    assert body["preferences"]["expiration_notice_days"] == 3

    response = client.patch(
        NOTIF_PREFERENCES_ENDPOINT,
        headers=headers,
        json={
            "notifications_enabled": False,
            "expiration_notice_days": 3,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == UPDATE_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is False
    assert body["preferences"]["expiration_notice_days"] == 3

    response = view_preferences_request(client, headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == GET_PREFERENCES_CODE
    assert body["preferences"]["notifications_enabled"] is False
    assert body["preferences"]["expiration_notice_days"] == 3


def test_update_notification_preferences_without_notifications_enabled_returns_validation_error(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]

    response = client.patch(
        NOTIF_PREFERENCES_ENDPOINT,
        headers=headers,
        json={
            "expiration_notice_days": 5,
        },
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert "detail" in body


def test_update_notification_preferences_without_expiration_notice_days_returns_validation_error(
    client,
    owner_home,
):
    headers = owner_home["owner"]["headers"]

    response = client.patch(
        NOTIF_PREFERENCES_ENDPOINT,
        headers=headers,
        json={
            "notifications_enabled": False,
        },
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert "detail" in body