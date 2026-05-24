from datetime import date
from uuid import UUID

import pytest

COST_SETTLEMENTS_ENDPOINT = "/inventory/costs/settlements"


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


def test_create_cost_settlement_updates_split(
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

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "3.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SETTLEMENT_CREATED"
    assert body["settlement"]["from_user_id"] == member1["user"]["id"]
    assert body["settlement"]["to_user_id"] == owner["user"]["id"]
    assert body["settlement"]["amount"] == "3.00"

    split = body["split"]
    assert split["code"] == "COST_SPLIT"

    members = members_by_user_id(split)

    assert members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert members[owner["user"]["id"]]["settled_received"] == "3.00"
    assert members[member1["user"]["id"]]["balance"] == "0.00"
    assert members[owner["user"]["id"]]["balance"] == "3.00"
    assert members[member2["user"]["id"]]["balance"] == "-3.00"

    assert transfers_as_tuples(split) == {
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }


def test_create_cost_settlement_allows_partial_payment_and_updates_split(
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
        name="public_cost_product_partial_settlement",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "1.50",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SETTLEMENT_CREATED"
    assert body["settlement"]["amount"] == "1.50"

    split = body["split"]
    members = members_by_user_id(split)

    assert members[member1["user"]["id"]]["settled_paid"] == "1.50"
    assert members[owner["user"]["id"]]["settled_received"] == "1.50"
    assert members[member1["user"]["id"]]["balance"] == "-1.50"
    assert members[owner["user"]["id"]]["balance"] == "4.50"
    assert members[member2["user"]["id"]]["balance"] == "-3.00"

    assert transfers_as_tuples(split) == {
        (member1["user"]["id"], owner["user"]["id"], "1.50"),
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }


def test_create_cost_settlement_rejects_amount_higher_than_pending_transfer(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
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

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "3.01",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "SETTLEMENT_AMOUNT_TOO_HIGH"
    assert "error" in body


@pytest.mark.parametrize("amount", ["0", "-1.00", "1.999", "abc"])
def test_create_cost_settlement_rejects_invalid_amount(
    client,
    shared_home_setup,
    seed_product_db,
    amount,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="public_cost_product_invalid_amount",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": amount,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "INVALID_SETTLEMENT_AMOUNT"
    assert "error" in body


def test_create_cost_settlement_rejects_same_payer_and_receiver(
    client,
    shared_home_setup,
):
    owner = shared_home_setup["owner"]
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": owner["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "1.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "SAME_PAYER_AND_RECEIVER"
    assert "error" in body


def test_create_cost_settlement_rejects_payer_outside_home(
    client,
    shared_home_setup,
    outsider_user,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="public_cost_product_payer_outside_home",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": outsider_user["user"]["id"],
            "to_user_id": member1["user"]["id"],
            "amount": "1.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "PAYER_NOT_IN_HOME"
    assert "error" in body


def test_create_cost_settlement_rejects_receiver_outside_home(
    client,
    shared_home_setup,
    outsider_user,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="public_cost_product_receiver_outside_home",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": outsider_user["user"]["id"],
            "amount": "1.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "RECEIVER_NOT_IN_HOME"
    assert "error" in body


def test_create_cost_settlement_rejects_transfer_not_pending(
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
        name="public_cost_product_transfer_not_pending",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    # No existe transferencia pendiente de owner a member1
    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": owner["user"]["id"],
            "to_user_id": member1["user"]["id"],
            "amount": "1.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "TRANSFER_NOT_PENDING"
    assert "error" in body

    # Tampoco existe transferencia pendiente de member2 a member1
    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member2["user"]["id"],
            "to_user_id": member1["user"]["id"],
            "amount": "1.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "TRANSFER_NOT_PENDING"
    assert "error" in body


def test_create_cost_settlement_rejects_invalid_date_range(
    client,
    shared_home_setup,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "1.00",
            "date_from": "2026-02-01",
            "date_to": "2026-01-01",
        },
        headers=headers,
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "INVALID_DATE_RANGE"
    assert "error" in body


def test_non_member_cannot_create_cost_settlement(client, outsider_user):
    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": outsider_user["user"]["id"],
            "to_user_id": outsider_user["user"]["id"],
            "amount": "1.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=outsider_user["headers"],
    )

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_create_cost_settlement(client, headers):
    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": "00000000-0000-0000-0000-000000000001",
            "to_user_id": "00000000-0000-0000-0000-000000000002",
            "amount": "1.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


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
def test_create_cost_settlement_rejects_invalid_date_formats(
    client,
    shared_home_setup,
    date_from,
    date_to,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    headers = shared_home_setup["owner_headers"]

    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "1.00",
            "date_from": date_from,
            "date_to": date_to,
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text


def test_create_cost_settlement_with_exact_pending_amount_clears_that_debt(
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
        name="public_cost_product_exact_settlement",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    # La deuda pendiente real de member1 hacia owner es 3.00
    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "3.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] == "COST_SETTLEMENT_CREATED"
    assert body["settlement"]["amount"] == "3.00"

    split = body["split"]
    assert split["code"] == "COST_SPLIT"

    members = members_by_user_id(split)

    assert members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert members[owner["user"]["id"]]["settled_received"] == "3.00"

    # La deuda de member1 queda completamente liquidada
    assert members[member1["user"]["id"]]["balance"] == "0.00"

    # Sigue quedando pendiente solo la deuda de member2
    assert members[owner["user"]["id"]]["balance"] == "3.00"
    assert members[member2["user"]["id"]]["balance"] == "-3.00"

    assert transfers_as_tuples(split) == {
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }


def test_create_cost_settlements_with_exact_pending_amounts_clear_all_debts(
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
        name="public_cost_product_exact_full_settlement",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    # Primera liquidación exacta: member1 salda toda su deuda (3.00)
    first_response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member1["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "3.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert first_response.status_code == 200, first_response.text
    first_body = first_response.json()

    assert first_body["code"] == "COST_SETTLEMENT_CREATED"
    assert first_body["settlement"]["amount"] == "3.00"

    first_split = first_body["split"]
    assert first_split["code"] == "COST_SPLIT"

    first_members = members_by_user_id(first_split)

    assert first_members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert first_members[owner["user"]["id"]]["settled_received"] == "3.00"
    assert first_members[member1["user"]["id"]]["balance"] == "0.00"
    assert first_members[owner["user"]["id"]]["balance"] == "3.00"
    assert first_members[member2["user"]["id"]]["balance"] == "-3.00"

    assert transfers_as_tuples(first_split) == {
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }

    # Segunda liquidación exacta: member2 salda toda su deuda restante (3.00)
    second_response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": member2["user"]["id"],
            "to_user_id": owner["user"]["id"],
            "amount": "3.00",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        },
        headers=headers,
    )

    assert second_response.status_code == 200, second_response.text
    second_body = second_response.json()

    assert second_body["code"] == "COST_SETTLEMENT_CREATED"
    assert second_body["settlement"]["amount"] == "3.00"

    second_split = second_body["split"]
    assert second_split["code"] == "COST_SPLIT"

    second_members = members_by_user_id(second_split)

    assert second_members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert second_members[member2["user"]["id"]]["settled_paid"] == "3.00"
    assert second_members[owner["user"]["id"]]["settled_received"] == "6.00"

    assert second_members[member1["user"]["id"]]["balance"] == "0.00"
    assert second_members[member2["user"]["id"]]["balance"] == "0.00"
    assert second_members[owner["user"]["id"]]["balance"] == "0.00"

    assert transfers_as_tuples(second_split) == set()
