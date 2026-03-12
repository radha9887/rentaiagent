from fastapi import APIRouter, Depends
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import secrets

from db import get_db
from models.user import User, APIKey
from models.credit import CreditAccount
from models.task import Task
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
        select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active == True).order_by(APIKey.created_at.desc())
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
