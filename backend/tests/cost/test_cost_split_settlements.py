from datetime import date
from uuid import UUID

COST_SPLIT_ENDPOINT = "/inventory/costs/split"
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


def get_split(client, headers, *, date_from="2026-01-01", date_to="2026-01-31"):
    response = client.get(
        COST_SPLIT_ENDPOINT,
        params={"date_from": date_from, "date_to": date_to},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "COST_SPLIT"
    return body


def create_settlement(
    client,
    headers,
    *,
    from_user_id,
    to_user_id,
    amount,
    date_from="2026-01-01",
    date_to="2026-01-31",
):
    response = client.post(
        COST_SETTLEMENTS_ENDPOINT,
        json={
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "amount": amount,
            "date_from": date_from,
            "date_to": date_to,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "COST_SETTLEMENT_CREATED"
    assert body["split"]["code"] == "COST_SPLIT"
    return body


def test_split_then_partial_settlement_updates_pending_transfer(
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
        name="public_cost_product_partial_flow",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    initial_split = get_split(client, headers)
    initial_members = members_by_user_id(initial_split)

    assert initial_members[owner["user"]["id"]]["balance"] == "6.00"
    assert initial_members[member1["user"]["id"]]["balance"] == "-3.00"
    assert initial_members[member2["user"]["id"]]["balance"] == "-3.00"

    assert transfers_as_tuples(initial_split) == {
        (member1["user"]["id"], owner["user"]["id"], "3.00"),
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="1.50",
    )

    updated_split = settlement_body["split"]
    updated_members = members_by_user_id(updated_split)

    assert updated_members[member1["user"]["id"]]["settled_paid"] == "1.50"
    assert updated_members[owner["user"]["id"]]["settled_received"] == "1.50"

    assert updated_members[member1["user"]["id"]]["balance"] == "-1.50"
    assert updated_members[owner["user"]["id"]]["balance"] == "4.50"
    assert updated_members[member2["user"]["id"]]["balance"] == "-3.00"

    assert transfers_as_tuples(updated_split) == {
        (member1["user"]["id"], owner["user"]["id"], "1.50"),
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }


def test_split_then_exact_settlement_removes_that_transfer(
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
        name="public_cost_product_exact_flow",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.00",
    )

    updated_split = settlement_body["split"]
    updated_members = members_by_user_id(updated_split)

    assert updated_members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert updated_members[owner["user"]["id"]]["settled_received"] == "3.00"

    assert updated_members[member1["user"]["id"]]["balance"] == "0.00"
    assert updated_members[owner["user"]["id"]]["balance"] == "3.00"
    assert updated_members[member2["user"]["id"]]["balance"] == "-3.00"

    assert transfers_as_tuples(updated_split) == {
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }


def test_split_then_two_exact_settlements_clear_all_pending_transfers(
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
        name="public_cost_product_full_flow",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    first_settlement = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.00",
    )

    first_split = first_settlement["split"]
    assert transfers_as_tuples(first_split) == {
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }

    second_settlement = create_settlement(
        client,
        headers,
        from_user_id=member2["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.00",
    )

    final_split = second_settlement["split"]
    final_members = members_by_user_id(final_split)

    assert final_members[member1["user"]["id"]]["balance"] == "0.00"
    assert final_members[member2["user"]["id"]]["balance"] == "0.00"
    assert final_members[owner["user"]["id"]]["balance"] == "0.00"

    assert final_members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert final_members[member2["user"]["id"]]["settled_paid"] == "3.00"
    assert final_members[owner["user"]["id"]]["settled_received"] == "6.00"

    assert transfers_as_tuples(final_split) == set()


def test_settlement_then_recheck_split_returns_same_updated_state_split(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="public_cost_product_recheck_flow",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.00",
    )

    split_after_settlement = settlement_body["split"]
    split_rechecked = get_split(client, headers)

    assert split_after_settlement["total"] == split_rechecked["total"]
    assert split_after_settlement["members"] == split_rechecked["members"]
    assert split_after_settlement["transfers"] == split_rechecked["transfers"]


def test_split_and_settlement_flow_for_private_product_owned_by_two_members(
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
        name="private_cost_product_flow",
        category="HARD_CHEESE",
        quantity=1,
        price="8.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=member1["user"]["id"],
        owner_user_ids=[member1["user"]["id"], member2["user"]["id"]],
    )

    initial_split = get_split(client, headers)
    initial_members = members_by_user_id(initial_split)

    assert initial_members[owner["user"]["id"]]["balance"] == "0.00"
    assert initial_members[member1["user"]["id"]]["balance"] == "4.00"
    assert initial_members[member2["user"]["id"]]["balance"] == "-4.00"

    assert transfers_as_tuples(initial_split) == {
        (member2["user"]["id"], member1["user"]["id"], "4.00"),
    }

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member2["user"]["id"],
        to_user_id=member1["user"]["id"],
        amount="4.00",
    )

    final_split = settlement_body["split"]
    final_members = members_by_user_id(final_split)

    assert final_members[owner["user"]["id"]]["balance"] == "0.00"
    assert final_members[member1["user"]["id"]]["balance"] == "0.00"
    assert final_members[member2["user"]["id"]]["balance"] == "0.00"

    assert transfers_as_tuples(final_split) == set()


def test_split_flow_rounding_is_preserved_after_settlement(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    # 10 / 3 => decimal periódico
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="periodic_decimal_cost_product_flow",
        category="RICE",
        quantity=1,
        price="10.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    initial_split = get_split(client, headers)
    initial_members = members_by_user_id(initial_split)

    assert initial_members[owner["user"]["id"]]["balance"] == "6.67"
    assert initial_members[member1["user"]["id"]]["balance"] == "-3.33"
    assert initial_members[member2["user"]["id"]]["balance"] == "-3.33"

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.33",
    )

    updated_split = settlement_body["split"]
    updated_members = members_by_user_id(updated_split)

    assert updated_members[member1["user"]["id"]]["balance"] == "0.00"
    assert updated_members[member2["user"]["id"]]["balance"] == "-3.33"
    assert updated_members[owner["user"]["id"]]["balance"] == "3.34"

    assert transfers_as_tuples(updated_split) == {
        (member2["user"]["id"], owner["user"]["id"], "3.33"),
    }


def test_split_settlement_flow_changes_after_adding_new_product(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    # Producto inicial: 9.00 público pagado por owner
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="initial_public_cost_product",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    initial_split = get_split(client, headers)
    initial_members = members_by_user_id(initial_split)

    assert initial_members[owner["user"]["id"]]["balance"] == "6.00"
    assert initial_members[member1["user"]["id"]]["balance"] == "-3.00"
    assert initial_members[member2["user"]["id"]]["balance"] == "-3.00"

    # member1 salda su deuda inicial
    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.00",
    )

    settled_split = settlement_body["split"]
    settled_members = members_by_user_id(settled_split)

    assert settled_members[member1["user"]["id"]]["balance"] == "0.00"
    assert settled_members[member2["user"]["id"]]["balance"] == "-3.00"
    assert settled_members[owner["user"]["id"]]["balance"] == "3.00"

    # Se añade un nuevo producto público pagado por member2
    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member2,
        name="new_public_cost_product",
        category="MILK",
        quantity=1,
        price="6.00",
        purchase_date=date(2026, 1, 11),
        paid_by_user_id=member2["user"]["id"],
        owner_user_ids=[],
    )

    updated_split = get_split(client, headers)
    updated_members = members_by_user_id(updated_split)

    # Total acumulado: 15.00
    assert updated_split["total"] == "15.00"

    # should_pay = 5.00 cada uno
    assert updated_members[owner["user"]["id"]]["should_pay"] == "5.00"
    assert updated_members[member1["user"]["id"]]["should_pay"] == "5.00"
    assert updated_members[member2["user"]["id"]]["should_pay"] == "5.00"

    # paid acumulado
    assert updated_members[owner["user"]["id"]]["paid"] == "9.00"
    assert updated_members[member1["user"]["id"]]["paid"] == "0.00"
    assert updated_members[member2["user"]["id"]]["paid"] == "6.00"

    # settlements previos deben seguir contando
    assert updated_members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert updated_members[owner["user"]["id"]]["settled_received"] == "3.00"

    # balance actualizado
    assert updated_members[owner["user"]["id"]]["balance"] == "1.00"
    assert updated_members[member1["user"]["id"]]["balance"] == "-2.00"
    assert updated_members[member2["user"]["id"]]["balance"] == "1.00"


# balance = paid - should_pay - settled_received + settled_paid


def test_split_settlement_flow_changes_after_increasing_product_price(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seeded = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="more_expensive_cost_product",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    initial_split = get_split(client, headers)
    initial_members = members_by_user_id(initial_split)

    assert initial_split["total"] == "9.00"
    assert initial_members[owner["user"]["id"]]["balance"] == "6.00"
    assert initial_members[member1["user"]["id"]]["balance"] == "-3.00"
    assert initial_members[member2["user"]["id"]]["balance"] == "-3.00"

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.00",
    )

    split_after_settlement = settlement_body["split"]
    members_after_settlement = members_by_user_id(split_after_settlement)

    assert members_after_settlement[member1["user"]["id"]]["balance"] == "0.00"
    assert members_after_settlement[owner["user"]["id"]]["balance"] == "3.00"
    assert members_after_settlement[member2["user"]["id"]]["balance"] == "-3.00"

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
        row.preu = "12.00"
        db.commit()
    finally:
        db.close()

    updated_split = get_split(client, headers)
    updated_members = members_by_user_id(updated_split)

    assert updated_split["total"] == "12.00"

    assert updated_members[owner["user"]["id"]]["should_pay"] == "4.00"
    assert updated_members[member1["user"]["id"]]["should_pay"] == "4.00"
    assert updated_members[member2["user"]["id"]]["should_pay"] == "4.00"

    assert updated_members[owner["user"]["id"]]["paid"] == "12.00"
    assert updated_members[member1["user"]["id"]]["paid"] == "0.00"
    assert updated_members[member2["user"]["id"]]["paid"] == "0.00"

    assert updated_members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert updated_members[owner["user"]["id"]]["settled_received"] == "3.00"

    # El settlement previo se mantiene; solo aumenta la deuda restante
    assert updated_members[owner["user"]["id"]]["balance"] == "5.00"
    assert updated_members[member1["user"]["id"]]["balance"] == "-1.00"
    assert updated_members[member2["user"]["id"]]["balance"] == "-4.00"

    assert transfers_as_tuples(updated_split) == {
        (member1["user"]["id"], owner["user"]["id"], "1.00"),
        (member2["user"]["id"], owner["user"]["id"], "4.00"),
    }


def test_split_settlement_flow_changes_after_making_product_cheaper(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    seeded = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="cheaper_price_cost_product",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    initial_split = get_split(client, headers)
    initial_members = members_by_user_id(initial_split)

    assert initial_split["total"] == "9.00"
    assert initial_members[owner["user"]["id"]]["balance"] == "6.00"
    assert initial_members[member1["user"]["id"]]["balance"] == "-3.00"
    assert initial_members[member2["user"]["id"]]["balance"] == "-3.00"

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="3.00",
    )

    split_after_settlement = settlement_body["split"]
    members_after_settlement = members_by_user_id(split_after_settlement)

    assert members_after_settlement[member1["user"]["id"]]["balance"] == "0.00"
    assert members_after_settlement[owner["user"]["id"]]["balance"] == "3.00"
    assert members_after_settlement[member2["user"]["id"]]["balance"] == "-3.00"

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
        row.preu = "6.00"
        db.commit()
    finally:
        db.close()

    updated_split = get_split(client, headers)
    updated_members = members_by_user_id(updated_split)

    assert updated_split["total"] == "6.00"

    assert updated_members[owner["user"]["id"]]["should_pay"] == "2.00"
    assert updated_members[member1["user"]["id"]]["should_pay"] == "2.00"
    assert updated_members[member2["user"]["id"]]["should_pay"] == "2.00"

    assert updated_members[owner["user"]["id"]]["paid"] == "6.00"
    assert updated_members[member1["user"]["id"]]["paid"] == "0.00"
    assert updated_members[member2["user"]["id"]]["paid"] == "0.00"

    assert updated_members[member1["user"]["id"]]["settled_paid"] == "3.00"
    assert updated_members[owner["user"]["id"]]["settled_received"] == "3.00"

    # Como el producto ahora cuesta menos, owner cobró 1.00 de más a member1
    assert updated_members[owner["user"]["id"]]["balance"] == "-1.00"
    assert updated_members[member1["user"]["id"]]["balance"] == "1.00"
    assert updated_members[member2["user"]["id"]]["balance"] == "-2.00"

    assert transfers_as_tuples(updated_split) == {
        (owner["user"]["id"], member1["user"]["id"], "1.00"),
        (member2["user"]["id"], owner["user"]["id"], "2.00"),
    }


def test_split_settlement_flow_changes_after_deleting_product(
    client,
    shared_home_setup,
    seed_product_db,
):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    deletable = seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner,
        name="deletable_public_cost_product",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    initial_split = get_split(client, headers)
    initial_members = members_by_user_id(initial_split)

    assert initial_members[owner["user"]["id"]]["balance"] == "6.00"
    assert initial_members[member1["user"]["id"]]["balance"] == "-3.00"
    assert initial_members[member2["user"]["id"]]["balance"] == "-3.00"

    settlement_body = create_settlement(
        client,
        headers,
        from_user_id=member1["user"]["id"],
        to_user_id=owner["user"]["id"],
        amount="1.50",
    )

    split_after_settlement = settlement_body["split"]
    members_after_settlement = members_by_user_id(split_after_settlement)

    assert members_after_settlement[member1["user"]["id"]]["balance"] == "-1.50"
    assert members_after_settlement[owner["user"]["id"]]["balance"] == "4.50"
    assert members_after_settlement[member2["user"]["id"]]["balance"] == "-3.00"

    delete_response = client.request(
        "DELETE",
        "/inventory_delete_product",
        json={"id_producte": str(deletable["id"])},
        headers=headers,
    )
    assert delete_response.status_code == 200, delete_response.text

    updated_split = get_split(client, headers)
    updated_members = members_by_user_id(updated_split)

    assert updated_split["total"] == "0.00"

    assert updated_members[owner["user"]["id"]]["paid"] == "0.00"
    assert updated_members[member1["user"]["id"]]["paid"] == "0.00"
    assert updated_members[member2["user"]["id"]]["paid"] == "0.00"

    assert updated_members[owner["user"]["id"]]["should_pay"] == "0.00"
    assert updated_members[member1["user"]["id"]]["should_pay"] == "0.00"
    assert updated_members[member2["user"]["id"]]["should_pay"] == "0.00"

    assert updated_members[member1["user"]["id"]]["settled_paid"] == "1.50"
    assert updated_members[owner["user"]["id"]]["settled_received"] == "1.50"

    # Como el producto desaparece, owner ahora debe devolver lo que ya cobró
    assert updated_members[owner["user"]["id"]]["balance"] == "-1.50"
    assert updated_members[member1["user"]["id"]]["balance"] == "1.50"
    assert updated_members[member2["user"]["id"]]["balance"] == "0.00"

    assert transfers_as_tuples(updated_split) == {
        (owner["user"]["id"], member1["user"]["id"], "1.50"),
    }


def test_cost_split_minimizes_number_of_transfers_when_each_user_paid_one_product(
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
        name="owner_paid_product",
        category="RICE",
        quantity=1,
        price="9.00",
        purchase_date=date(2026, 1, 10),
        paid_by_user_id=owner["user"]["id"],
        owner_user_ids=[],
    )

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member1,
        name="member1_paid_product",
        category="MILK",
        quantity=1,
        price="6.00",
        purchase_date=date(2026, 1, 11),
        paid_by_user_id=member1["user"]["id"],
        owner_user_ids=[],
    )

    seed_cost_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member2,
        name="member2_paid_product",
        category="EGGS",
        quantity=1,
        price="3.00",
        purchase_date=date(2026, 1, 12),
        paid_by_user_id=member2["user"]["id"],
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
    assert body["total"] == "18.00"

    members = members_by_user_id(body)

    assert members[owner["user"]["id"]]["paid"] == "9.00"
    assert members[owner["user"]["id"]]["should_pay"] == "6.00"
    assert members[owner["user"]["id"]]["balance"] == "3.00"

    assert members[member1["user"]["id"]]["paid"] == "6.00"
    assert members[member1["user"]["id"]]["should_pay"] == "6.00"
    assert members[member1["user"]["id"]]["balance"] == "0.00"

    assert members[member2["user"]["id"]]["paid"] == "3.00"
    assert members[member2["user"]["id"]]["should_pay"] == "6.00"
    assert members[member2["user"]["id"]]["balance"] == "-3.00"

    # La minimización correcta deja una sola transferencia
    assert transfers_as_tuples(body) == {
        (member2["user"]["id"], owner["user"]["id"], "3.00"),
    }
    assert len(body["transfers"]) == 1
