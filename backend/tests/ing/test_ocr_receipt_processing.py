OCR_ENDPOINT = "/inventory/ticket/ocr"


def assert_ocr_success(response, expected_code="OCR_SUCCESS"):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "productes" in body
    return body


def post_ticket_ocr(
    client, headers, file_bytes, filename="ticket.png", content_type="image/png"
):
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
    items.append(
        make_ocr_detected_item(
            nom="Aigua", categoria="WATER_AND_FLAVORED_WATER", preu="1.00"
        )
    )
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
            categoria_label=None,
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
        make_ocr_detected_item(nom=None, categoria="MILK", preu="1.25"),
        make_ocr_detected_item(nom="Galetes", categoria=None, preu="2.15"),
        make_ocr_detected_item(nom="Aigua", categoria="OTHER", preu=None),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 3

    assert body["productes"][0]["nom"] is None
    assert body["productes"][0]["categoria"] == "MILK"
    assert body["productes"][0]["preu"] == "1.25"

    assert body["productes"][1]["nom"] == "Galetes"
    assert body["productes"][1]["categoria"] is None
    assert body["productes"][1]["preu"] == "2.15"

    assert body["productes"][2]["nom"] == "Aigua"
    assert body["productes"][2]["categoria"] == "OTHER"
    assert body["productes"][2]["preu"] is None


def test_ocr_returns_preliminary_products_even_with_minimum_product_info(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(nom="Refresc", categoria=None, preu=None),
        make_ocr_detected_item(nom=None, categoria=None, preu="1.25"),
        make_ocr_detected_item(nom=None, categoria="FRESH_FRUIT", preu=None),
    ]
    mock_ticket_ocr_success(items)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    body = assert_ocr_success(response)

    assert len(body["productes"]) == 3

    assert body["productes"][0]["nom"] == "Refresc"
    assert body["productes"][0]["categoria"] is None
    assert body["productes"][0]["preu"] is None

    assert body["productes"][1]["nom"] is None
    assert body["productes"][1]["categoria"] is None
    assert body["productes"][1]["preu"] == "1.25"

    assert body["productes"][2]["nom"] is None
    assert body["productes"][2]["categoria"] == "FRESH_FRUIT"
    assert body["productes"][2]["preu"] is None


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


def test_ocr_returns_different_ticket_lines_separately_even_if_products_are_similar(
    client,
    shared_home_setup,
    fake_png_bytes,
    make_ocr_detected_item,
    mock_ticket_ocr_success,
):
    items = [
        make_ocr_detected_item(
            nom="Tomàquet",
            categoria="FRESH_VEGETABLES",
            quantitat=2,
            preu="2.30",
        ),
        make_ocr_detected_item(
            nom="Tomàquet_A",
            categoria="FRESH_VEGETABLES",
            quantitat=1,
            preu="1.10",
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
    returned_names = [product["nom"] for product in body["productes"]]
    assert returned_names == ["Tomàquet", "Tomàquet_A"]