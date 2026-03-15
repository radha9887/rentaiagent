from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from uuid import UUID

from db import get_db
from models.user import User, APIKey
from models.credit import CreditAccount, Transaction
from schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse, APIKeyCreate, APIKeyCreated, APIKeyResponse
from schemas.common import MessageResponse
from utils.hashing import hash_password, verify_password, generate_api_key, hash_api_key
from utils.jwt import create_access_token, create_refresh_token
from utils.errors import AuthError, ConflictError, NotFoundError, ValidationError as AppValidationError
from utils.email_validator import validate_email_domain
from api.deps import get_current_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=APIKeyCreated, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    is_valid, error_msg = validate_email_domain(data.email)
    if not is_valid:
        raise AppValidationError(error_msg)

    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing:
        raise ConflictError("Email already registered")

    user = User(email=data.email, password_hash=hash_password(data.password), display_name=data.display_name)
    db.add(user)
    await db.flush()

    raw_key = generate_api_key()
    api_key = APIKey(user_id=user.id, key_prefix=raw_key[:13], key_hash=hash_api_key(raw_key), name="default")
    db.add(api_key)

    credit_account = CreditAccount(user_id=user.id, balance=100, currency="credits")
    db.add(credit_account)

    signup_tx = Transaction(
        from_account_id=None,
        to_account_id=credit_account.id,
        amount=100,
        type="bonus",
        description="Welcome bonus: 100 credits on signup",
    )
    db.add(signup_tx)

    await db.commit()
    await db.refresh(api_key)
    return APIKeyCreated(
        id=api_key.id, key_prefix=api_key.key_prefix, name=api_key.name,
        scopes=api_key.scopes or [], is_active=api_key.is_active,
        last_used_at=api_key.last_used_at, expires_at=api_key.expires_at,
        created_at=api_key.created_at, raw_key=raw_key,
    )


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise AuthError("Invalid credentials")
    if not user.is_active:
        raise AuthError("Account disabled")
    return {
        "token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
        },
    }


@router.post("/api-keys", response_model=APIKeyCreated, status_code=201)
async def create_api_key(data: APIKeyCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    raw_key = generate_api_key()
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
    api_key = APIKey(user_id=user.id, key_prefix=raw_key[:13], key_hash=hash_api_key(raw_key), name=data.name, scopes=data.scopes, expires_at=expires_at)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return APIKeyCreated(
        id=api_key.id, key_prefix=api_key.key_prefix, name=api_key.name,
        scopes=api_key.scopes or [], is_active=api_key.is_active,
        last_used_at=api_key.last_used_at, expires_at=api_key.expires_at,
        created_at=api_key.created_at, raw_key=raw_key,
    )


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
async def revoke_api_key(key_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    api_key = (await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))).scalar_one_or_none()
    if not api_key:
        raise NotFoundError("API key not found")
    api_key.is_active = False
    await db.commit()
    return MessageResponse(message="API key revoked")
