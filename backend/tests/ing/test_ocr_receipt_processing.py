import pytest

OCR_ENDPOINT = "/inventory/ticket/ocr"

def assert_ocr_success(response, expected_code="OCR_SUCCESS"):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "productes" in body
    return body

def post_ticket_ocr(client, headers, file_bytes, filename="ticket.png", content_type="image/png"):
    return client.post(
        "/inventory/ticket/ocr",
        headers=headers,
        files={"file": (filename, file_bytes, content_type)},
    )


def test_ocr_detects_one_product(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    item = make_ocr_detected_item(nom="Llet", categoria="MILK", preu="1.25")
    mock_ticket_ocr_success([item])

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)
    assert len(body["productes"]) == 1
    assert body["productes"][0]["nom"] == "Llet"

def test_ocr_detects_multiple_products(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [] 
    items.append(make_ocr_detected_item(nom="Llet", categoria="MILK", preu="1.25"))
    items.append(make_ocr_detected_item(nom="Galetes", categoria="OTHER", preu="2.15"))
    items.append(make_ocr_detected_item(nom="Aigua", categoria="DRINK", preu="1.00"))
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)
    assert len(body["productes"]) == 3
    assert body["productes"][0]["nom"] == "Llet"
    assert body["productes"][1]["nom"] == "Galetes"
    assert body["productes"][2]["nom"] == "Aigua"

