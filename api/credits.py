from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from decimal import Decimal

from db import get_db
from models.user import User
from models.credit import CreditAccount, Transaction, Escrow
from schemas.credit import BalanceResponse, TopupRequest, TopupResponse, TransactionResponse
from schemas.common import CursorPage
from utils.errors import NotFoundError
from utils.pagination import encode_cursor, decode_cursor
from api.deps import get_current_user

router = APIRouter(prefix="/v1/credits", tags=["credits"])


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = (await db.execute(select(CreditAccount).where(CreditAccount.user_id == user.id))).scalar_one_or_none()
    if not account:
        raise NotFoundError("Credit account not found")

    pending = (await db.execute(
        select(func.coalesce(func.sum(Escrow.amount + Escrow.platform_fee), 0))
        .where(Escrow.payer_account_id == account.id, Escrow.status == "held")
    )).scalar()

    return BalanceResponse(
        balance=account.balance, total_earned=account.total_earned,
        total_spent=account.total_spent, total_fees_paid=account.total_fees_paid,
        currency=account.currency, pending_escrows=Decimal(str(pending)),
    )


@router.post("/topup", response_model=TopupResponse)
async def topup(data: TopupRequest, user: User = Depends(get_current_user)):
    # Stub: would create Razorpay order here
    return TopupResponse(razorpay_order_id="order_stub_" + str(user.id)[:8], amount=data.amount, currency="credits")


@router.get("/transactions", response_model=CursorPage[TransactionResponse])
async def list_transactions(
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = (await db.execute(select(CreditAccount).where(CreditAccount.user_id == user.id))).scalar_one_or_none()
    if not account:
        raise NotFoundError("Credit account not found")

    query = select(Transaction).where(
        (Transaction.from_account_id == account.id) | (Transaction.to_account_id == account.id)
    ).order_by(Transaction.created_at.desc())

    if cursor:
        from uuid import UUID
        query = query.where(Transaction.id < UUID(decode_cursor(cursor)))

    query = query.limit(limit + 1)
    result = (await db.execute(query)).scalars().all()

    has_more = len(result) > limit
    items = result[:limit]
    next_cursor = encode_cursor(str(items[-1].id)) if has_more and items else None

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
