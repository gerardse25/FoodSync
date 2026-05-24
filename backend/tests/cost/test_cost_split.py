from datetime import date
from uuid import UUID

import pytest

COST_SPLIT_ENDPOINT = "/inventory/costs/split"


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


def members_by_user_id(split_body):
    return {member["user_id"]: member for member in split_body["members"]}


def transfers_as_tuples(split_body):
    return {
        (item["from_user_id"], item["to_user_id"], item["amount"])
        for item in split_body["transfers"]
    }


def test_cost_split_public_product_is_shared_between_all_active_members(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="public_cost_product",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "9.00"

    members = members_by_user_id(body)

    owner_row = members[owner["user"]["id"]]
    member1_row = members[member1["user"]["id"]]
    member2_row = members[member2["user"]["id"]]

    assert owner_row["paid"] == "9.00"
    assert owner_row["should_pay"] == "3.00"
    assert owner_row["balance"] == "6.00"

    assert member1_row["paid"] == "0.00"
    assert member1_row["should_pay"] == "3.00"
    assert member1_row["balance"] == "-3.00"

    assert member2_row["paid"] == "0.00"
    assert member2_row["should_pay"] == "3.00"
    assert member2_row["balance"] == "-3.00"

    assert transfers_as_tuples(body) == {
        (member1["user"]["id"], owner["user"]["id"], "3.00"),
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }


def test_cost_split_private_product_is_shared_only_between_private_owners(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member1,
        name="private_cost_product",
        category="HARD_CHEESE",
        quantity=1,
        price="8.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=member1["user"]["id"],
        owner_user_ids=[member1["user"]["id"], member2["user"]["id"]],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "8.00"

    members = members_by_user_id(body)

    owner_row = members[owner["user"]["id"]]
    member1_row = members[member1["user"]["id"]]
    member2_row = members[member2["user"]["id"]]

    assert owner_row["paid"] == "0.00"
    assert owner_row["should_pay"] == "0.00"
    assert owner_row["balance"] == "0.00"

    assert member1_row["paid"] == "8.00"
    assert member1_row["should_pay"] == "4.00"
    assert member1_row["balance"] == "4.00"

    assert member2_row["paid"] == "0.00"
    assert member2_row["should_pay"] == "4.00"
    assert member2_row["balance"] == "-4.00"

    assert transfers_as_tuples(body) == {
        (member2["user"]["id"], member1["user"]["id"], "4.00"),
    }


def test_cost_split_private_product_owned_by_single_user_is_only_charged_to_that_user(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member1,
        name="single_owner_private_cost_product",
        category="HARD_CHEESE",
        quantity=1,
        price="8.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=member1["user"]["id"],
        owner_user_ids=[member1["user"]["id"]],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "8.00"

    members = members_by_user_id(body)

    owner_row = members[owner["user"]["id"]]
    member1_row = members[member1["user"]["id"]]
    member2_row = members[member2["user"]["id"]]

    assert owner_row["paid"] == "0.00"
    assert owner_row["should_pay"] == "0.00"
    assert owner_row["balance"] == "0.00"

    assert member1_row["paid"] == "8.00"
    assert member1_row["should_pay"] == "8.00"
    assert member1_row["balance"] == "0.00"

    assert member2_row["paid"] == "0.00"
    assert member2_row["should_pay"] == "0.00"
    assert member2_row["balance"] == "0.00"

    assert transfers_as_tuples(body) == set()


def test_cost_split_private_product_owned_by_all_members_is_shared_between_all_of_them(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="all_owners_private_cost_product",
        category="HARD_CHEESE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[
            owner["user"]["id"],
            member1["user"]["id"],
            member2["user"]["id"],
        ],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "9.00"

    members = members_by_user_id(body)

    owner_row = members[owner["user"]["id"]]
    member1_row = members[member1["user"]["id"]]
    member2_row = members[member2["user"]["id"]]

    assert owner_row["paid"] == "9.00"
    assert owner_row["should_pay"] == "3.00"
    assert owner_row["balance"] == "6.00"

    assert member1_row["paid"] == "0.00"
    assert member1_row["should_pay"] == "3.00"
    assert member1_row["balance"] == "-3.00"

    assert member2_row["paid"] == "0.00"
    assert member2_row["should_pay"] == "3.00"
    assert member2_row["balance"] == "-3.00"

    assert transfers_as_tuples(body) == {
        (member1["user"]["id"], owner["user"]["id"], "3.00"),
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }


def test_cost_split_private_product_paid_by_one_user_but_owned_by_another_user(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="private_product_paid_by_owner_owned_by_member2",
        category="HARD_CHEESE",
        quantity=1,
        price="8.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[member2["user"]["id"]],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "8.00"

    members = members_by_user_id(body)

    owner_row = members[owner["user"]["id"]]
    member1_row = members[member1["user"]["id"]]
    member2_row = members[member2["user"]["id"]]

    assert owner_row["paid"] == "8.00"
    assert owner_row["should_pay"] == "0.00"
    assert owner_row["balance"] == "8.00"

    assert member1_row["paid"] == "0.00"
    assert member1_row["should_pay"] == "0.00"
    assert member1_row["balance"] == "0.00"

    assert member2_row["paid"] == "0.00"
    assert member2_row["should_pay"] == "8.00"
    assert member2_row["balance"] == "-8.00"

    assert transfers_as_tuples(body) == {
        (member2["user"]["id"], owner["user"]["id"], "8.00"),
    }


def test_cost_split_private_product_paid_by_one_user_and_owned_by_other_members(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="private_product_paid_by_owner_owned_by_other_members",
        category="HARD_CHEESE",
        quantity=1,
        price="8.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[member1["user"]["id"], member2["user"]["id"]],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "8.00"

    members = members_by_user_id(body)

    owner_row = members[owner["user"]["id"]]
    member1_row = members[member1["user"]["id"]]
    member2_row = members[member2["user"]["id"]]

    assert owner_row["paid"] == "8.00"
    assert owner_row["should_pay"] == "0.00"
    assert owner_row["balance"] == "8.00"

    assert member1_row["paid"] == "0.00"
    assert member1_row["should_pay"] == "4.00"
    assert member1_row["balance"] == "-4.00"

    assert member2_row["paid"] == "0.00"
    assert member2_row["should_pay"] == "4.00"
    assert member2_row["balance"] == "-4.00"

    assert transfers_as_tuples(body) == {
        (member1["user"]["id"], owner["user"]["id"], "4.00"),
        (member2["user"]["id"], owner["user"]["id"], "4.00"),
    }


def test_cost_split_multiple_products_with_different_payers_are_aggregated_correctly(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    # público pagado por owner
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="public_owner_paid",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    # público pagado por member1
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member1,
        name="public_member1_paid",
        category="MILK",
        quantity=1,
        price="6.00",
        purchase_date=date(2026, 1, 11),
        paid_by_user_id=member1["user"]["id"],
        owner_user_ids=[],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "15.00"

    members = members_by_user_id(body)

    # cada uno debería pagar 5
    assert members[owner["user"]["id"]]["should_pay"] == "5.00"
    assert members[member1["user"]["id"]]["should_pay"] == "5.00"
    assert members[member2["user"]["id"]]["should_pay"] == "5.00"

    # pagado
    assert members[owner["user"]["id"]]["paid"] == "9.00"
    assert members[member1["user"]["id"]]["paid"] == "6.00"
    assert members[member2["user"]["id"]]["paid"] == "0.00"

    # balances
    assert members[owner["user"]["id"]]["balance"] == "4.00"
    assert members[member1["user"]["id"]]["balance"] == "1.00"
    assert members[member2["user"]["id"]]["balance"] == "-5.00"

    assert transfers_as_tuples(body) == {
        (member2["user"]["id"], owner["user"]["id"], "4.00"),
        (member2["user"]["id"], member1["user"]["id"], "1.00"),
    }


def test_cost_split_ignores_products_without_price_or_purchase_date(
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
        owner_user_ids=[],
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
        owner_user_ids=[],
    )

    no_purchase = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="no_purchase_product",
        category="EGGS",
        quantity=1,
        price="4.00",
        purchase_date=date(2026, 1, 12),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    db = client.db_session_factory()
    try:
        inventory_models = client.app_modules["inventory_models"]
        InventoryProduct = inventory_models.InventoryProduct

        row1 = (
            db.query(InventoryProduct)
            .filter(InventoryProduct.id_inventari == int(no_price["id"]))
            .first()
        )
        row2 = (
            db.query(InventoryProduct)
            .filter(InventoryProduct.id_inventari == int(no_purchase["id"]))
            .first()
        )

        row1.preu = None
        row2.data_compra = None
        db.commit()
    finally:
        db.close()

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "10.00"


def test_cost_split_returns_empty_split_when_home_has_no_cost_data(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "0.00"
    assert body["transfers"] == []

    for member in body["members"]:
        assert member["paid"] == "0.00"
        assert member["should_pay"] == "0.00"
        assert member["balance"] == "0.00"


def test_cost_split_rejects_invalid_date_range(client, shared_home_setup):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-02-01", "date_to": "2026-01-01"},
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "INVALID_DATE_RANGE"
    assert "error" in body


def test_member_can_get_cost_split(
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
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["code"] == "COST_SPLIT"


def test_non_member_cannot_get_cost_split(client, outsider_user):
    response = client.get(COST_SPLIT_ENDPOINT, headers=outsider_user["headers"])

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_get_cost_split(client, headers):
    response = client.get(COST_SPLIT_ENDPOINT, headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_cost_split_rounds_periodic_shares_correctly(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="periodic_decimal_cost_product",
        category="RICE",
        quantity=1,
        price="10.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SPLIT"
    assert body["total"] == "10.00"

    members = members_by_user_id(body)

    owner_row = members[owner["user"]["id"]]
    member1_row = members[member1["user"]["id"]]
    member2_row = members[member2["user"]["id"]]

    # Cada miembro debe tener una parte redondeada a 2 decimales
    assert owner_row["should_pay"] == "3.33"
    assert member1_row["should_pay"] == "3.33"
    assert member2_row["should_pay"] == "3.33"

    # El owner ha pagado todo
    assert owner_row["paid"] == "10.00"
    assert member1_row["paid"] == "0.00"
    assert member2_row["paid"] == "0.00"

    # Balance esperado tras redondeo
    assert owner_row["balance"] == "6.67"
    assert member1_row["balance"] == "-3.33"
    assert member2_row["balance"] == "-3.33"

    transfers = transfers_as_tuples(body)
    assert transfers == {
        (member1["user"]["id"], owner["user"]["id"], "3.33"),
        (member2["user"]["id"], owner["user"]["id"], "3.33"),
    }


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
def test_cost_split_rejects_invalid_date_formats(
    client,
    shared_home_setup,
    date_from,
    date_to,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={
            "date_from": date_from,
            "date_to": date_to,
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == "INVALID_DATE_FORMAT"
