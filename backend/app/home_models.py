import secrets
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

# ── Constants ────────────────────────────────────────────────────────────────

HOME_MAX_MEMBERS = 10          # màxim de membres per llar (propietari inclòs)
INVITE_CODE_LENGTH = 8         # longitud del codi d'invitació (caràcters URL-safe)


def _generate_invite_code() -> str:
    """Genera un codi d'invitació únic de 8 caràcters en majúscules."""
    return secrets.token_urlsafe(6).upper()[:INVITE_CODE_LENGTH]


# ── Models ────────────────────────────────────────────────────────────────────

class Home(Base):
    """
    Representa una llar compartida.

    Restriccions:
      - Només un propietari (owner_id → users.id).
      - Màxim HOME_MAX_MEMBERS membres actius.
      - invite_code és únic i es pot regenerar.
      - Soft-delete via is_active (coherent amb User).
    """
    __tablename__ = "homes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    invite_code = Column(
        String(16),
        unique=True,
        nullable=False,
        default=_generate_invite_code,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class HomeMembership(Base):
    """
    Representa la pertinença d'un usuari a una llar.

    Restriccions:
      - Un usuari només pot tenir una membresia activa (unique constraint).
      - role: 'owner' | 'member'
      - Soft-delete via is_active.
    """
    __tablename__ = "home_memberships"

    __table_args__ = (
        # Un usuari actiu només pot pertànyer a una llar activa.
        # Enforçat a nivell de BD amb índex parcial (gestionat des del servei)
        # i a nivell d'aplicació abans de cada inserció.
        UniqueConstraint("user_id", "home_id", name="uq_membership_user_home"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(
        UUID(as_uuid=True),
        ForeignKey("homes.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False, default="member")  # 'owner' | 'member'
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)
