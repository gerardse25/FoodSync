import pytest
from freezegun import freeze_time
from datetime import date

CADUCITY_ENTRY_ENDPOINT = "/expiration/estimate"


def make_category_purchase_date_json(categoria, data_compra=None):
    payload = {"categoria": categoria}
    if data_compra is not None:
        payload["data_compra"] = data_compra
    return payload


def assert_backend_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "detail" in body or "error" in body


def test_valid_category_and_purchase_date_return_valid_expiration(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        CADUCITY_ENTRY_ENDPOINT,
        json=make_category_purchase_date_json("RICE", "2026-01-01"),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "EXPIRATION_ESTIMATED"
    assert body["categoria"] == "RICE"
    assert body["dies_caducitat_estimats"] == 365
    assert body["data_compra"] == "2026-01-01"
    assert body["data_caducitat"] == "2027-01-01"
    assert body["data_caducitat_estimada"] is True

def test_two_valid_categories_return_different_estimated_expirations(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    rice_response = client.post(
        CADUCITY_ENTRY_ENDPOINT,
        json=make_category_purchase_date_json("RICE", "2026-01-01"),
        headers=headers,
    )
    assert rice_response.status_code == 200, rice_response.text
    rice_body = rice_response.json()
    assert rice_body["code"] == "EXPIRATION_ESTIMATED"

    poultry_response = client.post(
        CADUCITY_ENTRY_ENDPOINT,
        json=make_category_purchase_date_json("POULTRY", "2026-01-01"),
        headers=headers,
    )
    assert poultry_response.status_code == 200, poultry_response.text
    poultry_body = poultry_response.json()
    assert poultry_body["code"] == "EXPIRATION_ESTIMATED"

    assert rice_body["categoria"] == "RICE"
    assert poultry_body["categoria"] == "POULTRY"

    assert rice_body["dies_caducitat_estimats"] == 365
    assert poultry_body["dies_caducitat_estimats"] == 2

    assert rice_body["data_caducitat"] == "2027-01-01"
    assert poultry_body["data_caducitat"] == "2026-01-03"

    assert rice_body["data_caducitat"] != poultry_body["data_caducitat"]



def test_invalid_category_return_error(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        CADUCITY_ENTRY_ENDPOINT,
        json=make_category_purchase_date_json("invalid_category", "2026-01-01"),
        headers=headers,
    )

    assert response.status_code == 400, response.text
    body = response.json()

    assert body["code"] == "EXPIRATION_ESTIMATION_NOT_POSSIBLE"
    assert body["categoria"] == "invalid_category"
    assert body["data_caducitat_estimada"] is False


def test_purchase_date_same_as_system_date_returns_estimated_expiration(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    with freeze_time("2026-01-10"):
        response = client.post(
            CADUCITY_ENTRY_ENDPOINT,
            json=make_category_purchase_date_json("RICE", "2026-01-10"),
            headers=headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "EXPIRATION_ESTIMATED"
    assert body["categoria"] == "RICE"
    assert body["dies_caducitat_estimats"] == 365
    assert body["data_compra"] == "2026-01-10"
    assert body["data_caducitat"] == "2027-01-10"
    assert body["data_caducitat_estimada"] is True

@pytest.mark.parametrize(
    "purchase_date, expected_expiration_date",
    [
        ("2025-01-10", "2026-01-10"),
        ("2025-01-11", "2026-01-11"),
    ],
)
def test_purchase_date_within_valid_limit_returns_estimated_expiration(
    client,
    shared_home_setup,
    purchase_date,
    expected_expiration_date,
):
    headers = shared_home_setup["owner_headers"]

    with freeze_time("2026-01-10"):
        response = client.post(
            CADUCITY_ENTRY_ENDPOINT,
            json=make_category_purchase_date_json("RICE", purchase_date),
            headers=headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "EXPIRATION_ESTIMATED"
    assert body["categoria"] == "RICE"
    assert body["dies_caducitat_estimats"] == 365
    assert body["data_compra"] == purchase_date
    assert body["data_caducitat"] == expected_expiration_date
    assert body["data_caducitat_estimada"] is True


@pytest.mark.parametrize(
    "date, expected_code",
    [
        ("2025-01-09", "PURCHASE_DATE_TOO_OLD"),
        ("2026-01-11", "PURCHASE_DATE_IN_FUTURE"),
    ],
)
def test_invalid_date_return_error(
    client,
    shared_home_setup,
    date, 
    expected_code
):
    headers = shared_home_setup["owner_headers"]


    with freeze_time("2026-01-01"):
        response = client.post(
            CADUCITY_ENTRY_ENDPOINT,
            json=make_category_purchase_date_json("RICE", date),
            headers=headers,
        )
        assert response.status_code == 400, response.text
        body = response.json()
        assert body["code"] == expected_code

    assert body["data_caducitat_estimada"] is False


def test_expiration_estimation_does_not_depend_on_hour_or_minutes(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    with freeze_time("2026-01-10 08:15:00"):
        morning_response = client.post(
            CADUCITY_ENTRY_ENDPOINT,
            json={"categoria": "RICE"},
            headers=headers,
        )
        assert morning_response.status_code == 200, morning_response.text
        morning_body = morning_response.json()
        assert morning_body["code"] == "EXPIRATION_ESTIMATED"

    with freeze_time("2026-01-10 23:45:00"):
        night_response = client.post(
            CADUCITY_ENTRY_ENDPOINT,
            json={"categoria": "RICE"},
            headers=headers,
        )
        assert night_response.status_code == 200, night_response.text
        night_body = night_response.json()
        assert night_body["code"] == "EXPIRATION_ESTIMATED"

    assert morning_body["data_compra"] == "2026-01-10"
    assert night_body["data_compra"] == "2026-01-10"
    assert morning_body["data_caducitat"] == night_body["data_caducitat"]
    assert morning_body["dies_caducitat_estimats"] == night_body["dies_caducitat_estimats"]