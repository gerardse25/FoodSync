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

def test_filter_by_expired_returns_only_products_with_past_expiration_date(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="expired product",
        category="OTHER",
        quantity=1,
        expiration_date=today - timedelta(days=1),
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="soon product",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=3),
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="ok product",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=20),
    )

    response = client.get(f"{INVENTORY_ENDPOINT}?expiry_filter=expired", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "expired product" in names
    assert "soon product" not in names
    assert "ok product" not in names

    for product in products:
        assert product["data_caducitat"] < today.isoformat()


def test_filter_by_expiring_soon_returns_only_products_expiring_within_next_7_days(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="expired product",
        category="OTHER",
        quantity=1,
        expiration_date=today - timedelta(days=1),
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="today product",
        category="OTHER",
        quantity=1,
        expiration_date=today,
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="soon product",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=7),
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="ok product",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=8),
    )

    response = client.get(f"{INVENTORY_ENDPOINT}?expiry_filter=expiring_soon", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "today product" in names
    assert "soon product" in names
    assert "expired product" not in names
    assert "ok product" not in names

    lower_bound = today.isoformat()
    upper_bound = (today + timedelta(days=7)).isoformat()

    for product in products:
        assert lower_bound <= product["data_caducitat"] <= upper_bound


def test_filter_by_ok_returns_only_products_with_expiration_date_after_today(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="expired product",
        category="OTHER",
        quantity=1,
        expiration_date=today - timedelta(days=1),
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="today product",
        category="OTHER",
        quantity=1,
        expiration_date=today,
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="ok product",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=8),
    )

    response = client.get(f"{INVENTORY_ENDPOINT}?expiry_filter=ok", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)
    names = get_response_names(body)

    assert "ok product" in names
    assert "expired product" not in names
    assert "today product" not in names

    for product in products:
        assert product["data_caducitat"] > today.isoformat()


def test_filter_by_expiry_with_no_matches_returns_empty_list(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="only ok product",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=20),
    )

    response = client.get(f"{INVENTORY_ENDPOINT}?expiry_filter=expired", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert get_response_products(body) == []


def test_filter_by_expiry_orders_results_by_expiration_date_ascending(
    client,
    shared_home_setup,
    seed_product_db,
):
    headers = shared_home_setup["owner_headers"]
    home_id = shared_home_setup["home_id"]
    owner_ctx = shared_home_setup["owner"]

    today = date.today()

    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="later expiry",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=6),
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="earlier expiry",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=2),
    )
    make_inventory_product_with_expiry(
        seed_product_db,
        home_id,
        owner_ctx,
        name="middle expiry",
        category="OTHER",
        quantity=1,
        expiration_date=today + timedelta(days=4),
    )

    response = client.get(f"{INVENTORY_ENDPOINT}?expiry_filter=expiring_soon", headers=headers)
    assert response.status_code == 200, response.text

    body = response.json()
    products = get_response_products(body)

    assert len(products) >= 3
    assert_products_sorted_by_expiration_ascending(products)