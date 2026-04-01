import pytest


SUCCESS_REGISTER_CODE = "ACCOUNT_CREATED"
DUPLICATE_EMAIL_CODE = "EMAIL_ALREADY_REGISTERED"


def assert_validation_error(response, expected_code):
    assert response.status_code in (400, 422), response.text
    body = response.json()
    assert body["code"] == expected_code


def test_register_with_valid_data_creates_user_and_session(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "validuser",
            "email": "User@Example.com",
            "password": "Passw0rd",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Compte creat correctament"
    assert body["code"] == SUCCESS_REGISTER_CODE
    assert body["user"]["username"] == "validuser"
    assert body["user"]["email"] == "User@example.com"
    assert isinstance(body["access_token"], str)
    assert isinstance(body["refresh_token"], str)


@pytest.mark.parametrize("email", ["user@example.com", "USER@EXAMPLE.COM"])
def test_register_rejects_duplicate_email_case_insensitive(client, email):
    first = client.post(
        "/auth/register",
        json={"username": "validuser", "email": "user@example.com", "password": "Passw0rd"},
    )
    second = client.post(
        "/auth/register",
        json={"username": "otheruser", "email": email, "password": "Passw0rd"},
    )

    assert first.status_code == 201
    assert first.json()["code"] == SUCCESS_REGISTER_CODE
    assert second.status_code == 409
    body = second.json()
    assert body["detail"] == "Aquest correu electrònic ja està registrat"
    assert body["code"] == DUPLICATE_EMAIL_CODE


@pytest.mark.parametrize(
    "email, username, password, expected_code",
    [
        ("", "validuser", "Passw0rd", "EMAIL_REQUIRED"),
        ("user@example.com", "", "Passw0rd", "USERNAME_REQUIRED"),
        ("user@example.com", "validuser", "", "PASSWORD_REQUIRED"),
        ("", "", "", "REQUIRED_FIELDS_MISSING"),
    ],
    ids=["empty_email", "empty_username", "empty_password", "all_empty"],
)
def test_register_rejects_empty_fields(client, email, username, password, expected_code):
    response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert_validation_error(response, expected_code)


@pytest.mark.parametrize(
    "email, username, password",
    [
        (" user@example.com", "validuser", "Passw0rd"),
        ("user@example.com ", "validuser", "Passw0rd"),
        (" user@example.com ", "validuser", "Passw0rd"),
        ("user@example.com", " validuser", "Passw0rd"),
        ("user@example.com", "validuser ", "Passw0rd"),
        ("user@example.com", "validuser", " Passw0rd"),
        ("user@example.com", "validuser", "Passw0rd "),
    ],
    ids=[
        "email_leading_space",
        "email_trailing_space",
        "email_both_sides",
        "username_leading_space",
        "username_trailing_space",
        "password_leading_space",
        "password_trailing_space",
    ],
)
def test_register_trims_leading_and_trailing_spaces(client, email, username, password):
    response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == SUCCESS_REGISTER_CODE
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["username"] == "validuser"


@pytest.mark.parametrize(
    "email, username, password, expected_code",
    [
        ("user @example.com", "validuser", "Passw0rd", "EMAIL_INVALID_CHARACTERS"),
        ("user@ example.com", "validuser", "Passw0rd", "EMAIL_INVALID_CHARACTERS"),
        ("user@example.com", "valid user", "Passw0rd", "USERNAME_INVALID_SPACES"),
        ("user@example.com", "validuser", "Pass word", "PASSWORD_INVALID_SPACES"),
    ],
    ids=[
        "email_space_before_at",
        "email_space_after_at",
        "username_internal_space",
        "password_internal_space",
    ],
)
def test_register_rejects_internal_spaces(client, email, username, password, expected_code):
    response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert_validation_error(response, expected_code)


@pytest.mark.parametrize(
    "invalid_email",
    [
        "plainaddress",
        "missingatsign.com",
        "@missinglocal.com",
        "user@",
        "user@domain",
        "user domain@example.com",
        "user@.com",
        "user@com",
    ],
)
def test_register_rejects_email_with_invalid_format(client, invalid_email):
    response = client.post(
        "/auth/register",
        json={"email": invalid_email, "username": "validuser", "password": "Passw0rd"},
    )
    assert_validation_error(response, "EMAIL_INVALID_FORMAT")


@pytest.mark.parametrize(
    "email, username, password, expected_code",
    [
        ("user @example.com", "validuser", "Passw0rd", "EMAIL_INVALID_CHARACTERS"),
        ("user	@example.com", "validuser", "Passw0rd", "EMAIL_INVALID_CHARACTERS"),
        ("user@example.com", "valid user", "Passw0rd", "USERNAME_INVALID_CHARACTERS"),
        ("user@example.com", "valid	user", "Passw0rd", "USERNAME_INVALID_CHARACTERS"),
        ("user@example.com", "passuser", "pass word", "PASSWORD_INVALID_CHARACTERS"),
        ("user@example.com", "passuser", "pass	word", "PASSWORD_INVALID_CHARACTERS"),
    ],
)
def test_register_rejects_control_characters(client, email, username, password, expected_code):
    response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert_validation_error(response, expected_code)


@pytest.mark.parametrize(
    "email, should_be_valid",
    [
        ("a@b.com", True),
        ((("a" * 120) + "@t.com"), True),
        ((("a" * 121) + "@t.com"), True),
        ((("a" * 122) + "@t.com"), True),
        ((("a" * 123) + "@t.com"), False),
        ((("a" * 140) + "@t.com"), False),
    ],
)
def test_register_validates_email_length_boundaries(client, email, should_be_valid):
    response = client.post(
        "/auth/register",
        json={"email": email, "username": "validuser", "password": "Passw0rd"},
    )
    if should_be_valid:
        assert response.status_code == 201, response.text
        assert response.json()["code"] == SUCCESS_REGISTER_CODE
    else:
        assert_validation_error(response, "EMAIL_TOO_LONG")


@pytest.mark.parametrize(
    "password, should_be_valid",
    [
        ("123", False),
        ("abcde", False),
        ("abcdef", True),
        ("abcdefg", True),
        ("validPass1", True),
        ("a" * 31, True),
        ("a" * 32, True),
        ("a" * 33, False),
        ("a" * 40, False),
    ],
)
def test_register_validates_password_length_boundaries(client, password, should_be_valid):
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "username": "validuser", "password": password},
    )
    if should_be_valid:
        assert response.status_code == 201, response.text
        assert response.json()["code"] == SUCCESS_REGISTER_CODE
    else:
        code = "PASSWORD_TOO_SHORT" if len(password) < 6 else "PASSWORD_TOO_LONG"
        assert_validation_error(response, code)


