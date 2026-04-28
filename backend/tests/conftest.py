import importlib
import sys
import types
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _optional_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None


@pytest.fixture
def app_modules(tmp_path, monkeypatch):
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
    attr_name = "config"
    setattr(app_pkg, attr_name, config_mod)

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

    # Módulos opcionales según la rama
    product_models = _optional_import("app.product_models")
    product_routes = _optional_import("app.product_routes")
    product_schemas = _optional_import("app.product_schemas")

    inventory_models = _optional_import("app.inventory_models")
    inventory_routes = _optional_import("app.inventory_routes")
    inventory_schemas = _optional_import("app.inventory_schemas")
    inventory_modify = _optional_import("app.inventory_modify")
    inventory_delete_product = _optional_import("app.inventory_delete_product")

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
        "product_models": product_models,
        "product_routes": product_routes,
        "product_schemas": product_schemas,
        "inventory_models": inventory_models,
        "inventory_routes": inventory_routes,
        "inventory_schemas": inventory_schemas,
        "inventory_modify": inventory_modify,
        "inventory_delete_product": inventory_delete_product,
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


def _normalize_owner_fields(owner_ids):
    owner_ids = owner_ids or []
    normalized_ids = [str(owner_id) for owner_id in owner_ids]

    if len(normalized_ids) == 1:
        single_owner = normalized_ids[0]
    else:
        single_owner = None

    return {
        "owner_user_ids": normalized_ids,
        "owner_user_id": single_owner,
        "owner": single_owner,
        "is_private": bool(normalized_ids),
    }

@pytest.fixture
def make_product_data():
    created = []

    def _make_product_data(
        *,
        name: str | None = None,
        price: Decimal | float | str = Decimal("1.00"),
        category: str = "general",
        quantity: int = 1,
        purchase_date: date | None = None,
        expiration_date: date | None = None,
        owner_user_ids: list[str | uuid.UUID] | None = None,
    ):
        idx = len(created) + 1
        product_name = name or f"Product{idx:02d}"

        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        price_srt = str(price)

        owner_data = _normalize_owner_fields(owner_user_ids)

        data = {
            "name": product_name,
            "price": price_srt,
            "category": category,
            "quantity": quantity,
            "purchase_date": purchase_date,
            "expiration_date": expiration_date,
            **owner_data,
        }
        created.append(data)
        return data

    return _make_product_data


