from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.home_models import Home, HomeMembership
from app.inventory_models import CatalogProduct, InventoryProduct, InventoryProductOwner
from app.models import User
from app.notification_models import Notification, NotificationPreference

NOTIFICATION_TYPE_EXPIRED = "EXPIRED"
NOTIFICATION_TYPE_EXPIRING_SOON = "EXPIRING_SOON"
NOTIFICATION_TYPE_HOME_MEMBER_JOINED = "HOME_MEMBER_JOINED"
NOTIFICATION_TYPE_HOME_PRODUCT_ADDED = "HOME_PRODUCT_ADDED"
DEFAULT_EXPIRATION_NOTICE_DAYS = 3


@dataclass(frozen=True)
class NotificationCandidate:
    user_id: object
    product: InventoryProduct
    product_name: str
    notification_type: str


def get_or_create_preferences(
    db: Session,
    user_id,
) -> NotificationPreference:
    preferences = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )

    if preferences:
        return preferences

    preferences = NotificationPreference(
        user_id=user_id,
        notifications_enabled=True,
        expiration_notice_days=DEFAULT_EXPIRATION_NOTICE_DAYS,
    )
    db.add(preferences)
    db.flush()
    return preferences


def _active_recipients_for_home(db: Session, home_id) -> list[tuple[User, int]]:
    rows = (
        db.query(User, NotificationPreference)
        .join(
            HomeMembership,
            and_(
                HomeMembership.user_id == User.id,
                HomeMembership.home_id == home_id,
                HomeMembership.is_active.is_(True),
            ),
        )
        .outerjoin(NotificationPreference, NotificationPreference.user_id == User.id)
        .filter(User.is_active.is_(True))
        .filter(
            or_(
                NotificationPreference.user_id.is_(None),
                NotificationPreference.notifications_enabled.is_(True),
            )
        )
        .all()
    )

    recipients = []
    for user, preferences in rows:
        notice_days = (
            preferences.expiration_notice_days
            if preferences is not None
            else DEFAULT_EXPIRATION_NOTICE_DAYS
        )
        recipients.append((user, notice_days))

    return recipients


def _active_users_for_home(db: Session, home_id) -> list[User]:
    rows = (
        db.query(User)
        .join(
            HomeMembership,
            and_(
                HomeMembership.user_id == User.id,
                HomeMembership.home_id == home_id,
                HomeMembership.is_active.is_(True),
            ),
        )
        .filter(User.is_active.is_(True))
        .all()
    )

    return rows


def _add_notification_if_missing(
    db: Session,
    *,
    user_id,
    notification_type: str,
    title: str,
    message: str,
    event_key: str,
    inventory_product_id: int | None = None,
) -> bool:
    exists = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.tipus == notification_type,
            Notification.event_key == event_key,
        )
        .first()
    )

    if exists:
        return False

    db.add(
        Notification(
            user_id=user_id,
            id_inventari=inventory_product_id,
            tipus=notification_type,
            event_key=event_key,
            title=title,
            message=message,
            delivery_channel="in_app",
            delivery_status="pending",
        )
    )
    return True


def _remove_member_joined_notifications_for_home(db: Session, home_id) -> None:
    active_member_count = (
        db.query(HomeMembership)
        .filter(
            HomeMembership.home_id == home_id,
            HomeMembership.is_active.is_(True),
        )
        .count()
    )
    if active_member_count <= 3:
        return

    event_prefix = f"home_member_joined:{home_id}:"
    latest_join_notification = (
        db.query(Notification)
        .filter(
            Notification.tipus == NOTIFICATION_TYPE_HOME_MEMBER_JOINED,
            Notification.event_key.like(f"{event_prefix}%"),
        )
        .order_by(Notification.created_at.desc())
        .first()
    )
    if latest_join_notification is None:
        return

    db.query(Notification).filter(
        Notification.tipus == NOTIFICATION_TYPE_HOME_MEMBER_JOINED,
        Notification.event_key == latest_join_notification.event_key,
    ).delete(synchronize_session=False)


def notify_home_member_joined(
    db: Session,
    *,
    home_id,
    joined_user: User,
    joined_at,
) -> int:
    event_key = (
        f"home_member_joined:{home_id}:" f"{joined_user.id}:{joined_at.isoformat()}"
    )
    title = "Nou membre a la llar"
    message = f"{joined_user.username} s'ha unit a la llar."

    created_count = 0
    for recipient in _active_users_for_home(db, home_id):
        if recipient.id == joined_user.id:
            continue

        if _add_notification_if_missing(
            db,
            user_id=recipient.id,
            notification_type=NOTIFICATION_TYPE_HOME_MEMBER_JOINED,
            title=title,
            message=message,
            event_key=event_key,
        ):
            created_count += 1

    return created_count


