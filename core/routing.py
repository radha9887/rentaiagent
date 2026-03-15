from uuid import UUID
from datetime import datetime, timezone
import logging
import time

from sqlalchemy import select, update
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.task import Task
from models.agent import Agent
from models.credit import Escrow
from models.external_agent import ExternalAgent
from core.escrow import release_escrow, refund_escrow
from core.health import record_dispatch_success, record_dispatch_failure

logger = logging.getLogger(__name__)


async def acquire_agent_slot(db: AsyncSession, agent_id: UUID) -> bool:
    """Try to reserve a concurrency slot. Returns False if at capacity."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id).with_for_update())
    agent = result.scalar_one()
    if agent.active_task_count >= agent.max_concurrent_tasks:
        return False
    agent.active_task_count += 1
    await db.flush()
    return True


async def release_agent_slot(db: AsyncSession, agent_id: UUID):
    """Release a concurrency slot when task completes/fails."""
    await db.execute(
        update(Agent).where(Agent.id == agent_id).values(
            active_task_count=func.greatest(Agent.active_task_count - 1, 0)
        )
    )
    await db.flush()


async def route_task(db: AsyncSession, task_id: UUID) -> Task:
    """Route task to internal worker, external REST, or external A2A agent.

    Dispatches based on agent type and protocol:
    1. Simulation mode → instant completion (dev/test)
    2. Internal agent → A2A or REST via existing client
    3. External agent → A2A JSON-RPC or webhook dispatch
    """
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one()

    # Check concurrency before routing
    if not await acquire_agent_slot(db, task.provider_agent_id):
        from utils.errors import ValidationError as AppValidationError
        raise AppValidationError("Agent at capacity")

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

        await release_agent_slot(db, task.provider_agent_id)
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
    await release_agent_slot(db, task.provider_agent_id)
    await db.flush()
    return task


async def _route_to_internal(db: AsyncSession, task: Task, agent: Agent) -> Task:
    """Route task to an internal platform agent (or hosted Lambda)."""
    from models.hosted_agent import HostedAgent

    # Check if agent is hosted on Lambda
    hosted = (await db.execute(
        select(HostedAgent).where(HostedAgent.agent_id == agent.id, HostedAgent.deploy_status == "live")
    )).scalar_one_or_none()

    if hosted:
        from core.invoker import invoke_hosted_agent
        task.status = "processing"
        task.processing_at = datetime.now(timezone.utc)
        await db.flush()

        start_t = time.time()
        result = await invoke_hosted_agent(hosted, task)
        latency_ms = (time.time() - start_t) * 1000

        hosted.invocation_count += 1
        hosted.last_invoked_at = datetime.now(timezone.utc)
        await db.flush()

        return await _finalize_task(db, task, result, agent, latency_ms)

    from a2a.client import send_task_to_provider

    task.status = "processing"
    task.processing_at = datetime.now(timezone.utc)
    await db.flush()

    start = time.time()
    result = await send_task_to_provider(agent, task)
    latency_ms = (time.time() - start) * 1000

    return await _finalize_task(db, task, result, agent, latency_ms)


async def _route_to_external(db: AsyncSession, task: Task, external_agent_id: UUID) -> Task:
    """Route task to an external A2A agent."""
    from a2a.client import send_task_a2a_external

    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == external_agent_id)
    )).scalar_one_or_none()
    if not ext:
        task.status = "failed"
        task.error_message = "External agent not found"
        await release_agent_slot(db, task.provider_agent_id)
        await db.flush()
        return task

    if ext.health_status == "unhealthy":
        logger.warning("Routing to unhealthy external agent %s", ext.name)

    task.status = "processing"
    task.processing_at = datetime.now(timezone.utc)
    await db.flush()

    start = time.time()
    result = await send_task_a2a_external(ext, task)
    latency_ms = (time.time() - start) * 1000

    # For external agents, pass None for agent (health tracking is separate)
    return await _finalize_task(db, task, result, None, latency_ms)


async def _finalize_task(
    db: AsyncSession, task: Task, result: dict,
    agent: Agent | None = None, latency_ms: float | None = None,
) -> Task:
    """Apply provider result to task and handle escrow.

    Supports two response modes:
    - Sync: result has status=completed/failed + data → task done immediately
    - Async ACK: result has accepted=true → task stays in "processing", agent calls back later
    """
    # Detect async ACK
    if result.get("accepted") is True:
        # Agent acknowledged, task stays "processing" — agent will call back
        task.status = "processing"
        estimated = result.get("estimated_seconds")
        meta = dict(task.metadata_ or {})
        meta["async_ack"] = True
        if estimated:
            meta["estimated_seconds"] = estimated
        task.metadata_ = meta
        await db.flush()

        # Record successful dispatch (ACK counts as healthy)
        if agent:
            await record_dispatch_success(db, agent, latency_ms)

        # Trigger webhook for processing state
        try:
            from core.webhooks import trigger_webhook
            await trigger_webhook(db, task.id, "task.processing")
        except Exception as e:
            logger.error("Failed to trigger webhooks for task %s: %s", task.id, e)

        return task

    # Sync completion path
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
        # Record healthy dispatch
        if agent:
            await record_dispatch_success(db, agent, latency_ms)
    elif status == "timeout":
        task.status = "timeout"
        task.error_message = result.get("error", "Provider timed out")
        if escrow:
            await refund_escrow(db, escrow.id)
        # Record failed dispatch
        if agent:
            await record_dispatch_failure(db, agent)
    else:
        task.status = "failed"
        task.error_message = result.get("error", "Provider error")
        if escrow:
            await refund_escrow(db, escrow.id)
        # Record failed dispatch
        if agent:
            await record_dispatch_failure(db, agent)

    # Release concurrency slot (for sync completion/failure)
    await release_agent_slot(db, task.provider_agent_id)

    await db.flush()

    # Trigger webhooks for task state changes
    try:
        from core.webhooks import trigger_webhook
        event = f"task.{task.status}"
        await trigger_webhook(db, task.id, event)
    except Exception as e:
        logger.error("Failed to trigger webhooks for task %s: %s", task.id, e)

    return task


async def route_task_with_failover(
    db: AsyncSession, task: Task, ranked_agents: list[Agent], max_attempts: int = 3,
) -> Task:
    """Try dispatching to ranked agents with failover.

    Used by auto-route. Tries up to max_attempts agents from the ranked list.
    On dispatch failure, releases the slot and tries the next agent.
    """
    from a2a.client import send_task_to_provider

    attempts = min(max_attempts, len(ranked_agents))

    for i, agent in enumerate(ranked_agents[:attempts]):
        # Check concurrency
        if not await acquire_agent_slot(db, agent.id):
            logger.info("Agent %s at capacity, trying next", agent.slug)
            continue

        # Update task to point at this agent
        task.provider_agent_id = agent.id
        task.status = "routed"
        task.routed_at = datetime.now(timezone.utc)
        await db.flush()

        if settings.SIMULATION_MODE:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.result = {"simulated": True, "message": "Task completed (simulation mode)", "agent": agent.slug}

            escrow = (await db.execute(
                select(Escrow).where(Escrow.task_id == task.id, Escrow.status == "held")
            )).scalar_one_or_none()
            if escrow:
                await release_escrow(db, escrow.id)

            await release_agent_slot(db, agent.id)
            await db.flush()
            return task

        task.status = "processing"
        task.processing_at = datetime.now(timezone.utc)
        await db.flush()

        start = time.time()
        result = await send_task_to_provider(agent, task)
        latency_ms = (time.time() - start) * 1000

        # Check if dispatch succeeded (sync complete or async ACK)
        dispatch_ok = (
            result.get("accepted") is True
            or result.get("status") == "completed"
        )

        if dispatch_ok:
            return await _finalize_task(db, task, result, agent, latency_ms)

        # Dispatch failed — record failure, release slot, try next
        logger.warning("Dispatch to agent %s failed: %s", agent.slug, result.get("error", "unknown"))
        await record_dispatch_failure(db, agent)
        await release_agent_slot(db, agent.id)

        # If this is the last attempt, finalize as failed
        if i == attempts - 1:
            return await _finalize_task(db, task, result, agent, latency_ms)

    # All agents at capacity or exhausted
    task.status = "failed"
    task.error_message = "No available agents could handle this task"
    await db.flush()
    return task
