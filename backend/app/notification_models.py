import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    expiration_notice_days = Column(Integer, default=3, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "id_inventari",
            "tipus",
            name="uq_notification_user_product_type",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_inventari = Column(
        Integer,
        ForeignKey("productes_inventari.id_inventari", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipus = Column(String(32), nullable=False)
    title = Column(String(120), nullable=False)
    message = Column(String(255), nullable=False)
    delivery_channel = Column(String(32), default="in_app", nullable=False)
    delivery_status = Column(String(32), default="pending", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)