def notify_home_product_added(
    db: Session,
    *,
    home_id,
    inventory_product: InventoryProduct,
    product_name: str,
    added_by: User,
) -> int:
    event_key = f"home_product_added:{inventory_product.id_inventari}"
    title = "Nou producte a l'inventari"
    message = f"{added_by.username} ha afegit {product_name} a l'inventari."

    created_count = 0
    _remove_member_joined_notifications_for_home(db, home_id)

    if inventory_product.es_privat:
        recipients = (
            db.query(User)
            .join(InventoryProductOwner, InventoryProductOwner.user_id == User.id)
            .join(
                HomeMembership,
                and_(
                    HomeMembership.user_id == User.id,
                    HomeMembership.home_id == home_id,
                    HomeMembership.is_active.is_(True),
                ),
            )
            .filter(
                InventoryProductOwner.id_inventari == inventory_product.id_inventari,
                User.is_active.is_(True),
            )
            .all()
        )
    else:
        recipients = _active_users_for_home(db, home_id)

    for recipient in recipients:
        if recipient.id == added_by.id:
            continue

        if _add_notification_if_missing(
            db,
            user_id=recipient.id,
            notification_type=NOTIFICATION_TYPE_HOME_PRODUCT_ADDED,
            title=title,
            message=message,
            event_key=event_key,
            inventory_product_id=inventory_product.id_inventari,
        ):
            created_count += 1

    return created_count


def _owner_ids_by_product(db: Session, product_ids: Iterable[int]) -> dict[int, set]:
    product_ids = list(product_ids)
    if not product_ids:
        return {}

    rows = (
        db.query(InventoryProductOwner)
        .filter(InventoryProductOwner.id_inventari.in_(product_ids))
        .all()
    )

    owners: dict[int, set] = {}
    for row in rows:
        owners.setdefault(row.id_inventari, set()).add(row.user_id)

    return owners


def _notification_type_for(
    expiration_date: date,
    today: date,
    notice_days: int,
) -> str | None:
    if expiration_date < today:
        return NOTIFICATION_TYPE_EXPIRED

    if today <= expiration_date <= today + timedelta(days=notice_days):
        return NOTIFICATION_TYPE_EXPIRING_SOON

    return None


def _build_notification(candidate: NotificationCandidate) -> Notification:
    product = candidate.product

    if candidate.notification_type == NOTIFICATION_TYPE_EXPIRED:
        title = "Producte caducat"
        message = f"{candidate.product_name} ja ha caducat."
    else:
        title = "Producte pròxim a caducar"
        message = f"{candidate.product_name} caduca aviat."

    return Notification(
        user_id=candidate.user_id,
        id_inventari=product.id_inventari,
        tipus=candidate.notification_type,
        event_key=(
            f"expiration:{candidate.product.id_inventari}:"
            f"{candidate.notification_type}"
        ),
        title=title,
        message=message,
        delivery_channel="in_app",
        delivery_status="pending",
    )


def scan_expiration_notifications(
    db: Session,
    *,
    home_id=None,
    today: date | None = None,
) -> int:
    today = today or date.today()

    home_query = db.query(Home).filter(Home.is_active.is_(True))
    if home_id is not None:
        home_query = home_query.filter(Home.id == home_id)

    created_count = 0

    for home in home_query.all():
        recipients = _active_recipients_for_home(db, home.id)
        if not recipients:
            continue

        max_notice_days = max(notice_days for _, notice_days in recipients)
        max_expiration_date = today + timedelta(days=max_notice_days)

        product_rows = (
            db.query(InventoryProduct, CatalogProduct)
            .join(
                CatalogProduct,
                InventoryProduct.id_producte_cataleg
                == CatalogProduct.id_producte_cataleg,
            )
            .filter(
                InventoryProduct.id_llar == home.id,
                InventoryProduct.data_caducitat.isnot(None),
                InventoryProduct.data_caducitat <= max_expiration_date,
            )
            .all()
        )

        owner_ids = _owner_ids_by_product(
            db,
            [product.id_inventari for product, _ in product_rows],
        )

        candidates: list[NotificationCandidate] = []
        for product, catalog_product in product_rows:
            product_owner_ids = owner_ids.get(product.id_inventari, set())

            for user, notice_days in recipients:
                if product_owner_ids and user.id not in product_owner_ids:
                    continue

                notification_type = _notification_type_for(
                    product.data_caducitat,
                    today,
                    notice_days,
                )
                if notification_type is None:
                    continue

                candidates.append(
                    NotificationCandidate(
                        user_id=user.id,
                        product=product,
                        product_name=catalog_product.nom,
                        notification_type=notification_type,
                    )
                )

        if not candidates:
            continue

        existing_rows = (
            db.query(
                Notification.user_id, Notification.id_inventari, Notification.tipus
            )
            .filter(
                Notification.id_inventari.in_(
                    [candidate.product.id_inventari for candidate in candidates]
                )
            )
            .all()
        )
        existing_keys = {
            (row.user_id, row.id_inventari, row.tipus) for row in existing_rows
        }

        for candidate in candidates:
            key = (
                candidate.user_id,
                candidate.product.id_inventari,
                candidate.notification_type,
            )
            if key in existing_keys:
                continue

            db.add(_build_notification(candidate))
            existing_keys.add(key)
            created_count += 1

    db.commit()
    return created_count
