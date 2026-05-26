from datetime import date, timedelta

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


def assert_all_quantities_gte(products, minimum):
    for product in products:
        assert product["quantitat"] >= minimum


def assert_all_quantities_lte(products, maximum):
    for product in products:
        assert product["quantitat"] <= maximum


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
    ok_from = (date.today() + timedelta(days=7)).isoformat()
    for product in products:
        assert product["data_caducitat"] is not None
        assert product["data_caducitat"] > ok_from


def make_inventory_product_with_expiry(
    seed_product_db,
    home_id,
    created_by_ctx,
    name,
    category,
    quantity,
    expiration_date,
    owner_user_ids=None,
):
    return seed_product_db(
        home_id=home_id,
        created_by_ctx=created_by_ctx,
        name=name,
        category=category,
        quantity=quantity,
        price="1.00",
        expiration_date=expiration_date,
        owner_user_ids=owner_user_ids or [],
    )


def test_inventory_filter_by_name_and_expiry_returns_only_matching_products(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk expired",
        category="OTHER",
        quantity=1,
        expiration_date=today - timedelta(days=1),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk soon",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=3),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="rice soon",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=3),
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&expiry_filter=expiring_soon",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "milk soon" in names
    assert "milk expired" not in names
    assert "rice soon" not in names
    assert_all_names_contain(products, "milk")
    assert_all_expiring_soon(products)


def test_inventory_filter_by_category_and_expiry_returns_only_matching_products(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="veg expired",
        category="FRESH_VEGETABLES",
        quantity=1,
        expiration_date=today - timedelta(days=1),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="veg soon",
        category="FRESH_VEGETABLES",
        quantity=1,
        expiration_date=today + timedelta(days=2),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk soon",
        category="MILK",
        quantity=1,
        expiration_date=today + timedelta(days=2),
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?categoria=FRESH_VEGETABLES&expiry_filter=expiring_soon",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "veg soon" in names
    assert "veg expired" not in names
    assert "milk soon" not in names
    assert_all_categories_equal(products, "FRESH_VEGETABLES")
    assert_all_expiring_soon(products)


def test_inventory_filter_by_quantity_range_and_expiry_returns_only_matching_products(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="q1 soon",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=2),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="q5 soon",
        category="OTHER",
        quantity=5,
        expiration_date=today + timedelta(days=2),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="q10 expired",
        category="OTHER",
        quantity=10,
        expiration_date=today - timedelta(days=1),
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?min_quantity=5&max_quantity=10&expiry_filter=expired",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "q10 expired" in names
    assert "q1 soon" not in names
    assert "q5 soon" not in names
    assert_all_quantities_between(products, 5, 10)
    assert_all_expired(products)


def test_inventory_filter_by_owner_and_expiry_returns_only_matching_products(
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

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="owner soon",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[owner_id],
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, member1_ctx,
        name="member soon",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=2),
        owner_user_ids=[member1_id],
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="owner expired",
        category="OTHER",
        quantity=1,
        expiration_date=today - timedelta(days=1),
        owner_user_ids=[owner_id],
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?owner_user_id={owner_id}&expiry_filter=expiring_soon",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "owner soon" in names
    assert "member soon" not in names
    assert "owner expired" not in names
    assert_all_expiring_soon(products)


def test_inventory_filter_by_name_category_and_expiry_returns_only_matching_products(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="rice soon",
        category="RICE",
        quantity=3,
        expiration_date=today + timedelta(days=2),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="rice expired",
        category="RICE",
        quantity=3,
        expiration_date=today - timedelta(days=2),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk soon",
        category="MILK",
        quantity=3,
        expiration_date=today + timedelta(days=2),
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=rice&categoria=RICE&expiry_filter=expiring_soon",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "rice soon" in names
    assert "rice expired" not in names
    assert "milk soon" not in names
    assert_all_names_contain(products, "rice")
    assert_all_categories_equal(products, "RICE")
    assert_all_expiring_soon(products)


def test_inventory_combined_filters_with_no_matches_returns_empty_list(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="rice ok",
        category="RICE",
        quantity=3,
        expiration_date=today + timedelta(days=20),
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&categoria=RICE&expiry_filter=expired",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_inventory_invalid_expiry_filter_is_ignored_and_does_not_break_other_filters(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk expired",
        category="OTHER",
        quantity=1,
        expiration_date=today - timedelta(days=1),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk ok",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=20),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="rice ok",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=20),
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&expiry_filter=not_a_valid_value",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    # El backend actual ignora expiry_filter inválido y aplica el resto
    assert "milk expired" in names
    assert "milk ok" in names
    assert "rice ok" not in names
    assert_all_names_contain(products, "milk")


def test_inventory_filter_by_name_and_ok_expiry_returns_only_products_after_next_7_days(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk soon",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=7),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="milk ok",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=8),
    )
    make_inventory_product_with_expiry(
        seed_product_db, home_id, owner_ctx,
        name="rice ok",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=20),
    )

    response = client.get(
        f"{INVENTORY_ENDPOINT}?nom=milk&expiry_filter=ok",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "milk ok" in names
    assert "milk soon" not in names
    assert "rice ok" not in names
    assert_all_names_contain(products, "milk")
    assert_all_ok(products)