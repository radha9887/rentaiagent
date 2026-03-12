from decimal import Decimal
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.credit import CreditAccount, Escrow, Transaction
from config import settings
from utils.errors import InsufficientCreditsError, NotFoundError
import logging
logger = logging.getLogger(__name__)


async def hold_credits(db: AsyncSession, user_id: UUID, amount: Decimal, task_id: UUID) -> Escrow:
    """Atomic: deduct balance + create escrow."""
    platform_fee = amount * Decimal(str(settings.PLATFORM_FEE_PERCENT)) / Decimal("100")
    total = amount + platform_fee

    account = (await db.execute(select(CreditAccount).where(CreditAccount.user_id == user_id).with_for_update())).scalar_one_or_none()
    logger.info("hold_credits: user=%s amount=%s fee=%s total=%s account=%s balance=%s", user_id, amount, platform_fee, total, account.id if account else None, account.balance if account else None)
    if not account:
        raise NotFoundError("Credit account not found")
    if account.balance < total:
        logger.warning("Insufficient: balance=%s < total=%s", account.balance, total)
        raise InsufficientCreditsError()

    account.balance -= total
    account.total_spent += total

    escrow = Escrow(task_id=task_id, payer_account_id=account.id, amount=amount, platform_fee=platform_fee, status="held")
    db.add(escrow)

    tx = Transaction(from_account_id=account.id, type="escrow_hold", amount=total, task_id=task_id, description="Escrow hold for task")
    db.add(tx)

    await db.flush()
    return escrow


async def release_escrow(db: AsyncSession, escrow_id: UUID) -> None:
    """Atomic: credit provider + platform fee + update escrow."""
    escrow = (await db.execute(select(Escrow).where(Escrow.id == escrow_id).with_for_update())).scalar_one_or_none()
    if not escrow or escrow.status != "held":
        raise NotFoundError("Active escrow not found")

    # Find provider via task
    from models.task import Task
    from models.agent import Agent
    task = (await db.execute(select(Task).where(Task.id == escrow.task_id))).scalar_one()
    agent = (await db.execute(select(Agent).where(Agent.id == task.provider_agent_id))).scalar_one()
    provider_account = (await db.execute(select(CreditAccount).where(CreditAccount.user_id == agent.owner_id).with_for_update())).scalar_one()

    provider_account.balance += escrow.amount
    provider_account.total_earned += escrow.amount

    escrow.status = "released"
    escrow.released_at = datetime.now(timezone.utc)

    db.add(Transaction(to_account_id=provider_account.id, type="escrow_release", amount=escrow.amount, task_id=escrow.task_id, escrow_id=escrow.id, description="Escrow released to provider"))
    db.add(Transaction(type="fee", amount=escrow.platform_fee, task_id=escrow.task_id, escrow_id=escrow.id, description="Platform fee"))

    await db.flush()


async def refund_escrow(db: AsyncSession, escrow_id: UUID) -> None:
    """Atomic: refund to payer + update escrow."""
    escrow = (await db.execute(select(Escrow).where(Escrow.id == escrow_id).with_for_update())).scalar_one_or_none()
    if not escrow or escrow.status != "held":
        raise NotFoundError("Active escrow not found")

    account = (await db.execute(select(CreditAccount).where(CreditAccount.id == escrow.payer_account_id).with_for_update())).scalar_one()
    total = escrow.amount + escrow.platform_fee
    account.balance += total
    account.total_spent -= total

    escrow.status = "refunded"
    escrow.released_at = datetime.now(timezone.utc)

    db.add(Transaction(to_account_id=account.id, type="escrow_refund", amount=total, task_id=escrow.task_id, escrow_id=escrow.id, description="Escrow refunded"))
    await db.flush()
