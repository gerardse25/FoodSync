import pytest

OCR_ENDPOINT = "/inventory/ticket/ocr"


def assert_ocr_error(response, expected_status, expected_code):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_code
    assert "error" in body
    return body


def post_ticket_ocr(
    client, headers, file_bytes, filename="ticket.png", content_type="image/png"
):
    return client.post(
        "/inventory/ticket/ocr",
        headers=headers,
        files={"file": (filename, file_bytes, content_type)},
    )


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_unauthenticated_user_uploading_image_returns_error(
    client,
    headers,
    fake_png_bytes,
):
    response = post_ticket_ocr(
        client,
        headers,
        fake_png_bytes,
    )

    body = response.json()
    assert response.status_code in (401, 403), response.text
    assert body["code"] == "AUTH_REQUIRED"


def test_empty_file_returns_error(
    client,
    shared_home_setup,
):
    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        b"",
    )

    assert_ocr_error(response, 400, "EMPTY_FILE")


def test_invalid_file_not_an_image_returns_error(
    client,
    shared_home_setup,
):
    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        b"this-is-not-an-image",
        filename="ticket.txt",
        content_type="text/plain",
    )

    assert_ocr_error(response, 415, "UNSUPPORTED_IMAGE_FORMAT")


def test_image_with_invalid_dimensions_returns_error(
    client,
    shared_home_setup,
    monkeypatch,
):
    ticket_routes = client.app_modules["ticket_routes"]

    def fake_validate_image(**kwargs):
        raise ticket_routes.ImageValidationError(
            code="INVALID_IMAGE_DIMENSIONS",
            message="Dimensions d'imatge no vàlides.",
            status_code=400,
        )

    monkeypatch.setattr(ticket_routes, "validate_image", fake_validate_image)

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        b"fake-image-bytes",
    )

    assert_ocr_error(response, 400, "INVALID_IMAGE_DIMENSIONS")


def test_corrupted_image_returns_error(
    client,
    shared_home_setup,
    monkeypatch,
):
    ticket_routes = client.app_modules["ticket_routes"]

    def fake_validate_image(**kwargs):
        return None

    def fake_process_ticket_image(_image_bytes):
        raise ValueError("Imatge corrupta o no es pot decodificar")

    monkeypatch.setattr(ticket_routes, "validate_image", fake_validate_image)
    monkeypatch.setattr(
        ticket_routes, "process_ticket_image", fake_process_ticket_image
    )

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        b"corrupted-image-bytes",
    )

    assert_ocr_error(response, 422, "OCR_PROCESSING_ERROR")


def test_external_ocr_engine_error_returns_controlled_error(
    client,
    shared_home_setup,
    fake_png_bytes,
    mock_ticket_ocr_failure,
):
    mock_ticket_ocr_failure(RuntimeError("OCR engine failed"))

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    assert_ocr_error(response, 500, "OCR_ENGINE_ERROR")


def test_external_ocr_timeout_returns_controlled_error(
    client,
    shared_home_setup,
    fake_png_bytes,
    monkeypatch,
):
    ticket_routes = client.app_modules["ticket_routes"]

    monkeypatch.setattr(ticket_routes, "validate_image", lambda **kwargs: None)

    def fake_process_ticket_image(_image_bytes):
        raise TimeoutError("OCR request timeout")

    monkeypatch.setattr(
        ticket_routes, "process_ticket_image", fake_process_ticket_image
    )

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    assert_ocr_error(response, 422, "OCR_PROCESSING_ERROR")


def test_external_ocr_malformed_response_returns_controlled_error(
    client,
    shared_home_setup,
    fake_png_bytes,
    monkeypatch,
):
    ticket_routes = client.app_modules["ticket_routes"]

    monkeypatch.setattr(ticket_routes, "validate_image", lambda **kwargs: None)

    def fake_process_ticket_image(_image_bytes):
        raise ValueError("Malformed OCR response")

    monkeypatch.setattr(
        ticket_routes, "process_ticket_image", fake_process_ticket_image
    )

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    assert_ocr_error(response, 422, "OCR_PROCESSING_ERROR")


def test_illegible_image_returns_empty_list_or_functional_equivalent_response(
    client,
    shared_home_setup,
    fake_png_bytes,
    mock_ticket_ocr_success,
):
    mock_ticket_ocr_success([])

    response = post_ticket_ocr(
        client,
        shared_home_setup["owner_headers"],
        fake_png_bytes,
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["code"] in ("OCR_NO_PRODUCTS")
    assert "productes" in body
    assert body["productes"] == []