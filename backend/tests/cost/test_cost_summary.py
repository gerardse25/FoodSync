from datetime import date, timedelta
from uuid import UUID

import pytest


COST_SUMMARY_ENDPOINT = "/inventory/costs/summary"


def seed_cost_product(
    client,
    seed_product_db,
    *,
    home_id,
    created_by_ctx,
    name,
    category,
    quantity,
    price,
    purchase_date,
    paid_by_user_id,
    owner_user_ids=None,
):
    owner_user_ids = owner_user_ids or []

    seeded = seed_product_db(
        home_id=home_id,
        created_by_ctx=created_by_ctx,
        name=name,
        category=category,
        quantity=quantity,
        price=price,
        purchase_date=purchase_date,
        owner_user_ids=owner_user_ids,
    )

    db = client.db_session_factory()
    try:
        inventory_models = client.app_modules["inventory_models"]
        InventoryProduct = inventory_models.InventoryProduct

        row = (
            db.query(InventoryProduct)
            .filter(InventoryProduct.id_inventari == int(seeded["id"]))
            .first()
        )
        assert row is not None

        row.paid_by_user_id = UUID(str(paid_by_user_id))
        row.es_privat = bool(owner_user_ids)
        db.commit()
    finally:
        db.close()

    return seeded


def patch_product_fields(
    client,
    *,
    product_id,
    preu_marker="KEEP",
    data_compra_marker="KEEP",
):
    db = client.db_session_factory()
    try:
        inventory_models = client.app_modules["inventory_models"]
        InventoryProduct = inventory_models.InventoryProduct

        row = (
            db.query(InventoryProduct)
            .filter(InventoryProduct.id_inventari == int(product_id))
            .first()
        )
        assert row is not None

        if preu_marker != "KEEP":
            row.preu = preu_marker
        if data_compra_marker != "KEEP":
            row.data_compra = data_compra_marker

        db.commit()
    finally:
        db.close()


def deactivate_home(client, home_id):
    db = client.db_session_factory()
    try:
        home_models = client.app_modules["home_models"]
        Home = home_models.Home

        row = db.query(Home).filter(Home.id == UUID(str(home_id))).first()
        assert row is not None
        row.is_active = False
        db.commit()
    finally:
        db.close()


def assert_no_cost_data(response):
    assert response.status_code in (200, 404), response.text
    body = response.json()
    assert body["code"] == "NO_COST_DATA"


def test_cost_summary_groups_costs_by_month_and_computes_total(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="rice_january",
        category="RICE",
        quantity=1,
        price="10.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
    )
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="milk_january",
        category="MILK",
        quantity=1,
        price="5.50",
        purchase_date=date(2026, 1, 20),
        paid_by_user_id=owner["user"]["id"],
    )
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="eggs_february",
        category="EGGS",
        quantity=1,
        price="7.00",
        purchase_date=date(2026, 2, 5),
        paid_by_user_id=owner["user"]["id"],
    )

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-02-28",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SUMMARY"
    assert body["period"] == "monthly"
    assert body["total"] == "22.50"
    assert body["item_count"] == 3
    assert len(body["series"]) == 2


def test_cost_summary_groups_costs_by_week(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="week1_product",
        category="RICE",
        quantity=1,
        price="10.00",
        purchase_date=date(2026, 1, 5),
        paid_by_user_id=owner["user"]["id"],
    )
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="week2_product",
        category="MILK",
        quantity=1,
        price="5.00",
        purchase_date=date(2026, 1, 12),
        paid_by_user_id=owner["user"]["id"],
    )

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "weekly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SUMMARY"
    assert body["period"] == "weekly"
    assert body["total"] == "15.00"
    assert body["item_count"] == 2
    assert len(body["series"]) >= 2


def test_cost_summary_groups_costs_by_year(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="year_2025_product",
        category="RICE",
        quantity=1,
        price="8.00",
        purchase_date=date(2025, 6, 10),
        paid_by_user_id=owner["user"]["id"],
    )
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="year_2026_product",
        category="MILK",
        quantity=1,
        price="12.00",
        purchase_date=date(2026, 3, 15),
        paid_by_user_id=owner["user"]["id"],
    )

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "yearly",
            "date_from": "2025-01-01",
            "date_to": "2026-12-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SUMMARY"
    assert body["period"] == "yearly"
    assert body["total"] == "20.00"
    assert body["item_count"] == 2
    assert len(body["series"]) == 2


def test_cost_summary_rejects_invalid_period(client, shared_home_setup):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "daily",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == "INVALID_PERIOD"


@pytest.mark.parametrize(
    "date_from,date_to",
    [
        ("01/01/2026", "2026-01-31"),
        ("2026-01-01", "31/01/2026"),
        ("2026/01/01", "2026-01-31"),
        ("2026-01-01", "2026/01/31"),
        ("not-a-date", "2026-01-31"),
        ("2026-01-01", "not-a-date"),
    ],
)
def test_cost_summary_rejects_invalid_date_formats(
    client,
    shared_home_setup,
    date_from,
    date_to,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": date_from,
            "date_to": date_to,
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == "INVALID_DATE_FORMAT"


def test_cost_summary_rejects_date_to_before_date_from(client, shared_home_setup):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-02-01",
            "date_to": "2026-01-01",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "INVALID_DATE_RANGE"

def test_cost_summary_rejects_to_in_the_future_date_to(client, shared_home_setup):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2099-01-01",
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] in ("INVALID_DATE_RANGE")

