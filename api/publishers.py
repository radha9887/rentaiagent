from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from decimal import Decimal
import secrets

from db import get_db
from models.user import User, APIKey
from models.credit import CreditAccount
from models.agent import Agent, AgentSkill
from models.rating import AgentStats
from utils.hashing import hash_password, generate_api_key, hash_api_key
from utils.errors import ConflictError, NotFoundError
from api.deps import get_current_user

router = APIRouter(prefix="/v1/publish", tags=["publishers"])


class PublishRegister(BaseModel):
    email: EmailStr
    name: str


class SkillInput(BaseModel):
    skill_tag: str
    category: str = "general"


class PublishAgent(BaseModel):
    name: str
    slug: str
    description: str = ""
    endpoint_url: str = ""
    skills: List[SkillInput] = []
    price_per_task: float = 0.0
    currency: str = "INR"


@router.post("/register")
async def publish_register(data: PublishRegister, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing:
        raise ConflictError("Email already registered. Use your existing key or request a new one.")

    random_pass = secrets.token_hex(16)
    user = User(
        email=data.email,
        password_hash=hash_password(random_pass),
        display_name=data.name,
        role="producer",
    )
    db.add(user)
    await db.flush()

    raw_key = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        key_prefix=raw_key[:13],
        key_hash=hash_api_key(raw_key),
        name="default",
    )
    db.add(api_key)

    credit_account = CreditAccount(user_id=user.id)
    db.add(credit_account)

    await db.commit()

    return {
        "api_key": raw_key,
        "user_id": str(user.id),
        "email": data.email,
        "name": data.name,
    }


@router.post("/agents")
async def publish_agent(data: PublishAgent, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Check slug uniqueness
    existing = (await db.execute(select(Agent).where(Agent.slug == data.slug))).scalar_one_or_none()
    if existing:
        raise ConflictError(f"Agent slug '{data.slug}' already taken")

    agent = Agent(
        owner_id=user.id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        endpoint_url=data.endpoint_url,
        endpoint_type="rest",
        pricing_model="per_task",
        price_per_task=Decimal(str(data.price_per_task)),
        currency=data.currency,
        status="online",
        trust_tier="new",
    )
    db.add(agent)
    await db.flush()

    for s in data.skills:
        skill = AgentSkill(agent_id=agent.id, skill_tag=s.skill_tag, category=s.category)
        db.add(skill)

    stats = AgentStats(agent_id=agent.id)
    db.add(stats)

    await db.commit()
    await db.refresh(agent)

    return {
        "id": str(agent.id),
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "endpoint_url": agent.endpoint_url,
        "price_per_task": str(agent.price_per_task),
        "currency": agent.currency,
        "status": agent.status,
        "skills": [{"skill_tag": s.skill_tag, "category": s.category} for s in agent.skills],
    }


@router.get("/agents")
async def list_my_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.owner_id == user.id))
    agents = result.scalars().all()

    items = []
    for a in agents:
        stats = a.stats
        items.append({
            "id": str(a.id),
            "name": a.name,
            "slug": a.slug,
            "description": a.description,
            "status": a.status,
            "price_per_task": str(a.price_per_task),
            "currency": a.currency,
            "skills": [{"skill_tag": s.skill_tag, "category": s.category} for s in a.skills],
            "tasks": stats.total_tasks if stats else 0,
            "earned": float(stats.total_earned) if stats else 0,
            "rating": stats.avg_rating if stats else 0,
        })

    return {"agents": items}


@router.get("/earnings")
async def get_earnings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.owner_id == user.id))
    agents = result.scalars().all()

    total_earned = 0.0
    agent_earnings = []
    for a in agents:
        stats = a.stats
        earned = float(stats.total_earned) if stats else 0
        total_earned += earned
        agent_earnings.append({
            "name": a.name,
            "earned": earned,
            "tasks": stats.total_tasks if stats else 0,
        })

    return {
        "total_earned": total_earned,
        "this_month": 0,  # TODO: compute from transactions
        "pending": 0,  # TODO: compute from escrowed tasks
        "agents": agent_earnings,
    }
