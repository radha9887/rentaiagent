from sqlalchemy import select, func, desc, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from models.agent import Agent, AgentSkill
from models.rating import AgentStats
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