def test_ocr_returns_products_even_when_secondary_fields_are_missing(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(
            nom="Llet",
            categoria="MILK",
            categoria_label="Llet",
            quantitat=1,
            preu="1.25",
        ),
        make_ocr_detected_item(
            nom="Galetes",
            categoria="OTHER",
            quantitat=1,
            preu="2.15",
            data_compra="2026-01-10",
        ),
        make_ocr_detected_item(
            nom="Aigua",
            categoria="OTHER",
            categoria_label="Altres",
            quantitat=1,
            preu="0.95",
            marca="Viladrau",
            quantitat_envas="1.5L",
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 3

    returned_names = [product["nom"] for product in body["productes"]]
    assert returned_names == ["Llet", "Galetes", "Aigua"]

    assert body["productes"][0]["nom"] == "Llet"
    assert body["productes"][0]["categoria"] == "MILK"
    assert body["productes"][0]["preu"] == "1.25"
    assert body["productes"][0]["marca"] is None
    assert body["productes"][0]["data_caducitat"] is None
    assert body["productes"][0]["nutriscore"] is None

    assert body["productes"][1]["nom"] == "Galetes"
    assert body["productes"][1]["categoria"] == "OTHER"
    assert body["productes"][1]["categoria_label"] is None
    assert body["productes"][1]["data_compra"] == "2026-01-10"

    assert body["productes"][2]["nom"] == "Aigua"
    assert body["productes"][2]["marca"] == "Viladrau"
    assert body["productes"][2]["quantitat_envas"] == "1.5L"
    assert body["productes"][2]["data_caducitat"] is None
    assert body["productes"][2]["imatge_url"] is None


def test_ocr_returns_preliminary_products_even_when_some_detected_items_are_highly_incomplete(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(nom="", categoria="MILK", preu="1.25"),
        make_ocr_detected_item(nom="Galetes", categoria="", preu="2.15"),
        make_ocr_detected_item(nom="Aigua", categoria="OTHER", preu=""),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 3

    assert body["productes"][0]["nom"] == ""
    assert body["productes"][0]["categoria"] == "MILK"
    assert body["productes"][0]["preu"] == "1.25"

    assert body["productes"][1]["nom"] == "Galetes"
    assert body["productes"][1]["categoria"] == ""
    assert body["productes"][1]["preu"] == "2.15"

    assert body["productes"][2]["nom"] == "Aigua"
    assert body["productes"][2]["categoria"] == "OTHER"
    assert body["productes"][2]["preu"] == ""

def test_ocr_returns_preliminary_products_even_with_minimum_product_info(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(nom="Refresc", categoria="", preu=""),
        make_ocr_detected_item(nom="", categoria="", preu="1.25"),
        make_ocr_detected_item(nom="", categoria="FRESH_FRUIT", preu=""),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 4

    assert body["productes"][0]["nom"] == "Refresc"
    assert body["productes"][0]["categoria"] == ""
    assert body["productes"][0]["preu"] == ""

    assert body["productes"][1]["nom"] == ""
    assert body["productes"][1]["categoria"] == ""
    assert body["productes"][1]["preu"] == "1.25"

    assert body["productes"][2]["nom"] == ""
    assert body["productes"][2]["categoria"] == "FRESH_FRUIT"
    assert body["productes"][2]["preu"] == ""


def test_ocr_returns_products_with_rich_detected_information(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(
            nom="Llet sencera",
            marca="Ato",
            categoria="MILK",
            categoria_label="Llet",
            quantitat=2,
            preu="2.40",
            data_caducitat="2026-01-18",
            data_compra="2026-01-10",
            quantitat_envas="1L",
            nutriscore="A",
            imatge_url="https://example.com/llet.png",
            id_propietaris_privats=[],
        ),
        make_ocr_detected_item(
            nom="Galetes Maria",
            marca="Cuétara",
            categoria="OTHER",
            categoria_label="Altres",
            quantitat=1,
            preu="1.95",
            data_caducitat="2026-06-01",
            data_compra="2026-01-10",
            quantitat_envas="500g",
            nutriscore="C",
            imatge_url="https://example.com/galetes.png",
            id_propietaris_privats=[],
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 2

    first = body["productes"][0]
    assert first["nom"] == "Llet sencera"
    assert first["marca"] == "Ato"
    assert first["categoria"] == "MILK"
    assert first["categoria_label"] == "Llet"
    assert first["quantitat"] == 2
    assert first["preu"] == "2.40"
    assert first["data_caducitat"] == "2026-01-18"
    assert first["data_compra"] == "2026-01-10"
    assert first["quantitat_envas"] == "1L"
    assert first["nutriscore"] == "A"
    assert first["imatge_url"] == "https://example.com/llet.png"
    assert first["id_propietaris_privats"] == []

    second = body["productes"][1]
    assert second["nom"] == "Galetes Maria"
    assert second["marca"] == "Cuétara"
    assert second["categoria"] == "OTHER"
    assert second["categoria_label"] == "Altres"
    assert second["quantitat"] == 1
    assert second["preu"] == "1.95"
    assert second["data_caducitat"] == "2026-06-01"
    assert second["data_compra"] == "2026-01-10"
    assert second["quantitat_envas"] == "500g"
    assert second["nutriscore"] == "C"
    assert second["imatge_url"] == "https://example.com/galetes.png"
    assert second["id_propietaris_privats"] == []


def test_ocr_returns_empty_list_when_no_identifiable_products_are_found(
    client,
    shared_home_setup,
    fake_png_bytes,
    mock_ticket_ocr_success,
    list_home_products_db,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    before_products = list_home_products_db(home_id)

    mock_ticket_ocr_success([])

    response = post_ticket_ocr(
        client,
        headers,
        fake_png_bytes,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] in ("OCR_NO_PRODUCTS")
    assert "productes" in body
    assert body["productes"] == []

    after_products = list_home_products_db(home_id)
    assert after_products == before_products


def test_ocr_returns_preliminary_products_even_with_incomplete_or_noisy_names(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
    list_home_products_db,
):
    home_id = shared_home_setup["home_id"]
    headers = shared_home_setup["owner_headers"]

    before_products = list_home_products_db(home_id)

    items = [
        make_ocr_detected_item(
            nom="LL3T SENC3RA",
            categoria="MILK",
            categoria_label="Llet",
            quantitat=1,
            preu="1.25",
        ),
        make_ocr_detected_item(
            nom="G4L3T3S M4R14",
            categoria="OTHER",
            categoria_label="Altres",
            quantitat=1,
            preu="2.10",
        ),
        make_ocr_detected_item(
            nom="AIG",
            categoria="OTHER",
            categoria_label="Altres",
            quantitat=1,
            preu="0.95",
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        headers,
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 3

    assert body["productes"][0]["nom"] == "LL3T SENC3RA"
    assert body["productes"][0]["categoria"] == "MILK"
    assert body["productes"][0]["preu"] == "1.25"

    assert body["productes"][1]["nom"] == "G4L3T3S M4R14"
    assert body["productes"][1]["categoria"] == "OTHER"
    assert body["productes"][1]["preu"] == "2.10"

    assert body["productes"][2]["nom"] == "AIG"
    assert body["productes"][2]["categoria"] == "OTHER"
    assert body["productes"][2]["preu"] == "0.95"

    after_products = list_home_products_db(home_id)
    assert after_products == before_products


def test_ocr_groups_repeated_products_with_same_name_and_sums_quantity_and_price(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(
            nom="Llet",
            categoria="MILK",
            categoria_label="Llet",
            quantitat=2,
            preu="1.20",
        ),
        make_ocr_detected_item(
            nom="Llet",
            categoria="MILK",
            categoria_label="Llet",
            quantitat=1,
            preu="1.20",
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 1
    product = body["productes"][0]
    assert product["nom"] == "Llet"
    assert product["quantitat"] == 3
    assert product["preu"] == "2.40"
    assert product["categoria"] == "MILK"
    assert product["categoria_label"] == "Llet"

@pytest.mark.parametrize(
    "quantitat_prod1, quantitat_prod2, quantitat_total",
    [
        (1, 2, 3),
        (1, None, 2),
        (None, 2, 3),
        (None, None, 2),
    ],
)
def test_ocr_groups_repeated_products_treating_missing_quantity_as_one(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
    quantitat_prod1,
    quantitat_prod2,
    quantitat_total,
):
    items = [
        make_ocr_detected_item(
            nom="Arròs",
            categoria="RICE",
            categoria_label="Arròs",
            quantitat=quantitat_prod1,
            preu="1.50",
        ),
        make_ocr_detected_item(
            nom="Arròs",
            categoria="RICE",
            categoria_label="Arròs",
            quantitat=quantitat_prod2,
            preu="1.50",
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 1
    product = body["productes"][0]
    assert product["nom"] == "Arròs"
    assert product["quantitat"] == quantitat_total
    assert product["preu"] == "3.00"

def test_ocr_does_not_group_products_when_name_is_different_even_if_other_fields_match(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(
            nom="Llet sencera",
            categoria="MILK",
            categoria_label="Llet",
            quantitat=1,
            preu="1.20",
        ),
        make_ocr_detected_item(
            nom="Llet semi",
            categoria="MILK",
            categoria_label="Llet",
            quantitat=1,
            preu="1.20",
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 2
    assert body["productes"][0]["nom"] == "Llet sencera"
    assert body["productes"][1]["nom"] == "Llet semi"

@pytest.mark.parametrize(
    "categoria_prod1, label_prod1, categoria_prod2, label_prod2",
    [
        ("MILK", "Llet", "OTHER", "Altres"),
        ("MILK", "", "OTHER", "Altres"),
        ("MILK", "Llet", "OTHER", ""),
        ("MILK", "", "OTHER", ""),
        ("", "Llet", "", "Altres"),
        ("", "", "", ""),
    ],
)
def test_ocr_groups_repeated_products_and_nulls_category_fields_when_category_conflicts(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
    categoria_prod1, categoria_prod2, label_prod1, label_prod2
):
    items = [
        make_ocr_detected_item(
            nom="Producte X",
            categoria=categoria_prod1,
            categoria_label=label_prod1,
            quantitat=1,
            preu="1.00",
        ),
        make_ocr_detected_item(
            nom="Producte X",
            categoria=categoria_prod2,
            categoria_label=label_prod2,
            quantitat=1,
            preu="1.00",
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 1
    product = body["productes"][0]
    assert product["nom"] == "Producte X"
    assert product["quantitat"] == 2
    assert product["preu"] == "2.00"
    assert product["categoria"] is None
    assert product["categoria_label"] is None


@pytest.mark.parametrize(
    "categoria_prod1, label_prod1, categoria_prod2, label_prod2, final_category",
    [
        ("MILK", "Llet", "", "Altres", "MILK"),
        ("", "Llet", "OTHER", "Altres", "OTHER"),
        ("MILK", "Llet", "", "", "MILK"),
        ("", "", "OTHER", "Altres", "OTHER"),
    ],
)
def test_ocr_groups_repeated_products_and_nulls_label_fields(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
    categoria_prod1, categoria_prod2, label_prod1, label_prod2, final_category
):
    items = [
        make_ocr_detected_item(
            nom="Producte X",
            categoria=categoria_prod1,
            categoria_label=label_prod1,
            quantitat=1,
            preu="1.00",
        ),
        make_ocr_detected_item(
            nom="Producte X",
            categoria=categoria_prod2,
            categoria_label=label_prod2,
            quantitat=1,
            preu="1.00",
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 1
    product = body["productes"][0]
    assert product["nom"] == "Producte X"
    assert product["quantitat"] == 2
    assert product["preu"] == "2.00"
    assert product["categoria"] == final_category
    assert product["categoria_label"] is None

@pytest.mark.parametrize(
    "price_prod1, price_prod2, price_total",
    [
        ("1.20", "1.50", "2.70"),
        (None, "1.00", "1.00"),
        ("2.00", None, "2.00"),
        (None, None, None)
    ],
)
def test_ocr_groups_repeated_products_and_sums_price_even_when_unit_price_differs(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
    price_prod1, price_prod2, price_total
):
    items = [
        make_ocr_detected_item(
            nom="Poma",
            categoria="OTHER",
            categoria_label="Altres",
            quantitat=1,
            preu=price_prod1,
        ),
        make_ocr_detected_item(
            nom="Poma",
            categoria="OTHER",
            categoria_label="Altres",
            quantitat=1,
            preu=price_prod2,
        ),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 1
    product = body["productes"][0]
    assert product["nom"] == "Poma"
    assert product["quantitat"] == 2
    assert product["preu"] == price_total
    assert product["categoria"] == "OTHER"
    assert product["categoria_label"] == "Altres"