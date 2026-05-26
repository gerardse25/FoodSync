from datetime import date, timedelta

'''
nom / search
categoria
min_quantity
max_quantity
owner_user_id
nutrition_score
expiry_filter
'''

INVENTORY_ENDPOINT = "/inventory/"


def get_response_products(body):
    assert body["code"] == "INVENTORY_RETRIEVED"
    assert "productes" in body
    assert isinstance(body["productes"], list)
    return body["productes"]


def get_response_names(body):
    return {product["nom"] for product in get_response_products(body)}


def assert_all_names_contain(products, search_term):
    for product in products:
        assert search_term.lower() in product["nom"].lower()


def assert_all_categories_equal(products, category):
    for product in products:
        assert product["categoria"] == category


def assert_all_quantities_between(products, minimum, maximum):
    for product in products:
        assert minimum <= product["quantitat"] <= maximum


def assert_all_owned_by(products, owner_user_id):
    for product in products:
        owner_ids = {owner["id_usuari"] for owner in product["propietaris"]}
        assert owner_user_id in owner_ids


def assert_all_expired(products):
    today = date.today().isoformat()
    for product in products:
        assert product["data_caducitat"] is not None
        assert product["data_caducitat"] < today


def assert_all_expiring_soon(products):
    today = date.today().isoformat()
    soon = (date.today() + timedelta(days=7)).isoformat()
    for product in products:
        assert product["data_caducitat"] is not None
        assert today <= product["data_caducitat"] <= soon


def assert_all_ok(products):
    today = date.today().isoformat()
    for product in products:
        assert product["data_caducitat"] is not None
        assert product["data_caducitat"] > today


def assert_products_sorted_by_expiration_ascending(products):
    dates = [
        product["data_caducitat"]
        for product in products
        if product["data_caducitat"] is not None
    ]
    assert dates == sorted(dates)


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


