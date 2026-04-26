import pytest

INVENTORY_ENDPOINT = "/inventory/"
OWNER_FILTER_PARAM = "owner_user_id"


def get_response_products(body):
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    return body["productes"]


def get_response_names(body):
    return {product["nom"] for product in get_response_products(body)}


def get_db_product_by_key(shared_home_with_products, key):
    return shared_home_with_products["products"][key]["db"]


def get_db_category(shared_home_with_products, key):
    return get_db_product_by_key(shared_home_with_products, key)["category"]


def get_db_quantity(shared_home_with_products, key):
    return get_db_product_by_key(shared_home_with_products, key)["quantity"]


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


def test_inventory_search_and_filter_returns_correct_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = get_db_category(shared_home_with_products, "owner_private")

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


def test_inventory_filter_by_category_and_partial_name_search_returns_partial_matches(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    search_term = "product"
    target_category = get_db_category(shared_home_with_products, "owner_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={search_term}&categoria={target_category}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_names_contain(products, search_term)
    assert_all_categories_equal(products, target_category)


def test_inventory_search_with_no_results_and_filter_existing_category_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_category = get_db_category(shared_home_with_products, "owner_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=this-product-does-not-exist&categoria={target_category}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_inventory_search_existing_name_and_filter_non_existing_category_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria=Categoria que no existeix",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_inventory_search_and_filter_data_do_not_match_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    wrong_category = get_db_category(shared_home_with_products, "public_product")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria={wrong_category}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_inventory_search_and_filter_on_empty_inventory_returns_empty_list(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&categoria=Arròs",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_can_view_private_products_of_another_user_using_search_and_filter(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member2_headers"]
    private_product_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    private_product_category = get_db_category(shared_home_with_products, "owner_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={private_product_name}&categoria={private_product_category}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)
    products = get_response_products(body)

    assert private_product_name in names
    assert_all_categories_equal(products, private_product_category)


def test_inventory_search_and_min_quantity_returns_expected_products(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    search_term = "product"

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={search_term}&min_quantity=3",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_names_contain(products, search_term)
    assert_all_quantities_gte(products, 3)


def test_inventory_search_and_max_quantity_returns_expected_products(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    search_term = "product"

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={search_term}&max_quantity=3",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_names_contain(products, search_term)
    assert_all_quantities_lte(products, 3)


def test_inventory_category_and_quantity_range_returns_expected_products(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_category = get_db_category(shared_home_with_products, "member1_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria={target_category}&min_quantity=5&max_quantity=5",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_categories_equal(products, target_category)
    assert_all_quantities_between(products, 5, 5)


def test_inventory_owner_and_name_returns_expected_private_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={target_name}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert names == {target_name}


def test_inventory_owner_and_category_returns_expected_private_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = get_db_category(shared_home_with_products, "owner_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria={target_category}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)
    products = get_response_products(body)

    assert target_name in names
    assert_all_categories_equal(products, target_category)


def test_inventory_owner_and_quantity_range_returns_expected_private_product(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    quantity = get_db_quantity(shared_home_with_products, "owner_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?min_quantity={quantity}&max_quantity={quantity}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)
    products = get_response_products(body)

    assert target_name in names
    assert_all_quantities_between(products, quantity, quantity)


def test_inventory_name_category_and_owner_returns_exact_match(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = get_db_category(shared_home_with_products, "owner_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom={target_name}&categoria={target_category}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert names == {target_name}


def test_inventory_name_category_quantity_and_owner_returns_exact_match(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    target_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]
    target_category = get_db_category(shared_home_with_products, "owner_private")
    quantity = get_db_quantity(shared_home_with_products, "owner_private")

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


def test_inventory_name_and_owner_with_no_match_returns_empty_list(
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


def test_inventory_category_and_owner_with_no_match_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    owner_id = shared_home_with_products["owner"]["user"]["id"]
    member1_private_category = get_db_category(shared_home_with_products, "member1_private")

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria={member1_private_category}&{OWNER_FILTER_PARAM}={owner_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_search_and_filter_inventory(client, headers):
    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&categoria=Arròs&min_quantity=1&max_quantity=5",
        headers=headers,
    )

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_unauthorized_user_cannot_search_and_filter_inventory(client, outsider_user):
    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&categoria=Arròs&min_quantity=1&max_quantity=5",
        headers=outsider_user["headers"],
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"