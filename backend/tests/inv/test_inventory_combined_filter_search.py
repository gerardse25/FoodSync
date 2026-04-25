import pytest

INVENTORY_ENDPOINT = "/inventory/"


def test_inventory_search_and_filter_returns_correct_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria={target_category}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    product_names = {product["nom"] for product in body["productes"]}
    assert target_name in product_names
    assert {product["categoria"] for product in body["productes"]} == {target_category}


def test_inventory_filter_by_category_and_partial_name_search_returns_partial_matches(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    search_term = "product"
    target_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={search_term}&categoria={target_category}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert len(body["productes"]) > 0

    for product in body["productes"]:
        assert search_term.lower() in product["nom"].lower()
        assert product["categoria"] == target_category


def test_inventory_search_with_no_results_and_filter_existing_category_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom=this-product-does-not-exist&categoria={target_category}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []

def test_inventory_search_existing_name_and_filter_non_existing_category_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria=this-category-does-not-exist", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


def test_inventory_search_and_filter_data_do_not_match_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = "OTHER"

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria={target_category}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


def test_inventory_search_and_filter_on_empty_inventory_returns_empty_list(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom=milk&categoria=OTHER", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


def test_can_view_private_products_of_another_user_using_search_and_filter(
    client, 
    shared_home_with_products
):
    headers = shared_home_with_products["member2_headers"]
    private_product_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]
    private_product_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(f"{INVENTORY_ENDPOINT}?nom={private_product_name}&categoria={private_product_category}", headers=headers)

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    product_names = {product["nom"] for product in body["productes"]}
    product_categories = {product["categoria"] for product in body["productes"]}
    assert private_product_name in product_names
    assert private_product_category in product_categories


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_search_and_filter_inventory(client, headers):
    response = client.get(f"{INVENTORY_ENDPOINT}?nom=milk&categoria=OTHER", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_unauthorized_user_cannot_search_and_filter_inventory(client, outsider_user):
    response = client.get(f"{INVENTORY_ENDPOINT}?nom=milk&categoria=OTHER", headers=outsider_user["headers"])

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"