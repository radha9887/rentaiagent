from uuid import UUID
from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.task import Task
from models.agent import Agent
from models.credit import Escrow
from core.escrow import release_escrow, refund_escrow

logger = logging.getLogger(__name__)


async def route_task(db: AsyncSession, task_id: UUID) -> Task:
    """Route task to provider agent. Uses A2A client or simulation mode."""
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one()
    task.status = "routed"
    task.routed_at = datetime.now(timezone.utc)
    await db.flush()

    if settings.SIMULATION_MODE:
        # Simulation: mark as completed without calling provider
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.result = {"simulated": True, "message": "Task completed (simulation mode)"}

        # Release escrow if held
        escrow = (await db.execute(
            select(Escrow).where(Escrow.task_id == task.id, Escrow.status == "held")
        )).scalar_one_or_none()
        if escrow:
            await release_escrow(db, escrow.id)

        await db.flush()
        return task

    # Real provider routing
    from a2a.client import send_task_to_provider

    agent = (await db.execute(select(Agent).where(Agent.id == task.provider_agent_id))).scalar_one()
    task.status = "processing"
    task.processing_at = datetime.now(timezone.utc)
    await db.flush()

    result = await send_task_to_provider(agent, task)
    status = result.get("status", "failed")

    escrow = (await db.execute(
        select(Escrow).where(Escrow.task_id == task.id, Escrow.status == "held")
    )).scalar_one_or_none()

    if status == "completed":
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.result = result.get("data", result)
        if escrow:
            await release_escrow(db, escrow.id)
    elif status == "timeout":
        task.status = "timeout"
        task.error_message = result.get("error", "Provider timed out")
        if escrow:
            await refund_escrow(db, escrow.id)
    else:
        task.status = "failed"
        task.error_message = result.get("error", "Provider error")
        if escrow:
            await refund_escrow(db, escrow.id)

    await db.flush()
    return task
