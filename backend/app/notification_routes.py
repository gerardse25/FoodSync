from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import app.auth
from app.database import get_db
from app.home_models import HomeMembership
from app.inventory_models import CatalogProduct, InventoryProduct
from app.notification_models import Notification
from app.notification_schemas import NotificationPreferenceUpdate
from app.notification_service import (
    get_or_create_preferences,
    scan_expiration_notifications,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _active_membership(user_id, db: Session):
    return (
        db.query(HomeMembership)
        .filter(
            HomeMembership.user_id == user_id,
            HomeMembership.is_active.is_(True),
        )
        .first()
    )


def _not_in_home_response():
    return JSONResponse(
        status_code=403,
        content={
            "code": "NOT_IN_HOME",
            "message": "L'usuari no pertany a cap llar activa.",
        },
    )


@router.get("/preferences")
def get_notification_preferences(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current
    preferences = get_or_create_preferences(db, user.id)
    db.commit()

    return {
        "code": "NOTIFICATION_PREFERENCES_RETRIEVED",
        "message": "Preferències de notificacions obtingudes correctament.",
        "preferences": {
            "notifications_enabled": preferences.notifications_enabled,
            "expiration_notice_days": preferences.expiration_notice_days,
        },
    }


@router.patch("/preferences")
def update_notification_preferences(
    data: NotificationPreferenceUpdate,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    if data.expiration_notice_days < 0 or data.expiration_notice_days > 30:
        return JSONResponse(
            status_code=422,
            content={
                "code": "NOTIFICATION_PREFERENCES_INVALID",
                "message": "Els dies d'avís han d'estar entre 0 i 30.",
            },
        )

    user, _session = current
    preferences = get_or_create_preferences(db, user.id)
    preferences.notifications_enabled = data.notifications_enabled
    preferences.expiration_notice_days = data.expiration_notice_days
    db.commit()
    db.refresh(preferences)

    return {
        "code": "NOTIFICATION_PREFERENCES_UPDATED",
        "message": "Preferències de notificacions actualitzades correctament.",
        "preferences": {
            "notifications_enabled": preferences.notifications_enabled,
            "expiration_notice_days": preferences.expiration_notice_days,
        },
    }


@router.post("/scan")
def scan_current_home_notifications(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current
    membership = _active_membership(user.id, db)
    if not membership:
        return _not_in_home_response()

    created_count = scan_expiration_notifications(db, home_id=membership.home_id)

    return {
        "code": "NOTIFICATIONS_SCAN_COMPLETED",
        "message": "Revisió de caducitats completada correctament.",
        "created_count": created_count,
    }


@router.get("")
def list_notifications(
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    rows = (
        db.query(Notification, InventoryProduct, CatalogProduct)
        .outerjoin(
            InventoryProduct,
            Notification.id_inventari == InventoryProduct.id_inventari,
        )
        .outerjoin(
            CatalogProduct,
            InventoryProduct.id_producte_cataleg == CatalogProduct.id_producte_cataleg,
        )
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    return {
        "code": "NOTIFICATIONS_RETRIEVED",
        "message": "Notificacions obtingudes correctament.",
        "notifications": [
            {
                "id": str(notification.id),
                "tipus": notification.tipus,
                "id_producte": str(product.id_inventari) if product else None,
                "nom_producte": catalog_product.nom if catalog_product else None,
                "data_caducitat": (
                    product.data_caducitat.isoformat()
                    if product and product.data_caducitat
                    else None
                ),
                "title": notification.title,
                "message": notification.message,
                "delivery_channel": notification.delivery_channel,
                "delivery_status": notification.delivery_status,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            }
            for notification, product, catalog_product in rows
        ],
    }


@router.patch("/{notification_id}/read")
def mark_notification_as_read(
    notification_id: str,
    current=Depends(app.auth.get_current_user),
    db: Session = Depends(get_db),
):
    user, _session = current

    try:
        notification_uuid = UUID(notification_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "code": "NOTIFICATION_ID_INVALID",
                "message": "L'ID de la notificació no té un format vàlid.",
            },
        )

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_uuid, Notification.user_id == user.id)
        .first()
    )

    if not notification:
        return JSONResponse(
            status_code=404,
            content={
                "code": "NOTIFICATION_NOT_FOUND",
                "message": "La notificació no s'ha trobat.",
            },
        )

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {
        "code": "NOTIFICATION_MARKED_AS_READ",
        "message": "Notificació marcada com a llegida correctament.",
    }