@pytest.fixture
def seed_product_db(client):
    SessionLocal = client.db_session_factory
    app_modules = client.app_modules

    def _seed_product_db(
        *,
        home_id: str | uuid.UUID,
        created_by_ctx: dict,
        name: str,
        category: str = "general",
        quantity: int = 1,
        price: Decimal | float | str = Decimal("1.00"),
        purchase_date: date | None = None,
        expiration_date: date | None = None,
        owner_user_ids: list[str | uuid.UUID] | None = None,
    ):
        db = SessionLocal()
        try:
            home_uuid = uuid.UUID(str(home_id)) if not isinstance(home_id, uuid.UUID) else home_id
            creator_uuid = uuid.UUID(created_by_ctx["user"]["id"])

            owner_uuids = []
            if owner_user_ids:
                owner_uuids = [
                    owner_id if isinstance(owner_id, uuid.UUID) else uuid.UUID(str(owner_id))
                    for owner_id in owner_user_ids
                ]

            if not isinstance(price, Decimal):
                price = Decimal(str(price))

            # Rama con product_models (owner único)
            product_models = app_modules["product_models"]
            if product_models is not None:
                Product = product_models.Product
                single_owner_uuid = owner_uuids[0] if owner_uuids else None

                product = Product(
                    home_id=home_uuid,
                    created_by_user_id=creator_uuid,
                    owner_user_id=single_owner_uuid,
                    name=name,
                    category=category,
                    price=price,
                    quantity=quantity,
                    purchase_date=purchase_date,
                    expiration_date=expiration_date,
                )
                db.add(product)
                db.commit()
                db.refresh(product)

                return {
                    "id": str(product.id),
                    "home_id": str(product.home_id),
                    "name": product.name,
                    "category": product.category,
                    "quantity": product.quantity,
                    "price": str(product.price),
                    "purchase_date": product.purchase_date.isoformat() if product.purchase_date else None,
                    "expiration_date": product.expiration_date.isoformat() if product.expiration_date else None,
                    **_normalize_owner_fields([product.owner_user_id] if product.owner_user_id else []),
                }

            # Ramas con inventory_models (owners múltiples)
            inventory_models = app_modules["inventory_models"]
            if inventory_models is None:
                raise RuntimeError("La rama no tiene ni product_models ni inventory_models")

            Category = inventory_models.Category
            CatalogProduct = inventory_models.CatalogProduct
            InventoryProduct = inventory_models.InventoryProduct
            InventoryProductOwner = getattr(inventory_models, "InventoryProductOwner", None)

            category_row = db.query(Category).filter(Category.nom == category).first()
            if not category_row:
                category_row = Category(nom=category)
                db.add(category_row)
                db.commit()
                db.refresh(category_row)

            catalog_product = CatalogProduct(
                nom=name,
                id_categoria=category_row.id_categoria,
            )
            db.add(catalog_product)
            db.commit()
            db.refresh(catalog_product)

            inv_product = InventoryProduct(
                id_llar=home_uuid,
                id_producte_cataleg=catalog_product.id_producte_cataleg,
                quantitat=quantity,
                data_caducitat=expiration_date,
            )

            if hasattr(inv_product, "preu"):
                inv_product.preu = price
            if hasattr(inv_product, "data_compra"):
                inv_product.data_compra = purchase_date
            if hasattr(inv_product, "metode_registre"):
                inv_product.metode_registre = "manual"

            db.add(inv_product)
            db.commit()
            db.refresh(inv_product)

            if InventoryProductOwner is not None:
                for owner_uuid in owner_uuids:
                    db.add(
                        InventoryProductOwner(
                            id_inventari=inv_product.id_inventari,
                            user_id=owner_uuid,
                        )
                    )
                db.commit()

            return {
                "id": str(inv_product.id_inventari),
                "home_id": str(inv_product.id_llar),
                "name": catalog_product.nom,
                "category": category_row.nom,
                "quantity": inv_product.quantitat,
                "price": str(price),
                "purchase_date": purchase_date.isoformat() if purchase_date else None,
                "expiration_date": inv_product.data_caducitat.isoformat() if inv_product.data_caducitat else None,
                **_normalize_owner_fields(owner_uuids),
            }
        finally:
            db.close()

    return _seed_product_db


@pytest.fixture
def list_home_products_db(client):
    SessionLocal = client.db_session_factory
    app_modules = client.app_modules

    def _list_home_products_db(home_id: str | uuid.UUID):
        db = SessionLocal()
        try:
            home_uuid = uuid.UUID(str(home_id)) if not isinstance(home_id, uuid.UUID) else home_id

            # Rama con product_models (owner único)
            if app_modules["product_models"] is not None:
                Product = app_modules["product_models"].Product
                rows = db.query(Product).filter(Product.home_id == home_uuid, Product.is_active.is_(True)).all()

                return [
                    {
                        "id": str(row.id),
                        "home_id": str(row.home_id),
                        "name": row.name,
                        "category": row.category,
                        "quantity": row.quantity,
                        "price": str(row.price),
                        "purchase_date": row.purchase_date.isoformat() if row.purchase_date else None,
                        "expiration_date": row.expiration_date.isoformat() if row.expiration_date else None,
                        **_normalize_owner_fields([row.owner_user_id] if row.owner_user_id else []),
                    }
                    for row in rows
                ]

            # Rama con inventory_models (owners múltiples)
            inventory_models = app_modules["inventory_models"]
            Category = inventory_models.Category
            CatalogProduct = inventory_models.CatalogProduct
            InventoryProduct = inventory_models.InventoryProduct
            InventoryProductOwner = getattr(inventory_models, "InventoryProductOwner", None)

            rows = (
                db.query(InventoryProduct, CatalogProduct, Category)
                .join(CatalogProduct, InventoryProduct.id_producte_cataleg == CatalogProduct.id_producte_cataleg)
                .outerjoin(Category, CatalogProduct.id_categoria == Category.id_categoria)
                .filter(InventoryProduct.id_llar == home_uuid)
                .all()
            )

            products = []
            for inv_row, catalog_row, category_row in rows:
                owner_user_ids = []

                if InventoryProductOwner is not None:
                    owner_rows = (
                        db.query(InventoryProductOwner)
                        .filter(InventoryProductOwner.id_inventari == inv_row.id_inventari)
                        .all()
                    )
                    owner_user_ids = [owner_row.user_id for owner_row in owner_rows]

                products.append(
                    {
                        "id": str(inv_row.id_inventari),
                        "home_id": str(inv_row.id_llar),
                        "name": catalog_row.nom,
                        "category": category_row.nom if category_row else None,
                        "quantity": inv_row.quantitat,
                        "price": str(inv_row.preu) if hasattr(inv_row, "preu") and inv_row.preu is not None else None,
                        "purchase_date": inv_row.data_compra.isoformat() if hasattr(inv_row, "data_compra") and inv_row.data_compra else None,
                        "expiration_date": inv_row.data_caducitat.isoformat() if inv_row.data_caducitat else None,
                        **_normalize_owner_fields(owner_user_ids),
                    }
                )

            return products
        finally:
            db.close()

    return _list_home_products_db


