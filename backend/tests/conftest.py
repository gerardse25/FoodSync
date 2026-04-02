import importlib
import sys
import types
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def app_modules(tmp_path, monkeypatch):
    """
    Carrega el backend real (auth + home) sense editar-ne els fitxers.
    Durant els tests es força SQLite i un UUID portable per poder executar
    el projecte sense PostgreSQL.
    """
    db_file = tmp_path / "test_suite.sqlite3"

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    app_pkg = importlib.import_module("app")

    config_mod = types.ModuleType("app.config")
    config_mod.DATABASE_URL = f"sqlite:///{db_file}"
    config_mod.SECRET_KEY = "test-secret-key"
    config_mod.ALGORITHM = "HS256"
    config_mod.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    config_mod.REFRESH_TOKEN_EXPIRE_DAYS = 7
    config_mod.SMTP_HOST = "smtp.test.local"
    config_mod.SMTP_PORT = 465
    config_mod.SMTP_USER = "noreply@test.local"
    config_mod.SMTP_PASSWORD = "dummy-password"
    config_mod.SMTP_FROM = "noreply@test.local"
    config_mod.FRONTEND_RESET_URL = "http://localhost:3000/reset-password"
    config_mod.PASSWORD_RESET_EXPIRE_MINUTES = 30
    sys.modules["app.config"] = config_mod
    setattr(app_pkg, "config", config_mod)

    import sqlalchemy
    import sqlalchemy.dialects.postgresql as pg

    monkeypatch.setattr(pg, "UUID", sqlalchemy.Uuid, raising=True)

    real_create_engine = sqlalchemy.create_engine

    def create_engine_for_tests(url, *args, **kwargs):
        if str(url).startswith("sqlite"):
            kwargs.setdefault("connect_args", {"check_same_thread": False})
        return real_create_engine(url, *args, **kwargs)

    monkeypatch.setattr(sqlalchemy, "create_engine", create_engine_for_tests, raising=True)

    database = importlib.import_module("app.database")
    models = importlib.import_module("app.models")
    home_models = importlib.import_module("app.home_models")
    auth = importlib.import_module("app.auth")
    routes = importlib.import_module("app.routes")
    home_routes = importlib.import_module("app.home_routes")
    main = importlib.import_module("app.main")

    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)

    sent_emails = []

    def fake_send_reset_email(to_email: str, token: str):
        sent_emails.append({"to_email": to_email, "token": token})

    monkeypatch.setattr(auth, "send_reset_email", fake_send_reset_email)

    yield {
        "app": main.app,
        "auth": auth,
        "routes": routes,
        "home_routes": home_routes,
        "models": models,
        "home_models": home_models,
        "database": database,
        "sent_emails": sent_emails,
    }

    main.app.dependency_overrides.clear()
    database.Base.metadata.drop_all(bind=database.engine)


@pytest.fixture
def client(app_modules):
    with TestClient(app_modules["app"]) as test_client:
        test_client.sent_emails = app_modules["sent_emails"]
        test_client.models = app_modules["models"]
        test_client.home_models = app_modules["home_models"]
        test_client.db_session_factory = app_modules["database"].SessionLocal
        test_client.app_modules = app_modules
        yield test_client


@pytest.fixture
def unsafe_client(app_modules):
    with TestClient(app_modules["app"], raise_server_exceptions=False) as test_client:
        test_client.app_modules = app_modules
        yield test_client


@pytest.fixture
def make_user(client):
    created = []

    def _make_user(*, username: str | None = None, email: str | None = None, password: str = "Passw0rd"):
        idx = len(created) + 1
        username = username or f"user{idx:02d}"
        email = email or f"user{idx:02d}@example.com"
        response = client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        created.append(body)
        return {
            "payload": {"username": username, "email": email, "password": password},
            "response": body,
            "user": body["user"],
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
        }

    return _make_user


@pytest.fixture
def registered_user(make_user):
    return make_user(username="validuser", email="user@example.com")


@pytest.fixture
def auth_headers(registered_user):
    return registered_user["headers"]


