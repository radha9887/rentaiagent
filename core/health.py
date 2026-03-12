"""Lazy agent health tracking — updated only during task dispatch, not proactively."""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.agent import Agent

logger = logging.getLogger(__name__)


async def record_dispatch_success(db: AsyncSession, agent: Agent, latency_ms: float | None = None):
    """Called when a task dispatch succeeds (sync complete or async ACK)."""
    agent.health_status = "healthy"
    agent.health_consecutive_fails = 0
    agent.health_last_success_at = datetime.now(timezone.utc)
    agent.health_last_checked_at = datetime.now(timezone.utc)
    if latency_ms is not None:
        agent.health_avg_latency_ms = latency_ms
    # Auto-restore if was auto-offlined
    if agent.auto_offline_at and agent.status == "offline":
        agent.status = "online"
        agent.auto_offline_at = None
        logger.info("Auto-restored agent %s after successful dispatch", agent.slug)
    await db.flush()


async def record_dispatch_failure(db: AsyncSession, agent: Agent):
    """Called when a task dispatch fails (timeout/error)."""
    agent.health_consecutive_fails += 1
    agent.health_status = "unhealthy"
    agent.health_last_checked_at = datetime.now(timezone.utc)
    if (agent.health_consecutive_fails >= settings.MAX_CONSECUTIVE_HEALTH_FAILS
            and agent.status == "online"):
        agent.status = "offline"
        agent.auto_offline_at = datetime.now(timezone.utc)
        logger.warning(
            "Auto-offlined agent %s after %d consecutive dispatch failures",
            agent.slug, agent.health_consecutive_fails,
        )
    await db.flush()


async def check_agent_health_manual(db: AsyncSession, agent: Agent) -> dict:
    """Manual health check for admin spot-checks. Not called automatically."""
    import time
    import httpx

    url = agent.health_check_url or agent.endpoint_url
    if not url:
        return {"healthy": False, "latency_ms": None, "error": "No health URL"}

    health_url = url.replace("/handle", "/health")
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS) as client:
            resp = await client.get(health_url)
            latency = (time.time() - start) * 1000
            healthy = resp.status_code == 200
            error = None if healthy else f"HTTP {resp.status_code}"
    except Exception as e:
        healthy = False
        latency = None
        error = str(e)

    if healthy:
        await record_dispatch_success(db, agent, latency)
    else:
        await record_dispatch_failure(db, agent)

    return {"healthy": healthy, "latency_ms": latency, "error": error}


async def check_all_agents_health(db):
    """Manual bulk health check for admin endpoint."""
    from sqlalchemy import select
    result = await db.execute(
        select(Agent).where(
            Agent.status.in_(["online", "offline"]),
            Agent.endpoint_url.isnot(None),
        )
    )
    agents = result.scalars().all()
    results = {"checked": 0, "healthy": 0, "unhealthy": 0, "auto_offlined": 0}
    for agent in agents:
        old_status = agent.status
        check = await check_agent_health_manual(db, agent)
        results["checked"] += 1
        if check["healthy"]:
            results["healthy"] += 1
        else:
            results["unhealthy"] += 1
        if old_status == "online" and agent.status == "offline":
            results["auto_offlined"] += 1
    await db.flush()
    return results
