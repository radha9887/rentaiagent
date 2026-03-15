import math
from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from models.agent import Agent, AgentSkill
from models.rating import AgentStats
from core.trust import calculate_trust_tier
from typing import Optional


def build_agent_search_query(
    skill: Optional[str] = None,
    q: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    sort: str = "relevance",
):
    """Build query for agent search with relevance scoring."""
    query = select(Agent).where(Agent.status == "online")

    if skill:
        query = query.join(AgentSkill, Agent.id == AgentSkill.agent_id).where(AgentSkill.skill_tag == skill)

    if q:
        query = query.where(Agent.skills_vector.match(q))

    if category:
        query = query.join(AgentSkill, Agent.id == AgentSkill.agent_id, isouter=True).where(AgentSkill.category == category)

    if max_price is not None:
        query = query.where(Agent.price_per_task <= max_price)

    if min_rating is not None:
        query = query.outerjoin(AgentStats, Agent.id == AgentStats.agent_id).where(AgentStats.avg_rating >= min_rating)

    if sort == "price_asc":
        query = query.order_by(Agent.price_per_task.asc())
    elif sort == "price_desc":
        query = query.order_by(Agent.price_per_task.desc())
    elif sort == "rating":
        query = query.outerjoin(AgentStats, Agent.id == AgentStats.agent_id).order_by(desc(AgentStats.avg_rating))
    else:
        query = query.order_by(Agent.created_at.desc())

    return query


def wilson_score(positive: int, total: int, z: float = 1.96) -> float:
    """Wilson lower bound score for binomial confidence interval."""
    if total == 0:
        return 0.0
    p = positive / total
    n = total
    return (p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / (1 + z * z / n)


TRUST_TIER_BONUS = {
    "platinum": 1.0,
    "gold": 0.8,
    "silver": 0.6,
    "bronze": 0.4,
    "new": 0.2,
}


def score_agent(agent: Agent, priority: str = "balanced") -> float:
    """Score an agent using Wilson lower bound + trust tier."""
    stats = agent.stats

    # Wilson score from rating data
    if stats and stats.rating_count > 0:
        # Convert avg 5-star rating to positive/total: ratings >= 4 are "positive"
        # Approximate: wilson based on acceptance-like metric
        positive = int(stats.avg_rating / 5.0 * stats.rating_count)
        w_score = wilson_score(positive, stats.rating_count)
    else:
        w_score = 0.3  # prior for unknown

    success = stats.acceptance_rate if stats and stats.acceptance_rate else 0.5
    avg_resp = agent.health_avg_latency_ms or 5000
    speed = 1.0 - min(avg_resp / 10000, 1.0)
    price_score = 1.0 - min(float(agent.price_per_task or 0) / 100, 1.0)
    capacity = 1.0 - (agent.active_task_count / max(agent.max_concurrent_tasks, 1))

    # Trust tier
    trust_tier = agent.trust_tier or "new"
    trust_bonus = TRUST_TIER_BONUS.get(trust_tier, 0.2)

    weights = {
        "balanced": (0.30, 0.20, 0.15, 0.15, 0.10, 0.10),
        "quality":  (0.40, 0.25, 0.10, 0.05, 0.10, 0.10),
        "speed":    (0.15, 0.15, 0.35, 0.10, 0.15, 0.10),
        "price":    (0.15, 0.10, 0.10, 0.40, 0.15, 0.10),
    }
    w = weights.get(priority, weights["balanced"])
    return (
        w[0] * w_score
        + w[1] * success
        + w[2] * speed
        + w[3] * price_score
        + w[4] * capacity
        + w[5] * trust_bonus
    )


async def search_agents_rag(
    db: AsyncSession,
    query: str,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    priority: str = "balanced",
    limit: int = 10,
) -> list[Agent]:
    """RAG-based agent search: embed query → pgvector cosine similarity → score top candidates."""
    from core.embeddings import embed_text

    query_embedding = await embed_text(query)
    if query_embedding is None:
        # Fallback to text search
        q = build_agent_search_query(q=query, max_price=max_price, min_rating=min_rating).limit(limit)
        result = (await db.execute(q)).scalars().all()
        return list(result)

    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # Build SQL for pgvector cosine similarity with filters
    sql_parts = [
        "SELECT a.id FROM agents a",
        "LEFT JOIN agent_stats s ON s.agent_id = a.id",
        "WHERE a.status = 'online'",
        "AND a.description_embedding IS NOT NULL",
        "AND a.health_status IN ('healthy', 'unknown')",
        "AND a.active_task_count < a.max_concurrent_tasks",
    ]
    params: dict = {"vec": vec_str}

    if max_price is not None:
        sql_parts.append("AND a.price_per_task <= :max_price")
        params["max_price"] = max_price
    if min_rating is not None:
        sql_parts.append("AND s.avg_rating >= :min_rating")
        params["min_rating"] = min_rating

    sql_parts.append("ORDER BY a.description_embedding <=> CAST(:vec AS vector)")
    sql_parts.append("LIMIT 50")

    sql = "\n".join(sql_parts)
    result = await db.execute(text(sql), params)
    candidate_ids = [row[0] for row in result.fetchall()]

    if not candidate_ids:
        return []

    # Build relevance scores from vector ordering (rank 0 = most relevant)
    relevance_by_id = {cid: 1.0 - (i / len(candidate_ids)) for i, cid in enumerate(candidate_ids)}

    # Load full agent objects
    agents_result = await db.execute(
        select(Agent)
        .outerjoin(AgentStats, Agent.id == AgentStats.agent_id)
        .where(Agent.id.in_(candidate_ids))
    )
    agents = list(agents_result.scalars().unique().all())

    # Blend: 50% semantic relevance + 50% quality score
    def combined_score(agent):
        relevance = relevance_by_id.get(agent.id, 0)
        quality = score_agent(agent, priority)
        return 0.5 * relevance + 0.5 * quality

    scored = sorted(agents, key=combined_score, reverse=True)
    return scored[:limit]
