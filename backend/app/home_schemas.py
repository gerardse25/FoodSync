from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateHomeSchema(BaseModel):
    """Dades per crear una nova llar."""

    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2 or len(value) > 64:
            raise ValueError("El nom de la llar ha de tenir entre 2 i 64 caràcters")
        return value


class JoinHomeSchema(BaseModel):
    """Dades per unir-se a una llar via codi d'invitació."""

    invite_code: str

    @field_validator("invite_code")
    @classmethod
    def validate_invite_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("El codi d'invitació no pot estar buit")
        return value


class KickMemberSchema(BaseModel):
    """Dades per expulsar un membre (només propietari)."""

    user_id: UUID


# ── Response schemas ──────────────────────────────────────────────────────────

class MemberResponse(BaseModel):
    """Informació pública d'un membre de la llar."""

    user_id: str
    username: str
    role: str
    joined_at: str


class HomeResponse(BaseModel):
    """Informació de la llar retornada als membres."""

    id: str
    name: str
    owner_id: str
    invite_code: Optional[str]   # None si l'usuari no és propietari
    member_count: int
    created_at: str


class HomeDetailResponse(HomeResponse):
    """Informació de la llar amb llista de membres."""

    members: list[MemberResponse]
