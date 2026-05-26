from datetime import date, timedelta


INVENTORY_ENDPOINT = "/inventory/"


def get_response_products(body):
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    return body["productes"]


def get_response_names(body):
    return {product["nom"] for product in get_response_products(body)}


def assert_products_sorted_by_expiration_ascending(products):
    dates = [
        product["data_caducitat"]
        for product in products
        if product["data_caducitat"] is not None
    ]
    assert dates == sorted(dates)


def assert_all_expiring_soon(products):
    today = date.today().isoformat()
    soon = (date.today() + timedelta(days=7)).isoformat()

    for product in products:
        assert product["data_caducitat"] is not None
        assert today <= product["data_caducitat"] <= soon


def set_inventory_product_nutrition_score(client, inventory_product_id, nutrition_score):
    db = client.db_session_factory()
    try:
        inventory_models = client.app_modules["inventory_models"]
        InventoryProduct = inventory_models.InventoryProduct
        CatalogProduct = inventory_models.CatalogProduct

        inv_product = (
            db.query(InventoryProduct)
            .filter(InventoryProduct.id_inventari == int(inventory_product_id))
            .first()
        )
        assert inv_product is not None

        catalog_product = (
            db.query(CatalogProduct)
            .filter(
                CatalogProduct.id_producte_cataleg
                == inv_product.id_producte_cataleg
            )
            .first()
        )
        assert catalog_product is not None

        catalog_product.nutriscore_grade = nutrition_score
        db.commit()
    finally:
        db.close()


def make_inventory_product_with_nutrition_score(
    client,
    seed_product_db,
    home_id,
    created_by_ctx,
    name,
    category="OTHER",
    quantity=1,
    nutrition_score=None,
    expiration_date=None,
    owner_user_ids=None,
):
    product = seed_product_db(
        home_id=home_id,
        created_by_ctx=created_by_ctx,
        name=name,
        category=category,
        quantity=quantity,
        price="1.00",
        expiration_date=expiration_date,
        owner_user_ids=owner_user_ids or [],
    )
    set_inventory_product_nutrition_score(
        client,
        product["id"],
        nutrition_score,
    )
    return product


def test_filter_by_nutrition_score_returns_only_matching_products(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="nutri a product",
        nutrition_score="A",
    )
    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="nutri b product",
        nutrition_score="B",
    )
    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="no nutri product",
        nutrition_score=None,
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nutrition_score=A",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert "nutri a product" in names
    assert "nutri b product" not in names
    assert "no nutri product" not in names


def test_filter_by_nutrition_score_is_case_insensitive(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="lowercase stored nutri b product",
        nutrition_score="b",
    )
    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="nutri c product",
        nutrition_score="C",
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nutrition_score=b",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    names = get_response_names(body)

    assert "lowercase stored nutri b product" in names
    assert "nutri c product" not in names


def test_filter_by_nutrition_score_with_no_matches_returns_empty_list(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="only nutri c product",
        nutrition_score="C",
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nutrition_score=A",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_filter_by_invalid_nutrition_score_returns_400(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nutrition_score=Z",
        headers=headers,
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "NUTRITION_SCORE_INVALID"
    assert body["error"] == "nutrition_score ha de ser A, B, C, D o E."


def test_filter_by_nutrition_score_and_expiry_filter_are_combined(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="nutri a later soon product",
        nutrition_score="A",
        expiration_date=today + timedelta(days=5),
    )
    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="nutri a earlier soon product",
        nutrition_score="A",
        expiration_date=today + timedelta(days=2),
    )
    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="nutri a expired product",
        nutrition_score="A",
        expiration_date=today - timedelta(days=1),
    )
    make_inventory_product_with_nutrition_score(
        client,
        seed_product_db,
        home_id,
        owner_ctx,
        name="nutri b soon product",
        nutrition_score="B",
        expiration_date=today + timedelta(days=3),
    )

    response = client.get(
        (
            f"{INVENTORY_ENDPOINT}?nutrition_score=A"
            "&expiry_filter=expiring_soon"
        ),
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "nutri a earlier soon product" in names
    assert "nutri a later soon product" in names
    assert "nutri a expired product" not in names
    assert "nutri b soon product" not in names

    assert_all_expiring_soon(products)
    assert_products_sorted_by_expiration_ascending(products)
