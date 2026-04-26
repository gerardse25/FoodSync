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


def test_inventory_filter_by_exact_category_returns_correct_products(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]
    target_category = get_db_category(shared_home_with_products, "owner_private")

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria={target_category}", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) > 0
    assert_all_categories_equal(products, target_category)


def test_inventory_filter_with_no_category_results_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria=this-category-does-not-exist",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_inventory_category_filter_on_empty_inventory_returns_empty_list(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(f"{INVENTORY_ENDPOINT}?categoria=Arròs", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_can_view_private_products_of_another_user_using_category_filter(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["member2_headers"]
    private_product_category = get_db_category(shared_home_with_products, "owner_private")
    private_product_name = shared_home_with_products["products"]["owner_private"]["payload"]["name"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria={private_product_category}",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert len(products) > 0
    assert private_product_name in names
    assert_all_categories_equal(products, private_product_category)


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

    response = client.get(
        f"{INVENTORY_ENDPOINT}?min_quantity=999&max_quantity=1000",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_filter_rejects_invalid_quantity_range(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?min_quantity=10&max_quantity=2",
        headers=headers,
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "QUANTITY_RANGE_INVALID"


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
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "INVALID_USER_ID"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_filter_inventory(client, headers):
    response = client.get(f"{INVENTORY_ENDPOINT}?categoria=Arròs", headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_unauthorized_user_cannot_filter_inventory(client, outsider_user):
    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria=Arròs",
        headers=outsider_user["headers"],
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"