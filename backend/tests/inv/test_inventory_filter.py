###TODO: in future add caducity filter
###TODO: in future add nutritional scoring filter

import pytest

INVENTORY_ENDPOINT = "/inventory/"
INVENTORY_PRODUCTS_ENDPOINT = "/inventory/products"
OWNER_FILTER_PARAM = "owner_user_id"


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



def get_product_names(body):
    return {product["nom"] for product in body["productes"]}


def get_product_quantities(body):
    return [product["quantitat"] for product in body["productes"]]


def assert_backend_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code


def test_filter_by_min_quantity_returns_only_products_with_quantity_greater_or_equal(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?min_quantity=2",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert len(body["productes"]) > 0
    assert all(product["quantitat"] >= 2 for product in body["productes"])


def test_filter_by_max_quantity_returns_only_products_with_quantity_lower_or_equal(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?max_quantity=2",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert len(body["productes"]) > 0
    assert all(product["quantitat"] <= 2 for product in body["productes"])


def test_filter_by_quantity_range_returns_only_products_inside_range(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?min_quantity=1&max_quantity=2",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert len(body["productes"]) > 0
    assert all(1 <= product["quantitat"] <= 2 for product in body["productes"])


def test_filter_by_quantity_range_with_no_matches_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?min_quantity=999&max_quantity=1000",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert body["productes"] == []


@pytest.mark.parametrize("min_quantity", ["abc", "1.5", "-1"])
def test_filter_rejects_invalid_min_quantity(
    client,
    shared_home_with_products,
    min_quantity,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?min_quantity={min_quantity}",
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    if "code" in body:
        assert body["code"] == "MIN_QUANTITY_INVALID"


@pytest.mark.parametrize("max_quantity", ["abc", "1.5", "-1"])
def test_filter_rejects_invalid_max_quantity(
    client,
    shared_home_with_products,
    max_quantity,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?max_quantity={max_quantity}",
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    if "code" in body:
        assert body["code"] == "MAX_QUANTITY_INVALID"


def test_filter_rejects_invalid_quantity_range_when_min_is_greater_than_max(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?min_quantity=5&max_quantity=2",
        headers=headers,
    )

    assert_backend_error(response, 400, "QUANTITY_RANGE_INVALID")


def test_filter_by_owner_user_returns_only_products_of_that_owner(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    owner_private_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"

    product_names = get_product_names(body)
    assert owner_private_name in product_names


def test_filter_by_other_member_owner_returns_products_of_that_member(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    member1_id = shared_home_with_products["member1"]["user"]["id"]
    member1_private_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?{OWNER_FILTER_PARAM}={member1_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"

    product_names = get_product_names(body)
    assert member1_private_name in product_names


def test_filter_by_owner_user_with_no_matching_products_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    member2_id = shared_home_with_products["member2"]["user"]["id"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?{OWNER_FILTER_PARAM}={member2_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    # Ajusta este test si en tu fixture member2 sí llega a tener productos
    assert body["productes"] == []


def test_filter_rejects_owner_user_not_in_home(
    client,
    shared_home_with_products,
    outsider_user,
):
    headers = shared_home_with_products["owner_headers"]
    outsider_id = outsider_user["user"]["id"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?{OWNER_FILTER_PARAM}={outsider_id}",
        headers=headers,
    )
    assert_backend_error(response, 400, "OWNER_NOT_IN_HOME")


def test_filter_rejects_invalid_owner_user_id_format(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?{OWNER_FILTER_PARAM}=abc",
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text
    body = response.json()
    if "code" in body:
        assert body["code"] == "OWNER_FILTER_INVALID"


def test_filter_by_owner_and_quantity_can_be_combined(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?{OWNER_FILTER_PARAM}={owner_id}&min_quantity=1&max_quantity=5",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert all(1 <= product["quantitat"] <= 5 for product in body["productes"])


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_filter_inventory_products_by_quantity_or_owner(
    client,
    headers,
):
    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?min_quantity=1&max_quantity=5",
        headers=headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_user_without_home_cannot_filter_inventory_products_by_quantity_or_owner(
    client,
    outsider_user,
):
    response = client.get(
        f"{INVENTORY_PRODUCTS_ENDPOINT}?min_quantity=1&max_quantity=5",
        headers=outsider_user["headers"],
    )

    assert response.status_code in (403, 404), response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"