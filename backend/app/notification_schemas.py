from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class NotificationPreferenceUpdate(BaseModel):
    notifications_enabled: bool
    expiration_notice_days: int


class NotificationPreferenceItem(BaseModel):
    notifications_enabled: bool
    expiration_notice_days: int


class NotificationPreferenceResponse(BaseModel):
    code: str
    message: str
    preferences: NotificationPreferenceItem


class NotificationItem(BaseModel):
    id: str
    tipus: str
    id_producte: str
    nom_producte: str
    data_caducitat: Optional[date] = None
    title: str
    message: str
    delivery_channel: str
    delivery_status: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    code: str
    message: str
    notifications: List[NotificationItem]


class NotificationScanResponse(BaseModel):
    code: str
    message: str
    created_count: int