def test_cost_summary_rejects_future_date_to(client, shared_home_setup):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": date.today() + timedelta(days=2),
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] in ("INVALID_DATE_RANGE")


def test_cost_summary_returns_no_cost_data_for_very_old_date_range(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "yearly",
            "date_from": "1900-01-01",
            "date_to": "1901-01-01",
        },
        headers=headers,
    )

    assert_no_cost_data(response)


def test_cost_summary_returns_no_cost_data_for_home_without_products(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert_no_cost_data(response)


def test_member_can_get_cost_summary(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["member1_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="member_visible_cost_product",
        category="RICE",
        quantity=1,
        price="11.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
    )

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "COST_SUMMARY"
    assert body["total"] == "11.00"


def test_non_member_cannot_get_cost_summary(client, outsider_user):
    response = client.get(COST_SUMMARY_ENDPOINT, headers=outsider_user["headers"])

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


def test_unauthenticated_user_cannot_get_cost_summary(client):
    response = client.get(COST_SUMMARY_ENDPOINT)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_cost_summary_returns_home_not_found_when_home_is_inactive(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]
    deactivate_home(client, shared_home_setup["home_id"])

    response = client.get(COST_SUMMARY_ENDPOINT, headers=headers)

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "HOME_NOT_FOUND"


def test_cost_summary_only_counts_products_from_user_home(
    client,
    shared_home_setup,
    outsider_user,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    # producto en la home del owner
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="owner_home_cost_product",
        category="RICE",
        quantity=1,
        price="10.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
    )

    # el outsider crea su propia home y añade un producto allí
    outsider_home_response = client.post(
        "/home/",
        json={"name": "Outsider Home"},
        headers=outsider_user["headers"],
    )
    assert outsider_home_response.status_code == 201, outsider_home_response.text
    outsider_home_id = outsider_home_response.json()["home"]["id"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=outsider_home_id,
        created_by_ctx=outsider_user,
        name="outsider_home_cost_product",
        category="MILK",
        quantity=1,
        price="99.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=outsider_user["user"]["id"],
    )

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "COST_SUMMARY"
    assert body["total"] == "10.00"
    assert body["item_count"] == 1


def test_cost_summary_changes_after_adding_product(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    first_response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )
    assert_no_cost_data(first_response)

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="new_cost_product",
        category="RICE",
        quantity=1,
        price="12.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
    )

    second_response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert second_response.status_code == 200, second_response.text
    body = second_response.json()
    assert body["code"] == "COST_SUMMARY"
    assert body["total"] == "12.00"
    assert body["item_count"] == 1


def test_cost_summary_changes_after_deleting_product(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seeded = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="deletable_cost_product",
        category="RICE",
        quantity=1,
        price="12.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
    )

    first_response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )
    assert first_response.status_code == 200, first_response.text
    assert first_response.json()["total"] == "12.00"

    delete_response = client.request(
        "DELETE",
        "/inventory_delete_product",
        json={"id_producte": str(seeded["id"])},
        headers=headers,
    )
    assert delete_response.status_code == 200, delete_response.text

    second_response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )
    assert_no_cost_data(second_response)


def test_cost_summary_changes_after_modifying_product_price(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seeded = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="price_edit_cost_product",
        category="RICE",
        quantity=1,
        price="10.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
    )

    first_response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )
    assert first_response.status_code == 200, first_response.text
    assert first_response.json()["total"] == "10.00"

    db = client.db_session_factory()
    try:
        inventory_models = client.app_modules["inventory_models"]
        InventoryProduct = inventory_models.InventoryProduct

        row = (
            db.query(InventoryProduct)
            .filter(InventoryProduct.id_inventari == int(seeded["id"]))
            .first()
        )
        assert row is not None
        row.preu = "15.00"
        db.commit()
    finally:
        db.close()

    second_response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )
    assert second_response.status_code == 200, second_response.text
    assert second_response.json()["total"] == "15.00"


def test_cost_summary_ignores_products_without_price_or_purchase_date(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="valid_cost_product",
        category="RICE",
        quantity=1,
        price="10.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
    )

    no_price = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="no_price_product",
        category="MILK",
        quantity=1,
        price="3.00",
        purchase_date=date(2026, 1, 11),
        paid_by_user_id=owner["user"]["id"],
    )
    patch_product_fields(client, product_id=no_price["id"], preu_marker=None)

    no_purchase_date = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="no_purchase_date_product",
        category="EGGS",
        quantity=1,
        price="4.00",
        purchase_date=date(2026, 1, 12),
        paid_by_user_id=owner["user"]["id"],
    )
    patch_product_fields(
        client,
        product_id=no_purchase_date["id"],
        data_compra_marker=None,
    )

    response = client.get(
        COST_SUMMARY_ENDPOINT,
        params={
            "period": "monthly",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SUMMARY"
    assert body["total"] == "10.00"
    assert body["item_count"] == 1