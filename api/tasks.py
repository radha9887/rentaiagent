from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
import json

from db import get_db
from models.user import User
from models.agent import Agent
from models.task import Task
from models.credit import Escrow
from schemas.task import TaskCreate, TaskResponse, TaskComplete
from schemas.common import CursorPage, MessageResponse
from utils.errors import NotFoundError, ForbiddenError, ValidationError as AppValidationError
from utils.pagination import encode_cursor, decode_cursor
from core.escrow import hold_credits, release_escrow, refund_escrow
from core.routing import route_task
from config import settings
from api.deps import get_current_user

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.id == data.provider_agent_id))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Provider agent not found")
    if agent.status != "online":
        raise AppValidationError("Provider agent is not online")

    quoted_price = agent.price_per_task
    payload_size = len(json.dumps(data.payload).encode()) if data.payload else 0

    task = Task(
        requester_user_id=user.id, requester_agent_id=data.requester_agent_id,
        provider_agent_id=data.provider_agent_id, skill_requested=data.skill_requested,
        description=data.description, payload=data.payload, payload_size_bytes=payload_size,
        max_wait_seconds=data.max_wait_seconds, priority=data.priority,
        quoted_price=quoted_price, currency=agent.currency, status="pending",
    )
    db.add(task)
    await db.flush()

    if quoted_price > 0:
        escrow = await hold_credits(db, user.id, quoted_price, task.id)
        task.status = "escrowed"
        task.escrowed_at = datetime.now(timezone.utc)
        task.platform_fee = escrow.platform_fee

    await route_task(db, task.id)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    if task.requester_user_id != user.id:
        agent = (await db.execute(select(Agent).where(Agent.id == task.provider_agent_id))).scalar_one_or_none()
        if not agent or agent.owner_id != user.id:
            raise ForbiddenError()
    return task


@router.get("", response_model=CursorPage[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task).where(Task.requester_user_id == user.id).order_by(Task.created_at.desc())
    if status:
        query = query.where(Task.status == status)
    if cursor:
        query = query.where(Task.id < UUID(decode_cursor(cursor)))
    query = query.limit(limit + 1)
    result = (await db.execute(query)).scalars().all()
    has_more = len(result) > limit
    items = result[:limit]
    next_cursor = encode_cursor(str(items[-1].id)) if has_more and items else None
    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post("/{task_id}/cancel", response_model=MessageResponse)
async def cancel_task(task_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    if task.requester_user_id != user.id:
        raise ForbiddenError()
    if task.status in ("completed", "failed", "cancelled"):
        raise AppValidationError("Task already finalized")

    escrow = (await db.execute(select(Escrow).where(Escrow.task_id == task_id, Escrow.status == "held"))).scalar_one_or_none()
    if escrow:
        await refund_escrow(db, escrow.id)

    task.status = "cancelled"
    task.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return MessageResponse(message="Task cancelled")


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: UUID, data: TaskComplete, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    # Only provider owner can complete
    agent = (await db.execute(select(Agent).where(Agent.id == task.provider_agent_id))).scalar_one_or_none()
    if not agent or agent.owner_id != user.id:
        raise ForbiddenError("Only provider can complete task")
    if task.status in ("completed", "failed", "cancelled"):
        raise AppValidationError("Task already finalized")

    task.result = data.result
    task.result_size_bytes = len(json.dumps(data.result).encode())
    task.actual_price = data.actual_price or task.quoted_price
    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)

    escrow = (await db.execute(select(Escrow).where(Escrow.task_id == task_id, Escrow.status == "held"))).scalar_one_or_none()
    if escrow:
        await release_escrow(db, escrow.id)

    await db.commit()
    await db.refresh(task)
    return task
