from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class BalanceResponse(BaseModel):
    balance: Decimal
    total_earned: Decimal
    total_spent: Decimal
    total_fees_paid: Decimal
    currency: str
    pending_escrows: Decimal = Decimal("0")

    model_config = {"from_attributes": True}


class TopupRequest(BaseModel):
    amount: Decimal


class TopupResponse(BaseModel):
    razorpay_order_id: str
    amount: Decimal
    currency: str


class TransactionResponse(BaseModel):
    id: UUID
    from_account_id: Optional[UUID] = None
    to_account_id: Optional[UUID] = None
    type: str
    amount: Decimal
    currency: str
    task_id: Optional[UUID] = None
    status: str
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
