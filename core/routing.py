from uuid import UUID
from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.task import Task
from models.agent import Agent
from models.credit import Escrow
from models.external_agent import ExternalAgent
from core.escrow import release_escrow, refund_escrow

logger = logging.getLogger(__name__)


async def route_task(db: AsyncSession, task_id: UUID) -> Task:
    """Route task to internal worker, external REST, or external A2A agent.

    Dispatches based on agent type and protocol:
    1. Simulation mode → instant completion (dev/test)
    2. Internal agent → A2A or REST via existing client
    3. External agent → A2A JSON-RPC or webhook dispatch
    """
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one()
    task.status = "routed"
    task.routed_at = datetime.now(timezone.utc)
    await db.flush()

    if settings.SIMULATION_MODE:
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.result = {"simulated": True, "message": "Task completed (simulation mode)"}

        escrow = (await db.execute(
            select(Escrow).where(Escrow.task_id == task.id, Escrow.status == "held")
        )).scalar_one_or_none()
        if escrow:
            await release_escrow(db, escrow.id)

        await db.flush()
        return task

    # Check if provider is an internal agent
    agent = (await db.execute(select(Agent).where(Agent.id == task.provider_agent_id))).scalar_one_or_none()

    if agent:
        return await _route_to_internal(db, task, agent)

    # Check task metadata for external agent routing
    ext_agent_id = (task.metadata_ or {}).get("external_agent_id")
    if ext_agent_id:
        return await _route_to_external(db, task, UUID(ext_agent_id))

    # Fallback: mark failed if no provider found
    task.status = "failed"
    task.error_message = "No provider agent found for routing"
    await db.flush()
    return task


async def _route_to_internal(db: AsyncSession, task: Task, agent: Agent) -> Task:
    """Route task to an internal platform agent."""
    from a2a.client import send_task_to_provider

    task.status = "processing"
    task.processing_at = datetime.now(timezone.utc)
    await db.flush()

    result = await send_task_to_provider(agent, task)
    return await _finalize_task(db, task, result)


async def _route_to_external(db: AsyncSession, task: Task, external_agent_id: UUID) -> Task:
    """Route task to an external A2A agent."""
    from a2a.client import send_task_a2a_external

    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == external_agent_id)
    )).scalar_one_or_none()
    if not ext:
        task.status = "failed"
        task.error_message = "External agent not found"
        await db.flush()
        return task

    if ext.health_status == "unhealthy":
        logger.warning("Routing to unhealthy external agent %s", ext.name)

    task.status = "processing"
    task.processing_at = datetime.now(timezone.utc)
    await db.flush()

    result = await send_task_a2a_external(ext, task)
    return await _finalize_task(db, task, result)


async def _finalize_task(db: AsyncSession, task: Task, result: dict) -> Task:
    """Apply provider result to task and handle escrow."""
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

    # Trigger webhooks for task state changes
    try:
        from core.webhooks import trigger_webhook
        event = f"task.{task.status}"
        await trigger_webhook(db, task.id, event)
    except Exception as e:
        logger.error("Failed to trigger webhooks for task %s: %s", task.id, e)

    return task
