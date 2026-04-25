import pytest

INVENTORY_ENDPOINT = "/inventory/"


def test_inventory_search_by_exact_name_returns_correct_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={target_name}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    product_names = {product["nom"] for product in body["productes"]}
    assert target_name in product_names


def test_inventory_search_by_partial_name_returns_partial_matches(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    search_term = "product"

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={search_term}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert len(body["productes"]) > 0

    for product in body["productes"]:
        assert search_term.lower() in product["nom"].lower()


def test_inventory_search_with_no_results_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom=this-product-does-not-exist", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


def test_inventory_search_is_case_insensitive(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member1_headers"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={target_name.upper()}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    product_names = {product["nom"] for product in body["productes"]}
    assert target_name in product_names


def test_inventory_search_trims_leading_and_trailing_spaces(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member1_headers"]
    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom=  {target_name}  ", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    product_names = {product["nom"] for product in body["productes"]}

    assert target_name in product_names


def test_inventory_search_on_empty_inventory_returns_empty_list(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom=milk", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


def test_can_view_private_products_of_another_user_using_name_search(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member2_headers"]
    private_product_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={private_product_name}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"

    product_names = {product["nom"] for product in body["productes"]}
    assert private_product_name in product_names


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_search_inventory(client, headers):
    response = client.get(f"{INVENTORY_ENDPOINT}?nom=milk", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_unauthorized_user_cannot_search_inventory(client, outsider_user):
    response = client.get(f"{INVENTORY_ENDPOINT}?nom=milk", headers=outsider_user["headers"])

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"