@pytest.mark.parametrize(
    "username, should_be_valid",
    [
        ("a", False),
        ("ab", True),
        ("abc", True),
        ("validuser", True),
        (("a" * 15), True),
        (("a" * 16), True),
        (("a" * 17), False),
        (("a" * 25), False),
    ],
)
def test_register_validates_username_length_boundaries(client, username, should_be_valid):
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "username": username, "password": "Passw0rd"},
    )
    if should_be_valid:
        assert response.status_code == 201, response.text
        assert response.json()["code"] == SUCCESS_REGISTER_CODE
    else:
        code = "USERNAME_TOO_SHORT" if len(username) < 2 else "USERNAME_TOO_LONG"
        assert_validation_error(response, code)


def test_register_handles_repository_lookup_failure(unsafe_client):
    routes = unsafe_client.app_modules["routes"]

    class BrokenLookupResult:
        def filter(self, *args, **kwargs):
            raise RuntimeError("lookup failed")

    class BrokenLookupDB:
        def query(self, *args, **kwargs):
            return BrokenLookupResult()

    def override_get_db():
        yield BrokenLookupDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.post(
        "/auth/register",
        json={"email": "user@example.com", "username": "validuser", "password": "Passw0rd"},
    )

    assert response.status_code == 500


def test_register_handles_repository_save_failure(unsafe_client):
    routes = unsafe_client.app_modules["routes"]

    class LookupResult:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class BrokenSaveDB:
        def query(self, *args, **kwargs):
            return LookupResult()

        def add(self, obj):
            return None

        def commit(self):
            raise RuntimeError("save failed")

        def refresh(self, obj):
            return None

    def override_get_db():
        yield BrokenSaveDB()

    unsafe_client.app.dependency_overrides[routes.get_db] = override_get_db

    response = unsafe_client.post(
        "/auth/register",
        json={"email": "user@example.com", "username": "validuser", "password": "Passw0rd"},
    )

    assert response.status_code == 500
