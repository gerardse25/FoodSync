import pytest

INVENTORY_ENDPOINT = "/inventory/"


def test_owner_can_view_inventory(client, shared_home_with_products):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(INVENTORY_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    assert len(body["productes"]) > 0


def test_member_can_view_inventory(client, shared_home_with_products):
    headers = shared_home_with_products["member1_headers"]

    response = client.get(INVENTORY_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    assert len(body["productes"]) > 0


def test_can_view_inventory_with_existing_products(client, shared_home_with_products):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(INVENTORY_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    assert len(body["productes"]) > 0

    product_names = {product["nom"] for product in body["productes"]}

    assert shared_home_with_products["products"]["owner_private"]["payload"]["name"] in product_names
    assert shared_home_with_products["products"]["member1_private"]["payload"]["name"] in product_names
    assert shared_home_with_products["products"]["public_product"]["payload"]["name"] in product_names


def test_member_can_view_all_home_products_including_products_owned_by_other_users(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member1_headers"]

    owner_private_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    member_private_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]
    public_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    response = client.get(INVENTORY_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"

    product_names = {product["nom"] for product in body["productes"]}

    assert owner_private_name in product_names
    assert member_private_name in product_names
    assert public_name in product_names


def test_can_view_empty_inventory(client, shared_home_setup):
    headers = shared_home_setup["owner_headers"]

    response = client.get(INVENTORY_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    assert body["productes"] == []


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_view_inventory(client, headers):
    response = client.get(INVENTORY_ENDPOINT, headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_non_member_cannot_view_inventory(client, outsider_user):
    response = client.get(INVENTORY_ENDPOINT, headers=outsider_user["headers"])

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


def test_inventory_response_includes_expected_basic_product_information(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member1_headers"]

    response = client.get(INVENTORY_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    assert len(body["productes"]) > 0

    for product in body["productes"]:
        assert "id_producte" in product
        assert "nom" in product
        assert product["nom"] not in (None, "")

        assert "quantitat" in product
        assert isinstance(product["quantitat"], int)
        assert product["quantitat"] >= 0

        assert "categoria" in product
        assert isinstance(product["categoria"], str)

        assert "data_caducitat" in product

        assert "es_privat" in product
        assert isinstance(product["es_privat"], bool)

        assert "propietari" in product