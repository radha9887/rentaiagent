"""Health check periodic task for agents."""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update

from config import settings
from worker import celery_app

logger = logging.getLogger(__name__)

# Track consecutive failures in memory (reset on worker restart — acceptable)
_failure_counts: dict[str, int] = {}


@celery_app.task(name="check_all_agents_health")
def check_all_agents_health():
    """Ping all online agents' health_check_url. 3 consecutive failures → offline."""
    import asyncio
    asyncio.run(_check_all())


async def _check_all():
    from db import async_session
    from models.agent import Agent

    async with async_session() as db:
        agents = (await db.execute(
            select(Agent).where(Agent.status == "online", Agent.health_check_url.isnot(None))
        )).scalars().all()

        for agent in agents:
            agent_key = str(agent.id)
            try:
                async with httpx.AsyncClient(timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS) as client:
                    resp = await client.get(agent.health_check_url)
                    resp.raise_for_status()

                # Success — reset counter, update timestamp
                _failure_counts.pop(agent_key, None)
                agent.last_health_at = datetime.now(timezone.utc)

            except Exception as e:
                count = _failure_counts.get(agent_key, 0) + 1
                _failure_counts[agent_key] = count
                logger.warning("Health check failed for %s (%d/3): %s", agent.slug, count, e)

                if count >= 3:
                    agent.status = "offline"
                    _failure_counts.pop(agent_key, None)
                    logger.warning("Agent %s marked offline after 3 failed health checks", agent.slug)

        await db.commit()
