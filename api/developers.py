from fastapi import APIRouter, Depends
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import secrets
from datetime import datetime, timezone

from db import get_db
from models.user import User, APIKey
from models.credit import CreditAccount
from models.task import Task
from models.agent import Agent
from utils.hashing import hash_password, generate_api_key, hash_api_key, verify_api_key
from utils.errors import ConflictError, NotFoundError, AuthError
from api.deps import get_current_user

router = APIRouter(prefix="/v1/developers", tags=["developers"])


class DevRegister(BaseModel):
    email: EmailStr


@router.post("/register")
async def developer_register(data: DevRegister, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing:
        raise ConflictError("Email already registered. Use /v1/developers/key to get a new key")

    random_pass = secrets.token_hex(16)
    user = User(
        email=data.email,
        password_hash=hash_password(random_pass),
        display_name=data.email.split("@")[0],
        role="developer",
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

    credit_account = CreditAccount(user_id=user.id, balance=100)
    db.add(credit_account)

    await db.commit()

    return {
        "api_key": raw_key,
        "credits": 100,
        "plan": "free",
        "email": data.email,
    }


@router.post("/key")
async def developer_get_key(data: DevRegister, db: AsyncSession = Depends(get_db)):
    # TODO: Rate limited: max 5 calls per hour per IP
    user = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if not user:
        raise NotFoundError("No account found for this email")

    # Generate a new key (old ones stay valid)
    raw_key = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        key_prefix=raw_key[:13],
        key_hash=hash_api_key(raw_key),
        name="recovered",
    )
    db.add(api_key)
    await db.commit()

    # TODO: Send key to email instead of returning it
    return {"api_key": raw_key, "email": data.email}


@router.get("/usage")
async def developer_usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    credit = (await db.execute(select(CreditAccount).where(CreditAccount.user_id == user.id))).scalar_one_or_none()

    # Count tasks
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_completed = (await db.execute(
        select(sqlfunc.count()).select_from(Task).where(Task.requester_user_id == user.id, Task.status == "completed")
    )).scalar() or 0

    total_failed = (await db.execute(
        select(sqlfunc.count()).select_from(Task).where(Task.requester_user_id == user.id, Task.status == "failed")
    )).scalar() or 0

    tasks_this_month = (await db.execute(
        select(sqlfunc.count()).select_from(Task).where(
            Task.requester_user_id == user.id,
            Task.created_at >= month_start,
        )
    )).scalar() or 0

    # Get API key prefix
    api_key = (await db.execute(
        select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active == True).order_by(APIKey.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    return {
        "email": user.email,
        "plan": "free",
        "credits_remaining": float(credit.balance) if credit else 0,
        "credits_used": float(credit.total_spent) if credit else 0,
        "tasks_completed": total_completed,
        "tasks_failed": total_failed,
        "tasks_this_month": tasks_this_month,
        "monthly_limit": 50,
        "api_key_prefix": api_key.key_prefix + "..." if api_key else None,
    }


@router.post("/generate-key")
async def generate_key(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    raw_key = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        key_prefix=raw_key[:13],
        key_hash=hash_api_key(raw_key),
        name="generated",
    )
    db.add(api_key)
    await db.commit()

    return {
        "api_key": raw_key,
        "prefix": raw_key[:13],
        "created_at": api_key.created_at.isoformat() if api_key.created_at else datetime.now(timezone.utc).isoformat(),
    }


@router.get("/keys")
async def list_keys(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user.id).order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    return {
        "keys": [
            {
                "prefix": k.key_prefix,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]
    }


@router.delete("/keys/{prefix}")
async def revoke_key(prefix: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user.id, APIKey.key_prefix == prefix, APIKey.is_active == True)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise NotFoundError("Key not found or already revoked")

    key.is_active = False
    await db.commit()

    return {"revoked": True}


@router.get("/my-agents")
async def my_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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
