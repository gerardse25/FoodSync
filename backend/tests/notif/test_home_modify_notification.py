from datetime import date, timedelta

LIST_NOTIFICATIONS_ENDPOINT = "/notifications"
MANUAL_ENTRY_ENDPOINT = "/inventory/manual"
CATEGORY_EXAMPLE = "RICE"

def list_notifications_request(client, headers):
    return client.get(LIST_NOTIFICATIONS_ENDPOINT, headers=headers)

def load_num_of_notifications(client, headers):
    response = list_notifications_request(client, headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "NOTIFICATIONS_RETRIEVED"
    return len(body["notifications"])

def future_expiration_date(days=90):
    return (date.today() + timedelta(days=days)).isoformat()

def make_manual_inventory_payload(
    *,
    nom: str | None = "manual product",
    preu: str | int | float | None = "2.50",
    categoria: str | None = CATEGORY_EXAMPLE,
    quantitat: int | None = 1,
    data_compra: str | None = None,
    data_caducitat: str | None = None,
    id_propietaris_privats: list[str] | None = None,
):
    return {
        "nom": nom,
        "preu": preu,
        "categoria": categoria,
        "quantitat": quantitat,
        "data_compra": data_compra,
        "data_caducitat": data_caducitat or future_expiration_date(),
        "id_propietaris_privats": id_propietaris_privats or [],
    }

def test_user_joins_home_generates_notification_for_other_users_in_home(client, outsider_user, shared_home_setup):
    new_user_headers = outsider_user["headers"]
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]
    home_invite_code = shared_home_setup["invite_code"]

    # Load users initial num of notifications
    new_user_old_num_notifications = load_num_of_notifications(client, new_user_headers)
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)

    # New user joins home
    response = client.post(
        "/home/join",
        json={"invite_code": home_invite_code},
        headers=new_user_headers,
    )
    assert response.status_code == 200, response.text

    # Validate new num of notifications
    assert load_num_of_notifications(client, new_user_headers) == new_user_old_num_notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications + 1
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications + 1
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications + 1

def test_creating_a_home_does_not_create_new_notifications(client, outsider_user):
    headers = outsider_user["headers"]
    old_num_notifications = load_num_of_notifications(client, headers)

    response = client.post("/home/", json={"name": "New Home"}, headers=headers)
    assert response.status_code == 201, response.text

    assert load_num_of_notifications(client, headers) == old_num_notifications

def test_user_adds_public_product_in_home_inventory_generates_notification_for_other_users(client, shared_home_setup):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]

    # Load users initial num of notifications
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)

    # User adds product
    product = make_manual_inventory_payload(
        nom="manual new product",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
    )
    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=owner_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    # Validate new num of notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications + 1
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications + 1

def test_user_adds_own_private_product_in_home_inventory_does_not_generate_notification(client, shared_home_setup):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]
    owner_id = shared_home_setup["owner"]["user"]["id"]

    # Load users initial num of notifications
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)

    # User adds product
    product = make_manual_inventory_payload(
        nom="manual new product",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
        id_propietaris_privats=[owner_id]
    )
    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=owner_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    # Validate new num of notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications


def test_user_adds_private_product_of_another_user_in_home_inventory_generates_notification_for_product_owner_user(client, shared_home_setup):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]
    member1_id = shared_home_setup["member1"]["user"]["id"]

    # Load users initial num of notifications
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)

    # User adds product
    product = make_manual_inventory_payload(
        nom="manual new product",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
        id_propietaris_privats=[member1_id]
    )
    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=owner_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    # Validate new num of notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications + 1
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications

def test_user_adds_private_product_of_other_users_in_home_inventory_generates_notification_for_all_product_owner_users_excluding_himself(client, shared_home_setup):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]
    owner_id = shared_home_setup["owner"]["user"]["id"]
    member1_id = shared_home_setup["member1"]["user"]["id"]

    # Load users initial num of notifications
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)

    # User adds product
    product = make_manual_inventory_payload(
        nom="manual new product",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
        id_propietaris_privats=[member1_id, owner_id]
    )
    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=owner_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    # Validate new num of notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications + 1
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications

def test_user_adds_private_product_of_all_users_in_home_inventory_generates_notification_for_all_users_excluding_himself(client, shared_home_setup):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]
    owner_id = shared_home_setup["owner"]["user"]["id"]
    member1_id = shared_home_setup["member1"]["user"]["id"]
    member2_id = shared_home_setup["member2"]["user"]["id"]

    # Load users initial num of notifications
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)

    # User adds product
    product = make_manual_inventory_payload(
        nom="manual new product",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
        id_propietaris_privats=[member1_id, owner_id, member2_id]
    )
    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=owner_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    # Validate new num of notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications + 1
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications + 1

def test_new_user_in_home_adds_public_product_in_home_inventory_generates_notification_for_all_users_excluding_himself(client, outsider_user, shared_home_setup):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]
    new_user_headers = outsider_user["headers"]
    home_invite_code = shared_home_setup["invite_code"]

    # Load users initial num of notifications
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)
    new_user_old_num_notifications = load_num_of_notifications(client, new_user_headers)

    # New user joins home
    response = client.post(
        "/home/join",
        json={"invite_code": home_invite_code},
        headers=new_user_headers,
    )
    assert response.status_code == 200, response.text

    # User adds product
    product = make_manual_inventory_payload(
        nom="manual new product",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
    )
    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=new_user_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    # Validate new num of notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications + 1
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications + 1
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications + 1
    assert load_num_of_notifications(client, new_user_headers) == new_user_old_num_notifications

def test_new_user_in_home_can_receive_new_notifications(client, outsider_user, shared_home_setup):
    owner_headers = shared_home_setup["owner_headers"]
    member1_headers = shared_home_setup["member1_headers"]
    member2_headers = shared_home_setup["member2_headers"]
    new_user_headers = outsider_user["headers"]
    home_invite_code = shared_home_setup["invite_code"]

    # Load users initial num of notifications
    owner_old_num_notifications = load_num_of_notifications(client, owner_headers)
    member1_old_num_notifications = load_num_of_notifications(client, member1_headers)
    member2_old_num_notifications = load_num_of_notifications(client, member2_headers)
    new_user_old_num_notifications = load_num_of_notifications(client, new_user_headers)

    # New user joins home
    response = client.post(
        "/home/join",
        json={"invite_code": home_invite_code},
        headers=new_user_headers,
    )
    assert response.status_code == 200, response.text

    # User adds product
    product = make_manual_inventory_payload(
        nom="manual new product",
        preu="2.50",
        categoria=CATEGORY_EXAMPLE,
        quantitat=3,
    )
    response = client.post(MANUAL_ENTRY_ENDPOINT, json=product, headers=owner_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "PRODUCT_CREATED"

    # Validate new num of notifications
    assert load_num_of_notifications(client, owner_headers) == owner_old_num_notifications
    assert load_num_of_notifications(client, member1_headers) == member1_old_num_notifications + 1
    assert load_num_of_notifications(client, member2_headers) == member2_old_num_notifications + 1
    assert load_num_of_notifications(client, new_user_headers) == new_user_old_num_notifications + 1
