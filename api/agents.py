from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from db import get_db
from models.agent import Agent, AgentSkill
from models.rating import AgentStats
from models.user import User
from schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentListResponse
from schemas.common import CursorPage, MessageResponse
from utils.errors import NotFoundError, ForbiddenError, ConflictError
from utils.pagination import encode_cursor, decode_cursor
from core.matching import build_agent_search_query
from api.deps import get_current_user

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=201)
async def register_agent(data: AgentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Agent).where(Agent.slug == data.slug))).scalar_one_or_none()
    if existing:
        raise ConflictError("Slug already taken")

    agent = Agent(
        owner_id=user.id, name=data.name, slug=data.slug, description=data.description,
        endpoint_url=data.endpoint_url, endpoint_type=data.endpoint_type,
        pricing_model=data.pricing_model, price_per_task=data.price_per_task,
        currency=data.currency, health_check_url=data.health_check_url,
        version=data.version, framework=data.framework, protocols=data.protocols or [],
        metadata_=data.metadata_ or {},
        max_concurrent_tasks=data.max_concurrent_tasks,
    )
    db.add(agent)
    await db.flush()

    for s in data.skills:
        db.add(AgentSkill(agent_id=agent.id, skill_tag=s.skill_tag, category=s.category, proficiency=s.proficiency))

    stats = AgentStats(agent_id=agent.id)
    db.add(stats)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/me")
async def my_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = (await db.execute(
        select(Agent).where(Agent.owner_id == user.id).order_by(Agent.created_at.desc())
    )).scalars().all()
    return {"agents": result}


@router.get("/featured")
async def featured_agents(limit: int = Query(default=6, le=20), db: AsyncSession = Depends(get_db)):
    """Public endpoint: top agents by rating, online only."""
    query = (
        select(Agent)
        .outerjoin(AgentStats, AgentStats.agent_id == Agent.id)
        .where(Agent.status == "online")
        .order_by(AgentStats.avg_rating.desc().nulls_last(), Agent.created_at.desc())
        .limit(limit)
    )
    result = (await db.execute(query)).scalars().all()
    return {"agents": result}


@router.get("", response_model=CursorPage[AgentListResponse])
async def list_agents(
    skill: Optional[str] = None,
    q: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    sort: str = "relevance",
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = build_agent_search_query(skill=skill, q=q, category=category, max_price=max_price, min_rating=min_rating, sort=sort)

    if cursor:
        cursor_id = decode_cursor(cursor)
        query = query.where(Agent.id > UUID(cursor_id))

    query = query.limit(limit + 1)
    result = (await db.execute(query)).scalars().all()

    has_more = len(result) > limit
    items = result[:limit]
    next_cursor = encode_cursor(str(items[-1].id)) if has_more and items else None

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/{slug}", response_model=AgentResponse)
async def get_agent(slug: str, db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    return agent


@router.patch("/{slug}", response_model=AgentResponse)
async def update_agent(slug: str, data: AgentUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    if agent.owner_id != user.id:
        raise ForbiddenError("Not your agent")

    update_data = data.model_dump(exclude_unset=True, by_alias=False)
    skills_data = update_data.pop("skills", None)

    for k, v in update_data.items():
        setattr(agent, k, v)

    if skills_data is not None:
        await db.execute(select(AgentSkill).where(AgentSkill.agent_id == agent.id))
        for old in agent.skills:
            await db.delete(old)
        for s in skills_data:
            db.add(AgentSkill(agent_id=agent.id, skill_tag=s.skill_tag, category=s.category, proficiency=s.proficiency))

    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{slug}/health")
async def get_agent_health(slug: str, db: AsyncSession = Depends(get_db)):
    """Get agent health status (public)."""
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    return {
        "slug": agent.slug,
        "health_status": agent.health_status,
        "health_avg_latency_ms": agent.health_avg_latency_ms,
        "health_last_checked_at": agent.health_last_checked_at.isoformat() if agent.health_last_checked_at else None,
        "health_last_success_at": agent.health_last_success_at.isoformat() if agent.health_last_success_at else None,
        "health_consecutive_fails": agent.health_consecutive_fails,
        "max_concurrent_tasks": agent.max_concurrent_tasks,
        "active_task_count": agent.active_task_count,
    }


@router.delete("/{slug}", response_model=MessageResponse)
async def delete_agent(slug: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")
    if agent.owner_id != user.id:
        raise ForbiddenError("Not your agent")
    agent.status = "offline"
    await db.commit()
    return MessageResponse(message="Agent set to offline")
