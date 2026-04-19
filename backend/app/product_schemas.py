from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CreateManualProductSchema(BaseModel):
    name: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None
    owner_user_id: Optional[UUID] = None


class ProductResponse(BaseModel):
    id: str
    home_id: str
    created_by_user_id: str
    owner_user_id: Optional[str]
    is_private: bool
    name: str
    category: str
    price: str
    quantity: int
    purchase_date: Optional[str]
    expiration_date: Optional[str]
    created_at: str
