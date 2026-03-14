from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from db import get_db
from models.agent import Agent
from models.task import Task

router = APIRouter(tags=["stats"])


@router.get("/v1/stats")
async def platform_stats(db: AsyncSession = Depends(get_db)):
    """Public platform stats - uses COUNT queries, not full table scans."""
    agent_count = (await db.execute(select(func.count(Agent.id)).where(Agent.status == "online"))).scalar() or 0
    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar() or 0
    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar() or 0
    completed_tasks = (await db.execute(select(func.count(Task.id)).where(Task.status == "completed"))).scalar() or 0

    return {
        "agents_online": agent_count,
        "agents_total": total_agents,
        "tasks_total": total_tasks,
        "tasks_completed": completed_tasks,
        "success_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
    }
