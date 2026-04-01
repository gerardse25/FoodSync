
import importlib
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def app_modules(tmp_path, monkeypatch):
    """
    Carrega el backend ORIGINAL sense editar-ne els fitxers.

    Per poder-lo provar amb SQLite durant els tests, fem dues adaptacions
    només al runtime de testing:
    - injectem un mòdul app.config temporal amb DATABASE_URL de SQLite
    - fem que el tipus PostgreSQL UUID sigui portable a SQLite
    """
    db_file = tmp_path / "test_auth.sqlite3"

    # Esborrem imports previs del paquet app perquè la configuració es recarregui neta.
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    # Importem el paquet buit app i hi injectem una configuració de test.
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
    app_pkg.config = config_mod

    # Ajustos de compatibilitat per executar el backend original sobre SQLite.
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
    auth = importlib.import_module("app.auth")
    routes = importlib.import_module("app.routes")
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
        "models": models,
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
        test_client.db_session_factory = app_modules["database"].SessionLocal
        test_client.app_modules = app_modules
        yield test_client


@pytest.fixture
def unsafe_client(app_modules):
    """Client que converteix excepcions no controlades del backend en resposta HTTP 500."""
    with TestClient(app_modules["app"], raise_server_exceptions=False) as test_client:
        test_client.app_modules = app_modules
        yield test_client


@pytest.fixture
def registered_user(client):
    payload = {
        "username": "validuser",
        "email": "user@example.com",
        "password": "Passw0rd",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "payload": payload,
        "response": body,
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "user": body["user"],
    }


@pytest.fixture
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


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
