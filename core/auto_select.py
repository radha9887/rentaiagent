"""Auto-select the best available agent for a skill."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent import Agent, AgentSkill
from models.rating import AgentStats
from core.matching import score_agent, search_agents_rag


async def select_best_agent(
    db: AsyncSession, skill: str, preferences: dict | None = None, query: str | None = None
) -> Agent | None:
    """Select the best available agent for a skill using scoring.

    If `query` is provided, uses RAG search. Otherwise falls back to tag match.
    """
    preferences = preferences or {}
    max_price = preferences.get("max_price")
    min_rating = preferences.get("min_rating")
    priority = preferences.get("priority", "balanced")

    # RAG path
    if query:
        results = await search_agents_rag(db, query, max_price=max_price, min_rating=min_rating, priority=priority, limit=1)
        return results[0] if results else None

    # Tag-based path
    q = (
        select(Agent)
        .join(AgentSkill, Agent.id == AgentSkill.agent_id)
        .outerjoin(AgentStats, Agent.id == AgentStats.agent_id)
        .where(
            Agent.status == "online",
            AgentSkill.skill_tag == skill,
            Agent.active_task_count < Agent.max_concurrent_tasks,
            Agent.health_status.in_(["healthy", "unknown"]),
        )
    )
    if max_price is not None:
        q = q.where(Agent.price_per_task <= max_price)
    if min_rating is not None:
        q = q.where(AgentStats.avg_rating >= min_rating)

    agents = (await db.execute(q)).scalars().unique().all()
    if not agents:
        return None

    scored = sorted(agents, key=lambda a: score_agent(a, priority), reverse=True)
    return scored[0]


async def select_ranked_agents(
    db: AsyncSession, skill: str, preferences: dict | None = None, limit: int = 5, query: str | None = None
) -> list[Agent]:
    """Return ranked list of agents for failover routing."""
    preferences = preferences or {}
    max_price = preferences.get("max_price")
    min_rating = preferences.get("min_rating")
    priority = preferences.get("priority", "balanced")

    # RAG path
    if query:
        return await search_agents_rag(db, query, max_price=max_price, min_rating=min_rating, priority=priority, limit=limit)

    # Tag-based path
    q = (
        select(Agent)
        .join(AgentSkill, Agent.id == AgentSkill.agent_id)
        .outerjoin(AgentStats, Agent.id == AgentStats.agent_id)
        .where(
            Agent.status == "online",
            AgentSkill.skill_tag == skill,
            Agent.active_task_count < Agent.max_concurrent_tasks,
            Agent.health_status.in_(["healthy", "unknown"]),
        )
    )
    if max_price is not None:
        q = q.where(Agent.price_per_task <= max_price)
    if min_rating is not None:
        q = q.where(AgentStats.avg_rating >= min_rating)

    agents = (await db.execute(q)).scalars().unique().all()
    if not agents:
        return []

    return sorted(agents, key=lambda a: score_agent(a, priority), reverse=True)[:limit]
