from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from db import get_db
from models.user import User, APIKey
from utils.jwt import decode_token
from utils.hashing import verify_api_key
from utils.errors import AuthError

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise AuthError("Missing authorization header")

    token = credentials.credentials

    # API key auth (raa_live_*)
    if token.startswith("raa_"):
        prefix = token[:13]
        keys = (await db.execute(select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True))).scalars().all()
        for key in keys:
            if verify_api_key(token, key.key_hash):
                if key.expires_at and key.expires_at < datetime.now(timezone.utc):
                    raise AuthError("API key expired")
                key.last_used_at = datetime.now(timezone.utc)
                await db.flush()
                user = (await db.execute(select(User).where(User.id == key.user_id))).scalar_one_or_none()
                if not user or not user.is_active:
                    raise AuthError("User inactive")
                return user
        raise AuthError("Invalid API key")

    # JWT auth
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise AuthError("Invalid token")

    user = (await db.execute(select(User).where(User.id == UUID(payload["sub"])))).scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("User not found or inactive")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AuthError("Admin access required")
    return user
