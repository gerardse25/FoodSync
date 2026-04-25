import pytest
import uuid

INVENTORY_MANUAL_ENTRY_ENDPOINT = "/inventory/manual"


def make_manual_inventory_payload(
    *,
    nom: str,
    preu: str,
    categoria: str,
    quantitat: int,
    owner_user_ids: list[str] | None = None,
    data_caducitat: str | None = None,
    data_compra: str | None = None,
):
    return {
        "nom": nom,
        "preu": preu,
        "categoria": categoria,
        "quantitat": quantitat,
        "owner_user_ids": owner_user_ids or [],
        "data_caducitat": data_caducitat,
        "data_compra": data_compra,
    }


def assert_backend_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "detail" in body or "error" in body


def test_can_add_private_product_assigned_to_specific_member(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    member1_id = shared_home_setup["member1"]["user"]["id"]

    product = make_manual_inventory_payload(
        nom="member1 assigned private product",
        preu="2.40",
        categoria="OTHER",
        quantitat=1,
        owner_user_ids=[member1_id],
    )

    response = client.post(INVENTORY_MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    created_product = next((item for item in products if item["name"] == product["nom"]), None)
    assert created_product is not None
    assert created_product["owner_user_ids"] == [member1_id]
    assert created_product["owner_user_id"] == member1_id
    assert created_product["owner"] == member1_id
    assert created_product["is_private"] is True


def test_can_add_product_without_specific_owner_as_public(
    client,
    shared_home_setup,
    list_home_products_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    product = make_manual_inventory_payload(
        nom="public product without owner",
        preu="1.10",
        categoria="OTHER",
        quantitat=2,
        owner_user_ids=[],
    )

    response = client.post(INVENTORY_MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    products = list_home_products_db(home_id)
    created_product = next((item for item in products if item["name"] == product["nom"]), None)
    assert created_product is not None
    assert created_product["owner_user_ids"] == []
    assert created_product["owner_user_id"] is None
    assert created_product["owner"] is None
    assert created_product["is_private"] is False


def test_cannot_assign_product_to_user_who_is_not_member_of_home(
    client,
    shared_home_setup,
    outsider_user,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="product assigned to outsider",
        preu="2.00",
        categoria="OTHER",
        quantitat=1,
        owner_user_ids=[outsider_user["user"]["id"]],
    )

    response = client.post(INVENTORY_MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 400, "OWNER_NOT_IN_HOME")


def test_cannot_assign_product_to_non_existing_user(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    product = make_manual_inventory_payload(
        nom="product assigned to non existing user",
        preu="2.00",
        categoria="OTHER",
        quantitat=1,
        owner_user_ids=[str(uuid.uuid4())],
    )

    response = client.post(INVENTORY_MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert_backend_error(response, 400, "OWNER_NOT_IN_HOME")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_assign_product_owner(
    client,
    shared_home_setup,
    headers,
):
    member1_id = shared_home_setup["member1"]["user"]["id"]

    product = make_manual_inventory_payload(
        nom="unauthenticated assigned product",
        preu="2.00",
        categoria="OTHER",
        quantitat=1,
        owner_user_ids=[member1_id],
    )

    response = client.post(INVENTORY_MANUAL_ENTRY_ENDPOINT, json=product, headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"