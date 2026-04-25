import pytest

DB_CATEGORIES_ENDPOINT = "/inventory/categories"


def get_category_names(body):
    return [category["nom"] for category in body["categories"]]


def test_get_db_categories_returns_success_and_expected_shape(client):
    response = client.get(DB_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["missatge"] == "Categories obtingudes correctament"
    assert "categories" in body
    assert isinstance(body["categories"], list)

    for category in body["categories"]:
        assert "id" in category
        assert "nom" in category
        assert isinstance(category["id"], int)
        assert isinstance(category["nom"], str)
        assert category["nom"] != ""


def test_get_db_categories_returns_empty_list_when_no_categories_exist(client):
    response = client.get(DB_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["missatge"] == "Categories obtingudes correctament"
    assert body["categories"] == []


def test_get_db_categories_returns_categories_present_in_database(
    client,
    shared_home_with_products,
):
    response = client.get(DB_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    names = set(get_category_names(body))

    assert len(names) > 0
    assert len(names) == len(body["categories"])


def test_get_db_categories_are_sorted_alphabetically(
    client,
    shared_home_with_products,
):
    response = client.get(DB_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_category_names(body)

    assert names == sorted(names)


def test_get_db_categories_contains_no_duplicates(
    client,
    shared_home_with_products,
):
    response = client.get(DB_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_category_names(body)

    assert len(names) == len(set(names))


def test_get_db_categories_can_be_filtered_by_search_text(
    client,
    shared_home_with_products,
):
    response = client.get(f"{DB_CATEGORIES_ENDPOINT}?q=arr")
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_category_names(body)

    assert len(names) > 0
    assert all("arr" in name.lower() for name in names)


def test_get_db_categories_search_is_case_insensitive(
    client,
    shared_home_with_products,
):
    response = client.get(f"{DB_CATEGORIES_ENDPOINT}?q=ARR")
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_category_names(body)

    assert len(names) > 0
    assert all("arr" in name.lower() for name in names)


def test_get_db_categories_search_with_no_results_returns_empty_list(
    client,
    shared_home_with_products,
):
    response = client.get(f"{DB_CATEGORIES_ENDPOINT}?q=this-category-does-not-exist")
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["categories"] == []


def test_get_db_categories_does_not_require_authentication(
    client,
    shared_home_with_products,
):
    response = client.get(DB_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["missatge"] == "Categories obtingudes correctament"


def test_get_db_categories_with_invalid_auth_still_returns_success(
    client,
    shared_home_with_products,
):
    response = client.get(
        DB_CATEGORIES_ENDPOINT,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["missatge"] == "Categories obtingudes correctament"