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
from schemas.task import TaskCreate, TaskResponse, TaskComplete, AutoTaskCreate
from schemas.common import CursorPage, MessageResponse
from utils.errors import NotFoundError, ForbiddenError, ValidationError as AppValidationError
from utils.pagination import encode_cursor, decode_cursor
from core.escrow import hold_credits, release_escrow, refund_escrow
from core.routing import route_task
from config import settings
from api.deps import get_current_user

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.get("/feed")
async def public_task_feed(
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = None,
    skill: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Public feed of recent tasks — like a blockchain explorer."""
    from sqlalchemy import func as sqlfunc
    base_query = select(Task.id, Task.skill_requested, Task.status, Task.quoted_price, Task.platform_fee,
               Task.currency, Task.created_at, Task.completed_at, Task.provider_agent_id)
    count_query = select(sqlfunc.count(Task.id))

    if status:
        base_query = base_query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)
    if skill:
        base_query = base_query.where(Task.skill_requested.ilike(f"%{skill}%"))
        count_query = count_query.where(Task.skill_requested.ilike(f"%{skill}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = (await db.execute(
        base_query.order_by(Task.created_at.desc()).offset(offset).limit(limit)
    )).all()
    tasks = []
    # Get agent names in bulk
    agent_ids = list(set(r.provider_agent_id for r in result if r.provider_agent_id))
    agents_map = {}
    if agent_ids:
        agents = (await db.execute(select(Agent.id, Agent.name, Agent.slug).where(Agent.id.in_(agent_ids)))).all()
        agents_map = {a.id: {"name": a.name, "slug": a.slug} for a in agents}
    for r in result:
        agent_info = agents_map.get(r.provider_agent_id, {})
        duration = None
        if r.completed_at and r.created_at:
            duration = round((r.completed_at - r.created_at).total_seconds(), 1)
        tasks.append({
            "id": str(r.id),
            "skill": r.skill_requested,
            "status": r.status,
            "price": str(r.quoted_price),
            "fee": str(r.platform_fee) if r.platform_fee else "0",
            "currency": r.currency,
            "agent_name": agent_info.get("name", "Unknown"),
            "agent_slug": agent_info.get("slug", ""),
            "duration_s": duration,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"tasks": tasks, "total": total, "offset": offset, "limit": limit}


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import logging; logging.getLogger(__name__).warning("CREATE_TASK: user=%s email=%s agent=%s skill=%s", user.id, user.email, data.provider_agent_id, data.skill_requested)
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


@router.post("/auto", response_model=TaskResponse, status_code=201)
async def auto_create_task(data: AutoTaskCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Auto-select best agent and create task with failover."""
    from core.auto_select import select_ranked_agents
    from core.routing import route_task_with_failover

    ranked = await select_ranked_agents(db, data.skill_requested, data.preferences)
    if not ranked:
        raise NotFoundError("No available agent for this skill")

    best = ranked[0]
    quoted_price = best.price_per_task
    payload_size = len(json.dumps(data.payload).encode()) if data.payload else 0

    task = Task(
        requester_user_id=user.id,
        provider_agent_id=best.id,
        skill_requested=data.skill_requested,
        description=data.description,
        payload=data.payload,
        payload_size_bytes=payload_size,
        max_wait_seconds=data.max_wait_seconds,
        priority="normal",
        quoted_price=quoted_price,
        currency=best.currency,
        status="pending",
        metadata_={"auto_selected": True, "preferences": data.preferences},
    )
    db.add(task)
    await db.flush()

    if quoted_price > 0:
        escrow = await hold_credits(db, user.id, quoted_price, task.id)
        task.status = "escrowed"
        task.escrowed_at = datetime.now(timezone.utc)
        task.platform_fee = escrow.platform_fee

    task = await route_task_with_failover(db, task, ranked, max_attempts=3)
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

    # Release concurrency slot
    from core.routing import release_agent_slot
    await release_agent_slot(db, task.provider_agent_id)

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

    # Release concurrency slot
    from core.routing import release_agent_slot
    await release_agent_slot(db, task.provider_agent_id)

    await db.commit()
    await db.refresh(task)
    return task


# ── Async agent callback endpoint ────────────────────────────────────────────

import hashlib
import hmac as hmac_mod
from fastapi import Header


@router.post("/{task_id}/result", response_model=TaskResponse)
async def submit_task_result(
    task_id: UUID,
    data: TaskComplete,
    x_rentanagent_signature: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Callback endpoint for async agents to submit results.

    Agents that returned {"accepted": true} during dispatch call this
    endpoint when processing is complete. The request must be signed
    with HMAC-SHA256 using the shared secret.
    """
    from config import settings as cfg
    from core.routing import release_agent_slot
    from core.health import record_dispatch_success

    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")

    if task.status not in ("processing", "routed"):
        raise AppValidationError(f"Task not awaiting result (status: {task.status})")

    # Verify HMAC signature
    body_bytes = json.dumps(data.model_dump(), default=str).encode()
    expected_sig = hmac_mod.new(cfg.HMAC_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()
    if not hmac_mod.compare_digest(x_rentanagent_signature, expected_sig):
        raise ForbiddenError("Invalid signature")

    task.result = data.result
    task.result_size_bytes = len(json.dumps(data.result).encode())
    task.actual_price = data.actual_price or task.quoted_price
    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)

    # Release escrow
    escrow = (await db.execute(
        select(Escrow).where(Escrow.task_id == task_id, Escrow.status == "held")
    )).scalar_one_or_none()
    if escrow:
        await release_escrow(db, escrow.id)

    # Release concurrency slot
    await release_agent_slot(db, task.provider_agent_id)

    # Record healthy dispatch
    agent = (await db.execute(select(Agent).where(Agent.id == task.provider_agent_id))).scalar_one_or_none()
    if agent:
        await record_dispatch_success(db, agent)

    await db.commit()
    await db.refresh(task)

    # Trigger webhooks
    try:
        from core.webhooks import trigger_webhook
        await trigger_webhook(db, task.id, "task.completed")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Failed to trigger webhooks for task %s: %s", task.id, e)

    return task


# ── Subtask & Chain endpoints ────────────────────────────────────────────────

from pydantic import BaseModel as SubtaskBase, Field as SubtaskField


class CreateSubtaskRequest(SubtaskBase):
    """Request body for creating a subtask under an existing task."""
    provider_agent_id: UUID
    skill_requested: str
    payload: dict = {}


@router.post("/{task_id}/subtask")
async def create_subtask_endpoint(
    task_id: UUID,
    body: CreateSubtaskRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a child task linked to a parent task.

    The caller must be the assigned provider of the parent task (via their user account).
    This allows provider agents to hire other agents during task execution.
    """
    from core.chain import create_subtask

    parent = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not parent:
        raise NotFoundError("Parent task not found")

    provider_agent = (await db.execute(
        select(Agent).where(Agent.id == parent.provider_agent_id)
    )).scalar_one_or_none()
    if not provider_agent or provider_agent.owner_id != user.id:
        raise ForbiddenError("Only the assigned provider can create subtasks")

    try:
        child = await create_subtask(
            db=db,
            parent_task_id=task_id,
            provider_agent_id=body.provider_agent_id,
            skill=body.skill_requested,
            payload=body.payload,
        )
        await db.commit()
        await db.refresh(child)
        return child
    except Exception as e:
        await db.rollback()
        raise


@router.get("/{task_id}/chain")
async def get_task_chain_endpoint(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the full task chain tree for a root task.

    Returns a nested tree structure showing all subtasks and their statuses.
    """
    from core.chain import get_task_chain

    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    if task.requester_user_id != user.id and user.role != "admin":
        raise ForbiddenError("Not your task")

    root_id = task.root_task_id or task.id
    return await get_task_chain(db, root_id)
