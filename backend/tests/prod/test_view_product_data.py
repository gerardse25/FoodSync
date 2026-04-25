import pytest

DETAIL_ENDPOINT_PREFIX = "/inventory"


def get_product_detail_request(client, product_id, headers):
    return client.get(f"{DETAIL_ENDPOINT_PREFIX}/{product_id}", headers=headers)


def delete_product_request(client, product_id, headers):
    return client.request(
        "DELETE",
        "/inventory_delete_product",
        json={"id_producte": str(product_id)},
        headers=headers,
    )


def test_can_view_detail_of_public_product(client, shared_home_with_products):
    headers = shared_home_with_products["owner_headers"]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"]["id"]
    target_product_name = shared_home_with_products["products"]["public_product"]["db"]["name"]

    response = get_product_detail_request(client, target_product_id, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_DETAIL_RETRIEVED"
    assert body["missatge"] == "Detall del producte obtingut correctament"

    product = body["producte"]
    assert product["id_producte"] == str(target_product_id)
    assert product["nom"] == target_product_name
    assert product["es_privat"] is False
    assert product["propietaris"] == []
    assert product["estat_stock"] == "En estoc"


def test_can_view_detail_of_private_product_with_single_owner(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_product_id = shared_home_with_products["products"]["owner_private"]["db"]["id"]
    target_product_name = shared_home_with_products["products"]["owner_private"]["db"]["name"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    owner_name = shared_home_with_products["owner"]["user"]["username"]

    response = get_product_detail_request(client, target_product_id, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_DETAIL_RETRIEVED"

    product = body["producte"]
    assert product["id_producte"] == str(target_product_id)
    assert product["nom"] == target_product_name
    assert product["es_privat"] is True
    assert product["estat_stock"] == "En estoc"

    assert len(product["propietaris"]) == 1
    assert product["propietaris"][0]["id_usuari"] == owner_id
    assert product["propietaris"][0]["nom"] == owner_name


def test_can_view_detail_of_product_with_multiple_owners(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    owner_id = shared_home_setup["owner"]["user"]["id"]
    owner_name = shared_home_setup["owner"]["user"]["username"]
    member1_id = shared_home_setup["member1"]["user"]["id"]
    member1_name = shared_home_setup["member1"]["user"]["username"]

    seeded = seed_product_db(
        home_id=home_id,
        created_by_ctx=shared_home_setup["owner"],
        name="multi_owner_detail_product",
        category="MULTI_OWNER_TEST",
        quantity=4,
        price="2.40",
        owner_user_ids=[owner_id, member1_id],
    )

    response = get_product_detail_request(client, seeded["id"], headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_DETAIL_RETRIEVED"

    product = body["producte"]
    assert product["id_producte"] == str(seeded["id"])
    assert product["nom"] == seeded["name"]
    assert product["es_privat"] is True
    assert product["estat_stock"] == "En estoc"

    owner_pairs = {(owner["id_usuari"], owner["nom"]) for owner in product["propietaris"]}
    assert owner_pairs == {
        (owner_id, owner_name),
        (member1_id, member1_name),
    }


def test_detail_response_includes_expected_fields(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member1_headers"]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = get_product_detail_request(client, target_product_id, headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_DETAIL_RETRIEVED"
    assert "producte" in body

    product = body["producte"]

    assert "id_producte" in product
    assert "nom" in product
    assert "marca" in product
    assert "quantitat_stock" in product
    assert "quantitat_envas" in product
    assert "categoria" in product
    assert "data_caducitat" in product
    assert "data_compra" in product
    assert "preu" in product
    assert "es_privat" in product
    assert "propietaris" in product
    assert "estat_stock" in product
    assert "nutriscore" in product
    assert "informacio_nutricional_100g_ml" in product
    assert "ingredients" in product
    assert "allergens" in product
    assert "imatge_url" in product


def test_detail_marks_product_as_out_of_stock_when_quantity_is_zero(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]

    seeded = seed_product_db(
        home_id=home_id,
        created_by_ctx=shared_home_setup["owner"],
        name="out_of_stock_detail_product",
        category="OUT_OF_STOCK_TEST",
        quantity=0,
        price="1.00",
        owner_user_ids=[],
    )

    response = get_product_detail_request(client, seeded["id"], headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_DETAIL_RETRIEVED"
    assert body["producte"]["quantitat_stock"] == 0
    assert body["producte"]["estat_stock"] == "Exhaurit"


def test_non_member_without_home_cannot_view_product_detail(client, outsider_user, shared_home_with_products):
    target_product_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = get_product_detail_request(client, target_product_id, outsider_user["headers"])
    assert response.status_code == 403, response.text

    body = response.json()
    assert body["code"] == "NOT_IN_HOME"


def test_user_from_another_home_cannot_view_foreign_product_detail(
    client,
    shared_home_with_products,
    private_home_setup,
):
    target_product_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = get_product_detail_request(client, target_product_id, private_home_setup["headers"])
    assert response.status_code == 404, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"
    assert body["error"] == "El producte no s'ha trobat."


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_view_product_detail(
    client,
    shared_home_with_products,
    headers,
):
    target_product_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    response = get_product_detail_request(client, target_product_id, headers)
    assert response.status_code in (401, 403), response.text

    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_viewing_non_existing_product_detail_returns_error(client, shared_home_with_products):
    headers = shared_home_with_products["owner_headers"]

    response = get_product_detail_request(client, 999999, headers)
    assert response.status_code == 404, response.text

    body = response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"
    assert body["error"] == "El producte no s'ha trobat."


def test_viewing_product_detail_with_non_numeric_id_returns_validation_error(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{DETAIL_ENDPOINT_PREFIX}/abc", headers=headers)
    assert response.status_code == 422, response.text

    body = response.json()
    assert "detail" in body


def test_deleted_product_detail_returns_not_found(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_product_id = shared_home_with_products["products"]["public_product"]["db"]["id"]

    delete_response = delete_product_request(client, target_product_id, headers)
    assert delete_response.status_code == 200, delete_response.text

    detail_response = get_product_detail_request(client, target_product_id, headers)
    assert detail_response.status_code == 404, detail_response.text

    body = detail_response.json()
    assert body["code"] == "PRODUCT_NOT_FOUND"
    assert body["error"] == "El producte no s'ha trobat."