@pytest.fixture
def second_session(client, registered_user):
    response = client.post(
        "/auth/login",
        json={
            "email": registered_user["payload"]["email"],
            "password": registered_user["payload"]["password"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
    }


@pytest.fixture
def owner_user(make_user):
    return make_user(username="owner01", email="owner01@example.com")


@pytest.fixture
def member1_user(make_user):
    return make_user(username="member01", email="member01@example.com")


@pytest.fixture
def member2_user(make_user):
    return make_user(username="member02", email="member02@example.com")


@pytest.fixture
def outsider_user(make_user):
    return make_user(username="outsider", email="outsider@example.com")


@pytest.fixture
def create_home_api(client):
    def _create_home(user_ctx, name: str = "My Home"):
        response = client.post("/home/", json={"name": name}, headers=user_ctx["headers"])
        return response

    return _create_home


@pytest.fixture
def join_home_api(client):
    def _join_home(user_ctx, invite_code: str):
        return client.post(
            "/home/join",
            json={"invite_code": invite_code},
            headers=user_ctx["headers"],
        )

    return _join_home


@pytest.fixture
def owner_home(client, owner_user):
    response = client.post("/home/", json={"name": "Shared Home"}, headers=owner_user["headers"])
    assert response.status_code == 201, response.text
    body = response.json()
    home = body["home"]
    return {
        "owner": owner_user,
        "home": home,
        "home_id": home["id"],
        "invite_code": home["invite_code"],
        "response": body,
    }


@pytest.fixture
def shared_home_setup(client, owner_home, member1_user, member2_user):
    join1 = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=member1_user["headers"],
    )
    assert join1.status_code == 200, join1.text

    join2 = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=member2_user["headers"],
    )
    assert join2.status_code == 200, join2.text

    return {
        "home_id": owner_home["home_id"],
        "invite_code": owner_home["invite_code"],
        "owner": owner_home["owner"],
        "owner_session_id": owner_home["owner"]["access_token"],
        "owner_headers": owner_home["owner"]["headers"],
        "member1": member1_user,
        "member1_session_id": member1_user["access_token"],
        "member1_headers": member1_user["headers"],
        "member2": member2_user,
        "member2_session_id": member2_user["access_token"],
        "member2_headers": member2_user["headers"],
    }


@pytest.fixture
def private_home_setup(client, make_user):
    user = make_user(username="private01", email="private01@example.com")
    response = client.post("/home/", json={"name": "Private Home"}, headers=user["headers"])
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "user": user,
        "session_id": user["access_token"],
        "headers": user["headers"],
        "home": body["home"],
        "home_id": body["home"]["id"],
        "invite_code": body["home"]["invite_code"],
    }


@pytest.fixture
def shared_home_member_setup(shared_home_setup):
    return {
        "home_id": shared_home_setup["home_id"],
        "user": shared_home_setup["member1"],
        "owner": shared_home_setup["owner"],
        "session_id": shared_home_setup["member1_session_id"],
        "headers": shared_home_setup["member1_headers"],
    }


@pytest.fixture
def shared_home_owner_setup(client, owner_home, make_user):
    oldest_member = make_user(username="oldest01", email="oldest01@example.com")
    newer_member = make_user(username="newer01", email="newer01@example.com")

    first_join = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=oldest_member["headers"],
    )
    assert first_join.status_code == 200, first_join.text

    second_join = client.post(
        "/home/join",
        json={"invite_code": owner_home["invite_code"]},
        headers=newer_member["headers"],
    )
    assert second_join.status_code == 200, second_join.text

    return {
        "home_id": owner_home["home_id"],
        "user": owner_home["owner"],
        "session_id": owner_home["owner"]["access_token"],
        "headers": owner_home["owner"]["headers"],
        "oldest_member": oldest_member["user"],
        "oldest_member_ctx": oldest_member,
        "newer_member": newer_member["user"],
        "newer_member_ctx": newer_member,
    }


@pytest.fixture
def home_capacity_setup(client, owner_home, make_user):
    members = []
    # owner + 9 members = 10 total
    for idx in range(1, 10):
        member = make_user(username=f"cap{idx:02d}", email=f"cap{idx:02d}@example.com")
        join = client.post(
            "/home/join",
            json={"invite_code": owner_home["invite_code"]},
            headers=member["headers"],
        )
        assert join.status_code == 200, join.text
        members.append(member)
    return {
        "home_id": owner_home["home_id"],
        "invite_code": owner_home["invite_code"],
        "owner": owner_home["owner"],
        "members": members,
    }


def parse_member_roles(home_payload: dict) -> dict[str, str]:
    return {member["username"]: member["role"] for member in home_payload.get("members", [])}
