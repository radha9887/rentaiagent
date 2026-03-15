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
from utils.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError as AppValidationError
from utils.pagination import encode_cursor, decode_cursor
from core.matching import build_agent_search_query, search_agents_rag
from core.embeddings import embed_and_store_agent
from api.deps import get_current_user
import httpx
import asyncio

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=201)
async def register_agent(data: AgentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent_count = (await db.execute(
        select(func.count(Agent.id)).where(Agent.owner_id == user.id)
    )).scalar() or 0
    if agent_count >= 20:
        raise AppValidationError("Maximum 20 agents per account. Contact support for higher limits.")

    existing = (await db.execute(select(Agent).where(Agent.slug == data.slug))).scalar_one_or_none()
    if existing:
        raise ConflictError("Slug already taken")

    if not data.health_check_url or not data.health_check_url.startswith(("http://", "https://")):
        raise AppValidationError("Health check URL is required and must be a valid HTTP/HTTPS URL")

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

    # Auto-verify: hit health endpoint
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(data.health_check_url)
            if resp.status_code < 300:
                agent.status = "online"
                agent.health_status = "healthy"
            else:
                agent.status = "pending_verification"
                agent.health_status = "unknown"
    except Exception:
        agent.status = "pending_verification"
        agent.health_status = "unknown"

    # Check if this is user's first verified agent — grant signup bonus
    if agent.status == "online":
        from models.credit import CreditAccount, Transaction
        first_agent_count = (await db.execute(
            select(func.count(Agent.id)).where(
                Agent.owner_id == user.id,
                Agent.status == "online",
                Agent.id != agent.id,
            )
        )).scalar() or 0

        if first_agent_count == 0:
            credit_account = (await db.execute(
                select(CreditAccount).where(CreditAccount.user_id == user.id)
            )).scalar_one_or_none()
            if credit_account and credit_account.balance == 0:
                credit_account.balance = 100
                bonus_tx = Transaction(
                    to_account_id=credit_account.id,
                    type="topup",
                    amount=100,
                    currency="credits",
                    status="completed",
                    description="Welcome bonus: first agent verified! 100 credits",
                )
                db.add(bonus_tx)

    await db.commit()
    await db.refresh(agent)

    # Embed agent description (non-blocking)
    asyncio.create_task(_embed_agent_background(str(agent.id)))

    return agent


async def _embed_agent_background(agent_id: str):
    """Background task to embed an agent's description."""
    try:
        from db import async_session
        from sqlalchemy import select as _select
        async with async_session() as session:
            agent = (await session.execute(_select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
            if agent:
                await embed_and_store_agent(session, agent)
                await session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Background embed failed for agent %s: %s", agent_id, e)


from pydantic import BaseModel as _ImportBase
from decimal import Decimal
import re
import secrets

class AgentImport(_ImportBase):
    url: str
    price_per_task: Optional[Decimal] = None

@router.post("/import", response_model=AgentResponse, status_code=201)
async def import_agent(data: AgentImport, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Import an agent from its A2A agent card URL."""
    # Check agent limit
    agent_count = (await db.execute(
        select(func.count(Agent.id)).where(Agent.owner_id == user.id)
    )).scalar() or 0
    if agent_count >= 20:
        raise AppValidationError("Maximum 20 agents per account. Contact support for higher limits.")

    # Fetch agent card
    card_url = data.url.rstrip("/") + "/.well-known/agent.json"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(card_url)
            if resp.status_code != 200:
                raise AppValidationError(f"Could not fetch agent card from {card_url} (HTTP {resp.status_code})")
            card = resp.json()
    except httpx.RequestError as e:
        raise AppValidationError(f"Could not reach {card_url}: {str(e)}")
    except AppValidationError:
        raise
    except Exception:
        raise AppValidationError(f"Invalid agent card JSON at {card_url}")

    # Extract info from card
    name = card.get("name", "Imported Agent")
    description = card.get("description", "")
    endpoint_url = card.get("url", data.url)

    # Generate slug from name
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # Check slug uniqueness
    existing = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{secrets.token_hex(3)}"

    # Extract pricing
    price = data.price_per_task
    if price is None:
        ext = card.get("x-rentaiagent", {}).get("pricing", {})
        price = Decimal(str(ext.get("price_per_task", 0)))

    # Extract protocols
    protocols = []
    if card.get("capabilities", {}).get("streaming"):
        protocols.append("streaming")
    protocols.append("a2a")

    # Create agent
    agent = Agent(
        owner_id=user.id, name=name, slug=slug, description=description,
        endpoint_url=endpoint_url, endpoint_type="a2a",
        pricing_model="per_task", price_per_task=price,
        currency="credits",
        health_check_url=endpoint_url,
        protocols=protocols,
        metadata_={"imported_from": data.url, "agent_card": card},
    )
    db.add(agent)
    await db.flush()

    # Add skills from card
    card_skills = card.get("skills", [])
    for s in card_skills:
        skill_tag = s.get("id") or s.get("name", "general")
        category = s.get("category", "general")
        db.add(AgentSkill(agent_id=agent.id, skill_tag=skill_tag, category=category, proficiency=0.5))

    # Create stats record
    stats = AgentStats(agent_id=agent.id)
    db.add(stats)

    # Auto-verify
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(endpoint_url)
            if resp.status_code < 400:
                agent.status = "online"
                agent.health_status = "healthy"
            else:
                agent.status = "pending_verification"
                agent.health_status = "unknown"
    except Exception:
        agent.status = "pending_verification"
        agent.health_status = "unknown"

    await db.commit()
    await db.refresh(agent)
    return agent

@router.get("/me")
async def my_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = (await db.execute(
        select(Agent).where(Agent.owner_id == user.id).order_by(Agent.created_at.desc())
    )).scalars().all()
    return {"agents": [AgentListResponse.model_validate(a) for a in result]}


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
    return {"agents": [AgentListResponse.model_validate(a) for a in result]}


@router.get("/import/preview")
async def preview_agent_import(url: str = Query(...)):
    """Preview an agent card without creating anything."""
    card_url = url.rstrip("/") + "/.well-known/agent.json"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(card_url)
            if resp.status_code != 200:
                raise AppValidationError(f"Could not fetch agent card (HTTP {resp.status_code})")
            card = resp.json()
    except httpx.RequestError as e:
        raise AppValidationError(f"Could not reach {card_url}: {str(e)}")
    except AppValidationError:
        raise
    except Exception:
        raise AppValidationError(f"Invalid JSON at {card_url}")

    name = card.get("name", "")
    description = card.get("description", "")
    endpoint_url = card.get("url", url)
    skills = []
    for s in card.get("skills", []):
        skills.append({
            "skill_tag": s.get("id") or s.get("name", ""),
            "category": s.get("category", "general"),
        })
    ext = card.get("x-rentaiagent", {}).get("pricing", {})
    price = ext.get("price_per_task", 0)

    return {
        "name": name,
        "description": description,
        "endpoint_url": endpoint_url,
        "health_check_url": endpoint_url,
        "skills": skills,
        "price_per_task": price,
        "card": card,
    }


@router.get("/search")
async def search_agents(
    q: Optional[str] = None,
    skill: Optional[str] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    priority: str = Query(default="balanced", pattern="^(balanced|quality|speed|price)$"),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search agents using natural language (RAG) or skill tag."""
    if q:
        agents = await search_agents_rag(db, q, max_price=max_price, min_rating=min_rating, priority=priority, limit=limit)
        return {"agents": [AgentListResponse.model_validate(a) for a in agents], "method": "rag"}
    elif skill:
        query = build_agent_search_query(skill=skill, max_price=max_price, min_rating=min_rating).limit(limit)
        agents = (await db.execute(query)).scalars().all()
        return {"agents": [AgentListResponse.model_validate(a) for a in agents], "method": "tag"}
    else:
        return {"agents": [], "method": "none", "error": "Provide either 'q' or 'skill' parameter"}


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

    # Re-embed if description or skills changed
    needs_reembed = "description" in update_data or "name" in update_data or skills_data is not None

    await db.commit()
    await db.refresh(agent)

    if needs_reembed:
        asyncio.create_task(_embed_agent_background(str(agent.id)))

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
