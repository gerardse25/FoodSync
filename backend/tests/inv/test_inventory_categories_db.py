import pytest

DB_CATEGORIES_ENDPOINT = "/inventory/categories"


def get_category_names(body):
    return [category["nom"] for category in body["categories"]]


def test_get_home_categories_returns_success_and_expected_shape(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(DB_CATEGORIES_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"
    assert body["missatge"] == "Categories de la llar obtingudes correctament"
    assert "categories" in body
    assert isinstance(body["categories"], list)

    for category in body["categories"]:
        assert "id" in category
        assert "nom" in category
        assert isinstance(category["id"], int)
        assert isinstance(category["nom"], str)
        assert category["nom"] != ""


def test_get_home_categories_returns_only_categories_used_in_user_home(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(DB_CATEGORIES_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    names = set(get_category_names(body))

    assert len(names) > 0
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"


def test_get_home_categories_does_not_return_unused_categories_from_system(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(DB_CATEGORIES_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    names = set(get_category_names(body))

    assert len(names) < 100
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"


def test_get_home_categories_returns_empty_list_when_home_has_no_products(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(DB_CATEGORIES_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"
    assert body["missatge"] == "Categories de la llar obtingudes correctament"
    assert body["categories"] == []


def test_get_home_categories_are_sorted_alphabetically(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(DB_CATEGORIES_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_category_names(body)

    assert names == sorted(names)
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"


def test_get_home_categories_contains_no_duplicates(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(DB_CATEGORIES_ENDPOINT, headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_category_names(body)

    assert len(names) == len(set(names))
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"


def test_member_gets_same_home_categories_as_owner(
    client,
    shared_home_with_products,
):
    owner_response = client.get(
        DB_CATEGORIES_ENDPOINT,
        headers=shared_home_with_products["owner_headers"],
    )
    member_response = client.get(
        DB_CATEGORIES_ENDPOINT,
        headers=shared_home_with_products["member1_headers"],
    )

    assert owner_response.status_code == 200, owner_response.text
    assert member_response.status_code == 200, member_response.text

    owner_body = owner_response.json()
    member_body = member_response.json()

    assert owner_body["code"] == "HOME_CATEGORIES_RETRIEVED"
    assert member_body["code"] == "HOME_CATEGORIES_RETRIEVED"

    assert get_category_names(owner_body) == get_category_names(member_body)


def test_different_homes_should_not_necessarily_receive_same_categories(
    client,
    shared_home_with_products,
    private_home_setup,
):
    shared_response = client.get(
        DB_CATEGORIES_ENDPOINT,
        headers=shared_home_with_products["owner_headers"],
    )
    private_response = client.get(
        DB_CATEGORIES_ENDPOINT,
        headers=private_home_setup["headers"],
    )

    assert shared_response.status_code == 200, shared_response.text
    assert private_response.status_code == 200, private_response.text

    shared_body = shared_response.json()
    private_body = private_response.json()

    assert shared_body["code"] == "HOME_CATEGORIES_RETRIEVED"
    assert private_body["code"] == "HOME_CATEGORIES_RETRIEVED"

    assert private_body["categories"] == []
    assert len(shared_body["categories"]) > 0


def test_home_categories_can_be_filtered_by_search_text(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{DB_CATEGORIES_ENDPOINT}?q=arr", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"

    names = get_category_names(body)
    assert all("arr" in name.lower() for name in names)


def test_home_categories_search_is_case_insensitive(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response_lower = client.get(f"{DB_CATEGORIES_ENDPOINT}?q=arr", headers=headers)
    response_upper = client.get(f"{DB_CATEGORIES_ENDPOINT}?q=ARR", headers=headers)

    assert response_lower.status_code == 200, response_lower.text
    assert response_upper.status_code == 200, response_upper.text

    body_lower = response_lower.json()
    body_upper = response_upper.json()

    assert body_lower["code"] == "HOME_CATEGORIES_RETRIEVED"
    assert body_upper["code"] == "HOME_CATEGORIES_RETRIEVED"
    assert get_category_names(body_lower) == get_category_names(body_upper)


def test_home_categories_search_with_no_results_returns_empty_list(
    client,
    shared_home_with_products,
):
    headers = shared_home_with_products["owner_headers"]

    response = client.get(f"{DB_CATEGORIES_ENDPOINT}?q=this-category-does-not-exist", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "HOME_CATEGORIES_RETRIEVED"
    assert body["categories"] == []


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_cannot_get_home_categories(client, headers):
    response = client.get(DB_CATEGORIES_ENDPOINT, headers=headers)

    assert response.status_code in (401, 403), response.text
    body = response.json()
    assert body["code"] == "AUTH_REQUIRED"


def test_user_without_home_cannot_get_home_categories(
    client,
    outsider_user,
):
    response = client.get(DB_CATEGORIES_ENDPOINT, headers=outsider_user["headers"])

    assert response.status_code in (403, 404), response.text
    body = response.json()
    assert body["code"] == "NOT_IN_HOME"