def make_inventory_product(
    client,
    seed_product_db,
    *,
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


def test_inventory_combines_search_category_quantity_owner_nutrition_and_expiring_soon(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]
    member1_ctx = shared_home_setup["member1"]
    owner_id = owner_ctx["user"]["id"]
    member1_id = member1_ctx["user"]["id"]
    today = date.today()

    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo alfa milk target",
        category="MILK",
        quantity=5,
        nutrition_score="A",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo beta milk wrong name",
        category="MILK",
        quantity=5,
        nutrition_score="A",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo alfa rice wrong category",
        category="RICE",
        quantity=5,
        nutrition_score="A",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo alfa milk wrong quantity",
        category="MILK",
        quantity=2,
        nutrition_score="A",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member1_ctx,
        name="combo alfa milk wrong owner",
        category="MILK",
        quantity=5,
        nutrition_score="A",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[member1_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo alfa milk wrong nutrition",
        category="MILK",
        quantity=5,
        nutrition_score="B",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo alfa milk wrong expiry",
        category="MILK",
        quantity=5,
        nutrition_score="A",
        expiration_date=today + timedelta(days=20),
        owner_user_ids=[owner_id],
    )

    response = client.get(
        INVENTORY_ENDPOINT,
        params={
            "nom": "alfa",
            "categoria": "MILK",
            "min_quantity": 4,
            "max_quantity": 6,
            "owner_user_id": owner_id,
            "nutrition_score": "A",
            "expiry_filter": "expiring_soon",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert names == {"combo alfa milk target"}
    assert_all_names_contain(products, "alfa")
    assert_all_categories_equal(products, "MILK")
    assert_all_quantities_between(products, 4, 6)
    assert_all_owned_by(products, owner_id)
    assert_all_expiring_soon(products)
    assert_products_sorted_by_expiration_ascending(products)


def test_inventory_combines_search_param_category_quantity_owner_nutrition_and_expired(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]
    member1_ctx = shared_home_setup["member1"]
    owner_id = owner_ctx["user"]["id"]
    member1_id = member1_ctx["user"]["id"]
    today = date.today()

    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo expired cereal target",
        category="BREAKFAST_CEREALS",
        quantity=4,
        nutrition_score="b",
        expiration_date=today - timedelta(days=1),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo expired cereal soon not expired",
        category="BREAKFAST_CEREALS",
        quantity=4,
        nutrition_score="B",
        expiration_date=today + timedelta(days=3),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo expired cereal wrong nutrition",
        category="BREAKFAST_CEREALS",
        quantity=4,
        nutrition_score="C",
        expiration_date=today - timedelta(days=1),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member1_ctx,
        name="combo expired cereal wrong owner",
        category="BREAKFAST_CEREALS",
        quantity=4,
        nutrition_score="B",
        expiration_date=today - timedelta(days=1),
        owner_user_ids=[member1_id],
    )

    response = client.get(
        INVENTORY_ENDPOINT,
        params={
            "search": "expired cereal",
            "categoria": "BREAKFAST_CEREALS",
            "min_quantity": 3,
            "max_quantity": 5,
            "owner_user_id": owner_id,
            "nutrition_score": "B",
            "expiry_filter": "expired",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert names == {"combo expired cereal target"}
    assert_all_names_contain(products, "expired cereal")
    assert_all_categories_equal(products, "BREAKFAST_CEREALS")
    assert_all_quantities_between(products, 3, 5)
    assert_all_owned_by(products, owner_id)
    assert_all_expired(products)


def test_inventory_combines_all_filters_with_ok_expiry(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]
    owner_id = owner_ctx["user"]["id"]
    today = date.today()

    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo ok pasta target",
        category="PASTA",
        quantity=8,
        nutrition_score="C",
        expiration_date=today + timedelta(days=30),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo ok pasta expiring soon",
        category="PASTA",
        quantity=8,
        nutrition_score="C",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo ok pasta quantity too high",
        category="PASTA",
        quantity=12,
        nutrition_score="C",
        expiration_date=today + timedelta(days=30),
        owner_user_ids=[owner_id],
    )

    response = client.get(
        INVENTORY_ENDPOINT,
        params={
            "nom": "ok pasta",
            "categoria": "PASTA",
            "min_quantity": 7,
            "max_quantity": 9,
            "owner_user_id": owner_id,
            "nutrition_score": "c",
            "expiry_filter": "ok",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert names == {"combo ok pasta target"}
    assert_all_names_contain(products, "ok pasta")
    assert_all_categories_equal(products, "PASTA")
    assert_all_quantities_between(products, 7, 9)
    assert_all_owned_by(products, owner_id)
    assert_all_ok(products)


def test_inventory_all_filters_return_empty_when_no_single_product_matches_everything(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]
    member1_ctx = shared_home_setup["member1"]
    owner_id = owner_ctx["user"]["id"]
    member1_id = member1_ctx["user"]["id"]
    today = date.today()

    # Cada producte coincideix amb alguns filtres, però cap compleix tots a la vegada.
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo empty milk wrong nutrition",
        category="MILK",
        quantity=5,
        nutrition_score="D",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=owner_ctx,
        name="combo empty milk wrong expiry",
        category="MILK",
        quantity=5,
        nutrition_score="A",
        expiration_date=today + timedelta(days=20),
        owner_user_ids=[owner_id],
    )
    make_inventory_product(
        client,
        seed_product_db,
        home_id=home_id,
        created_by_ctx=member1_ctx,
        name="combo empty milk wrong owner",
        category="MILK",
        quantity=5,
        nutrition_score="A",
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[member1_id],
    )

    response = client.get(
        INVENTORY_ENDPOINT,
        params={
            "nom": "combo empty",
            "categoria": "MILK",
            "min_quantity": 4,
            "max_quantity": 6,
            "owner_user_id": owner_id,
            "nutrition_score": "A",
            "expiry_filter": "expiring_soon",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_inventory_all_filters_keep_quantity_range_validation(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]
    owner_id = shared_home_setup["owner"]["user"]["id"]

    response = client.get(
        INVENTORY_ENDPOINT,
        params={
            "nom": "anything",
            "categoria": "MILK",
            "min_quantity": 10,
            "max_quantity": 2,
            "owner_user_id": owner_id,
            "nutrition_score": "A",
            "expiry_filter": "expiring_soon",
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "QUANTITY_RANGE_INVALID"


def test_inventory_all_filters_keep_nutrition_score_validation(
    client,
    shared_home_setup,
):
    headers = shared_home_setup["owner_headers"]
    owner_id = shared_home_setup["owner"]["user"]["id"]

    response = client.get(
        INVENTORY_ENDPOINT,
        params={
            "nom": "anything",
            "categoria": "MILK",
            "min_quantity": 1,
            "max_quantity": 10,
            "owner_user_id": owner_id,
            "nutrition_score": "Z",
            "expiry_filter": "expiring_soon",
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text

    body = response.json()
    assert body["code"] == "NUTRITION_SCORE_INVALID"
