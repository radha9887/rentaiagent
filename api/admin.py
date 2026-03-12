from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from db import get_db
from models.user import User
from models.agent import Agent
from models.task import Task
from models.credit import Transaction
from schemas.admin import MetricsResponse
from schemas.common import MessageResponse
from utils.errors import NotFoundError
from api.deps import require_admin

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar()
    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar()
    completed_tasks = (await db.execute(select(func.count(Task.id)).where(Task.status == "completed"))).scalar()
    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.type == "fee")
    )).scalar()
    return MetricsResponse(
        total_users=total_users, total_agents=total_agents,
        total_tasks=total_tasks, completed_tasks=completed_tasks,
        total_revenue=total_revenue,
    )


@router.post("/agents/{agent_id}/approve", response_model=MessageResponse)
async def approve_agent(agent_id: UUID, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    agent.status = "online"
    await db.commit()
    return MessageResponse(message="Agent approved")


@router.post("/agents/{agent_id}/suspend", response_model=MessageResponse)
async def suspend_agent(agent_id: UUID, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    agent.status = "suspended"
    await db.commit()
    return MessageResponse(message="Agent suspended")


@router.post("/health-check")
async def trigger_health_check(user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Trigger health check for all agents."""
    from core.health import check_all_agents_health
    results = await check_all_agents_health(db)
    await db.commit()
    return results
