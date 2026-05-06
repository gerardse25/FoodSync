from app.product_schemas import CATEGORY_LABELS_CA, ProductCategory

ALL_CATEGORIES_ENDPOINT = "/inventory/categories/all"


def test_get_all_categories_returns_success_and_expected_shape(client):
    response = client.get(ALL_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "ALL_CATEGORIES_RETRIEVED"
    assert body["missatge"] == "Categories completes obtingudes correctament"
    assert "categories" in body
    assert isinstance(body["categories"], list)
    assert len(body["categories"]) > 0

    for category in body["categories"]:
        assert "value" in category
        assert "label" in category
        assert isinstance(category["value"], str)
        assert isinstance(category["label"], str)
        assert category["value"] != ""
        assert category["label"] != ""


def test_get_all_categories_returns_all_enum_categories(client):
    response = client.get(ALL_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()

    expected = {
        (category.value, CATEGORY_LABELS_CA[category]) for category in ProductCategory
    }
    returned = {
        (category["value"], category["label"]) for category in body["categories"]
    }

    assert returned == expected
    assert body["code"] == "ALL_CATEGORIES_RETRIEVED"


def test_get_all_categories_contains_no_duplicate_values(client):
    response = client.get(ALL_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    values = [category["value"] for category in body["categories"]]

    assert len(values) == len(set(values))
    assert body["code"] == "ALL_CATEGORIES_RETRIEVED"


def test_get_all_categories_contains_no_duplicate_labels(client):
    response = client.get(ALL_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    labels = [category["label"] for category in body["categories"]]

    assert len(labels) == len(set(labels))
    assert body["code"] == "ALL_CATEGORIES_RETRIEVED"


def test_get_all_categories_does_not_require_authentication(client):
    response = client.get(ALL_CATEGORIES_ENDPOINT)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "ALL_CATEGORIES_RETRIEVED"


def test_get_all_categories_with_invalid_auth_still_returns_success(client):
    response = client.get(
        ALL_CATEGORIES_ENDPOINT,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["code"] == "ALL_CATEGORIES_RETRIEVED"