@pytest.fixture
def shared_home_with_products(shared_home_setup, make_product_data, seed_product_db):
    owner = shared_home_setup["owner"]
    member1 = shared_home_setup["member1"]
    member2 = shared_home_setup["member2"]

    owner_private_payload = make_product_data(
        name="owner_private_product",
        category="RICE",
        quantity=1,
        owner_user_ids=[owner["user"]["id"]],
    )
    owner_private = seed_product_db(
        home_id=shared_home_setup["home_id"],
        created_by_ctx=owner,
        **{ 
            k: v
            for k, v in owner_private_payload.items()
            if k not in {"is_private", "owner_user_id", "owner"}
        }
    )

    member1_private_payload = make_product_data(
    name="member1_private_product",
    category="HARD_CHEESE",
    quantity=5,
    owner_user_ids=[member1["user"]["id"]],
    )
    member1_private = seed_product_db(
        home_id=shared_home_setup["home_id"],
        created_by_ctx=member1,
        **{ 
            k: v
            for k, v in member1_private_payload.items()
            if k not in {"is_private", "owner_user_id", "owner"}
        }
    )

    public_payload = make_product_data(
    name="shared_public_product",
    category="FRESH_VEGETABLES",
    quantity=3,
    owner_user_ids=[],
    )
    public_product = seed_product_db(
        home_id=shared_home_setup["home_id"],
        created_by_ctx=owner,
        **{ 
            k: v
            for k, v in public_payload.items()
            if k not in {"is_private", "owner_user_id", "owner"}
        }
    )

    return {
        "home_id": shared_home_setup["home_id"],
        "invite_code": shared_home_setup["invite_code"],
        "owner": owner,
        "owner_headers": shared_home_setup["owner_headers"],
        "member1": member1,
        "member1_headers": shared_home_setup["member1_headers"],
        "member2": member2,
        "member2_headers": shared_home_setup["member2_headers"],
        "products": {
            "owner_private": {"payload": owner_private_payload, "db": owner_private},
            "member1_private": {"payload": member1_private_payload, "db": member1_private},
            "public_product": {"payload": public_payload, "db": public_product},
        },
    }


@pytest.fixture
def shared_home_with_single_product(shared_home_setup, make_product_data, seed_product_db):
    owner = shared_home_setup["owner"]

    only_payload = make_product_data(
    name="only_product",
    category="MILK",
    quantity=1,
    owner_user_ids=[],
    )
    only_product = seed_product_db(
        home_id=shared_home_setup["home_id"],
        created_by_ctx=owner,
        **{ 
            k: v
            for k, v in only_payload.items()
            if k not in {"is_private", "owner_user_id", "owner"}
        }
    )

    return {
        "home_id": shared_home_setup["home_id"],
        "invite_code": shared_home_setup["invite_code"],
        "owner": shared_home_setup["owner"],
        "owner_headers": shared_home_setup["owner_headers"],
        "member1": shared_home_setup["member1"],
        "member1_headers": shared_home_setup["member1_headers"],
        "member2": shared_home_setup["member2"],
        "member2_headers": shared_home_setup["member2_headers"],
        "products": {
            "only_product": {"payload": only_payload, "db": only_product},
        },
    }