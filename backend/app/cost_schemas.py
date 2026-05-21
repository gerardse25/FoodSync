from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CostSeriesPoint(BaseModel):
    period: str
    start_date: date
    end_date: date
    total: str
    item_count: int


class CostSummaryResponse(BaseModel):
    code: str = "COST_SUMMARY"
    period: str
    date_from: Optional[date] = None
    date_to: date
    total: str
    item_count: int
    series: List[CostSeriesPoint]


class CostMemberShare(BaseModel):
    user_id: str

    # Despeses originals
    should_pay: str
    paid: str

    # Pagaments ja marcats com “Està pagat!”
    settled_paid: str
    settled_received: str

    # Saldo pendent després de restar liquidacions.
    # Positiu = ha de rebre diners.
    # Negatiu = ha de pagar diners.
    balance: str


class CostTransfer(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: str


class CostSplitResponse(BaseModel):
    code: str = "COST_SPLIT"
    date_from: Optional[date] = None
    date_to: date
    total: str
    members: List[CostMemberShare] = Field(default_factory=list)
    transfers: List[CostTransfer] = Field(default_factory=list)


class CreateCostSettlementRequest(BaseModel):
    from_user_id: UUID
    to_user_id: UUID
    amount: str
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class CostSettlementItem(BaseModel):
    id: int
    from_user_id: str
    to_user_id: str
    amount: str
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    paid_at: datetime


class CreateCostSettlementResponse(BaseModel):
    code: str = "COST_SETTLEMENT_CREATED"
    missatge: str
    settlement: CostSettlementItem
    split: CostSplitResponse