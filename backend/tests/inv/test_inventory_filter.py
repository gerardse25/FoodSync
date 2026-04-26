###TODO: in future add caducity filter
###TODO: in future add nutritional scoring filter

import pytest

INVENTORY_ENDPOINT = "/inventory/"
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


##TEST QUANTITY & OWNER


def get_product_by_name(products, target_name):
    return next((product for product in products if product["name"] == target_name), None)


def get_response_products(body):
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    return body["productes"]


def get_response_names(body):
    return {product["nom"] for product in get_response_products(body)}


def assert_all_quantities_gte(products, minimum):
    for product in products:
        assert product["quantitat"] >= minimum


def assert_all_quantities_lte(products, maximum):
    for product in products:
        assert product["quantitat"] <= maximum


def assert_all_quantities_between(products, minimum, maximum):
    for product in products:
        assert minimum <= product["quantitat"] <= maximum


def assert_all_categories_equal(products, category):
    for product in products:
        assert product["categoria"] == category


def assert_all_names_contain(products, search_term):
    for product in products:
        assert search_term.lower() in product["nom"].lower()


def test_filter_by_min_quantity_returns_only_products_with_quantity_greater_or_equal(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?min_quantity=3", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_quantities_gte(products, 3)


def test_filter_by_max_quantity_returns_only_products_with_quantity_lower_or_equal(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?max_quantity=3", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_quantities_lte(products, 3)


def test_filter_by_quantity_range_returns_only_products_inside_range(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?min_quantity=2&max_quantity=5", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_quantities_between(products, 2, 5)


def test_filter_by_quantity_range_with_no_matches_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?min_quantity=999&max_quantity=1000", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_filter_by_owner_user_returns_only_products_of_that_owner(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    owner_private_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    member1_private_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]
    public_product_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert owner_private_name in names
    assert member1_private_name not in names
    assert public_product_name not in names


def test_filter_by_other_member_owner_returns_products_of_that_member(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    member1_id = shared_home_with_products["member1"]["user"]["id"]

    owner_private_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    member1_private_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]
    public_product_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={member1_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert member1_private_name in names
    assert owner_private_name not in names
    assert public_product_name not in names


def test_filter_by_owner_user_with_no_matching_products_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    member2_id = shared_home_with_products["member2"]["user"]["id"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={member2_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_filter_rejects_owner_user_not_in_home(
    client,
    shared_home_with_products,
    outsider_user,
):
    headers = shared_home_with_products["owner_headers"]
    outsider_id = outsider_user["user"]["id"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={outsider_id}",
        headers=headers,
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "OWNER_NOT_IN_HOME"


def test_filter_rejects_invalid_owner_user_id_format(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}=abc",
        headers=headers,
    )
    assert response.status_code in (400, 422), response.text

    body = response.json()
    assert body["code"] in ("OWNER_FILTER_INVALID", "INVALID_USER_ID")


def test_filter_by_name_and_category_returns_expected_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria={target_category}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert target_name in names
    assert_all_categories_equal(products, target_category)


def test_filter_by_name_and_min_quantity_returns_expected_product(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]
    db_products = list_home_products_db(home_id)
    target_product = get_product_by_name(db_products, target_name)
    assert target_product is not None

    min_quantity = target_product["quantity"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={target_name}&min_quantity={min_quantity}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert target_name in names
    assert_all_names_contain(products, target_name)
    assert_all_quantities_gte(products, min_quantity)


def test_filter_by_category_and_max_quantity_returns_expected_product(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    target_name = shared_home_with_products["products"]["public_product"]["payload"]["name"]
    target_category = shared_home_with_products["products"]["public_product"]["payload"]["category"]

    db_products = list_home_products_db(home_id)
    target_product = get_product_by_name(db_products, target_name)
    assert target_product is not None

    max_quantity = target_product["quantity"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria={target_category}&max_quantity={max_quantity}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert target_name in names
    assert_all_categories_equal(products, target_category)
    assert_all_quantities_lte(products, max_quantity)


def test_filter_by_owner_and_name_returns_expected_private_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    owner_private_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={owner_id}&nom={owner_private_name}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert names == {owner_private_name}


def test_filter_by_owner_and_category_returns_expected_private_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    owner_private_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    owner_private_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={owner_id}&categoria={owner_private_category}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert owner_private_name in names
    assert_all_categories_equal(products, owner_private_category)


def test_filter_by_owner_and_quantity_range_returns_expected_private_product(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    owner_private_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    db_products = list_home_products_db(home_id)
    target_product = get_product_by_name(db_products, owner_private_name)
    assert target_product is not None

    quantity = target_product["quantity"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={owner_id}&min_quantity={quantity}&max_quantity={quantity}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert owner_private_name in names
    assert_all_quantities_between(products, quantity, quantity)


def test_filter_by_name_category_and_owner_returns_exact_match(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria={target_category}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert names == {target_name}


def test_filter_by_name_category_quantity_and_owner_returns_exact_match(
    client,
    shared_home_with_products,
    list_home_products_db,
):
    headers = shared_home_with_products["owner_headers"]
    home_id = shared_home_with_products["home_id"]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = shared_home_with_products["products"]["owner_private"]["payload"]["category"]

    db_products = list_home_products_db(home_id)
    target_product = get_product_by_name(db_products, target_name)
    assert target_product is not None

    quantity = target_product["quantity"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}"
        f"?nom={target_name}"
        f"&categoria={target_category}"
        f"&min_quantity={quantity}"
        f"&max_quantity={quantity}"
        f"&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)
    products = get_response_products(body)

    assert names == {target_name}
    assert_all_categories_equal(products, target_category)
    assert_all_quantities_between(products, quantity, quantity)


def test_filter_by_name_and_owner_with_no_match_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    member1_private_name = shared_home_with_products["products"]["member1_private"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={member1_private_name}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_filter_by_category_and_owner_with_no_match_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    owner_id = shared_home_with_products["owner"]["user"]["id"]
    member1_private_category = shared_home_with_products["products"]["member1_private"]["payload"]["category"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria={member1_private_category}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_filter_by_owner_and_quantity_can_be_combined(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?{OWNER_FILTER_PARAM}={owner_id}&min_quantity=1&max_quantity=99",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_quantities_between(products, 1, 99)


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_use_combined_filters(
    client,
    headers,
):
    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&categoria=RICE&min_quantity=1&max_quantity=5",
        headers=headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_non_member_cannot_use_combined_filters(
    client,
    outsider_user,
):
    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&categoria=RICE&min_quantity=1&max_quantity=5",
        headers=outsider_user["headers"],
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"