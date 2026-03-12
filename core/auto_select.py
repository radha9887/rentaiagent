"""Auto-select the best available agent for a skill."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent import Agent, AgentSkill
from models.rating import AgentStats


async def select_best_agent(db: AsyncSession, skill: str, preferences: dict | None = None) -> Agent | None:
    """Select the best available agent for a skill using a scoring algorithm."""
    preferences = preferences or {}
    max_price = preferences.get("max_price")
    min_rating = preferences.get("min_rating")
    priority = preferences.get("priority", "balanced")

    query = (
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
        query = query.where(Agent.price_per_task <= max_price)
    if min_rating is not None:
        query = query.where(AgentStats.avg_rating >= min_rating)

    agents = (await db.execute(query)).scalars().unique().all()
    if not agents:
        return None

    def score_agent(agent: Agent) -> float:
        stats = agent.stats
        rating = (stats.avg_rating / 5.0) if stats and stats.avg_rating else 0.5
        success = stats.acceptance_rate if stats and stats.acceptance_rate else 0.5
        avg_resp = agent.health_avg_latency_ms or 5000
        speed = 1.0 - min(avg_resp / 10000, 1.0)
        price_score = 1.0 - min(float(agent.price_per_task or 0) / 100, 1.0)
        capacity = 1.0 - (agent.active_task_count / max(agent.max_concurrent_tasks, 1))

        weights = {
            "balanced": (0.30, 0.20, 0.15, 0.20, 0.15),
            "quality":  (0.45, 0.25, 0.10, 0.10, 0.10),
            "speed":    (0.15, 0.15, 0.40, 0.10, 0.20),
            "price":    (0.15, 0.15, 0.10, 0.45, 0.15),
        }
        w = weights.get(priority, weights["balanced"])
        return (
            w[0] * rating
            + w[1] * success
            + w[2] * speed
            + w[3] * price_score
            + w[4] * capacity
        )

    scored = sorted(agents, key=score_agent, reverse=True)
    return scored[0]


async def select_ranked_agents(db: AsyncSession, skill: str, preferences: dict | None = None, limit: int = 5) -> list[Agent]:
    """Return ranked list of agents for failover routing."""
    preferences = preferences or {}
    max_price = preferences.get("max_price")
    min_rating = preferences.get("min_rating")
    priority = preferences.get("priority", "balanced")

    query = (
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
        query = query.where(Agent.price_per_task <= max_price)
    if min_rating is not None:
        query = query.where(AgentStats.avg_rating >= min_rating)

    agents = (await db.execute(query)).scalars().unique().all()
    if not agents:
        return []

    def score_agent(agent: Agent) -> float:
        stats = agent.stats
        rating = (stats.avg_rating / 5.0) if stats and stats.avg_rating else 0.5
        success = stats.acceptance_rate if stats and stats.acceptance_rate else 0.5
        avg_resp = agent.health_avg_latency_ms or 5000
        speed = 1.0 - min(avg_resp / 10000, 1.0)
        price_score = 1.0 - min(float(agent.price_per_task or 0) / 100, 1.0)
        capacity = 1.0 - (agent.active_task_count / max(agent.max_concurrent_tasks, 1))
        weights = {
            "balanced": (0.30, 0.20, 0.15, 0.20, 0.15),
            "quality":  (0.45, 0.25, 0.10, 0.10, 0.10),
            "speed":    (0.15, 0.15, 0.40, 0.10, 0.20),
            "price":    (0.15, 0.15, 0.10, 0.45, 0.15),
        }
        w = weights.get(priority, weights["balanced"])
        return w[0]*rating + w[1]*success + w[2]*speed + w[3]*price_score + w[4]*capacity

    return sorted(agents, key=score_agent, reverse=True)[:limit]
