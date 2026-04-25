###TODO: in future add caducity filter
###TODO: in future add nutritional scoring filter

import pytest

INVENTORY_ENDPOINT = "/inventory/"


def test_inventory_filter_by_exact_category_returns_correct_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria={target_category}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert {product["categoria"] for product in body["productes"]} == {target_category}


def test_inventory_filter_by_partial_category_returns_partial_matches(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    search_term = "HARD" #from HARD_CHEESE

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria={search_term}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert len(body["productes"]) > 0

    for product in body["productes"]:
        assert search_term.lower() in product["categoria"].lower()


def test_inventory_filter_with_no_category_results_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria=this-category-does-not-exist", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


def test_inventory_category_filter_is_case_insensitive(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member1_headers"]
    #target_category = shared_home_with_products["products"]["public_product"]["payload"]["category"]
    target_category = "sAUcES" #SAUCES

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria={target_category.upper()}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert {product["categoria"] for product in body["productes"]} == {target_category}



def test_inventory_category_filter_trims_leading_and_trailing_spaces(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member1_headers"]
    target_category = shared_home_with_products["products"]["public_product"]["payload"]["category"]

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria=  {target_category}  ", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert {product["categoria"] for product in body["productes"]} == {target_category}



def test_inventory_category_filter_on_empty_inventory_returns_empty_list(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria=RICE", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


def test_can_view_private_products_of_another_user_using_category_filter(
    client, 
    shared_home_with_products
):
    headers = shared_home_with_products["member2_headers"]
    private_product_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria={private_product_category}", headers=headers)

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert {product["categoria"] for product in body["productes"]} == {private_product_category}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_filter_inventory(client, headers):
    response = client.get(f"{INVENTORY_ENDPOINT}?categoria=RICE", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_unauthorized_user_cannot_filter_inventory(client, outsider_user):
    response = client.get(f"{INVENTORY_ENDPOINT}?categoria=RICE", headers=outsider_user["headers"])

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"