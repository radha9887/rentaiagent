"""GET /v1/agents/{slug}/ratings — mounted separately to avoid circular prefix issues."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from db import get_db
from models.agent import Agent
from models.rating import Rating
from schemas.rating import RatingResponse
from schemas.common import CursorPage
from utils.errors import NotFoundError
from utils.pagination import encode_cursor, decode_cursor

router = APIRouter(prefix="/v1/agents", tags=["ratings"])


@router.get("/{slug}/ratings", response_model=CursorPage[RatingResponse])
async def get_agent_ratings(
    slug: str,
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")

    query = select(Rating).where(Rating.rated_agent_id == agent.id).order_by(Rating.created_at.desc())
    if cursor:
        from uuid import UUID
        query = query.where(Rating.id < UUID(decode_cursor(cursor)))
    query = query.limit(limit + 1)
    result = (await db.execute(query)).scalars().all()
    has_more = len(result) > limit
    items = result[:limit]
    next_cursor = encode_cursor(str(items[-1].id)) if has_more and items else None
    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
