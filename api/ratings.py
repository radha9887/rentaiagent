from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from db import get_db
from models.user import User
from models.agent import Agent
from models.task import Task
from models.rating import Rating, AgentStats
from schemas.rating import RatingCreate, RatingResponse
from schemas.common import CursorPage
from utils.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError as AppValidationError
from utils.pagination import encode_cursor, decode_cursor
from core.trust import calculate_trust_tier
from api.deps import get_current_user

router = APIRouter(prefix="/v1/ratings", tags=["ratings"])


@router.post("", response_model=RatingResponse, status_code=201)
async def submit_rating(data: RatingCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = (await db.execute(select(Task).where(Task.id == data.task_id))).scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    if task.status != "completed":
        raise AppValidationError("Can only rate completed tasks")
    if task.requester_user_id != user.id:
        raise ForbiddenError("Only task requester can rate")

    existing = (await db.execute(select(Rating).where(Rating.task_id == data.task_id, Rating.rater_user_id == user.id))).scalar_one_or_none()
    if existing:
        raise ConflictError("Already rated this task")

    response_ms = None
    if task.escrowed_at and task.completed_at:
        response_ms = int((task.completed_at - task.escrowed_at).total_seconds() * 1000)

    rating = Rating(
        task_id=data.task_id, rated_agent_id=data.rated_agent_id, rater_user_id=user.id,
        overall_score=data.overall_score, accuracy_score=data.accuracy_score,
        speed_score=data.speed_score, feedback=data.feedback,
        response_time_ms=response_ms, output_accepted=data.output_accepted,
    )
    db.add(rating)

    # Update agent stats
    stats = (await db.execute(select(AgentStats).where(AgentStats.agent_id == data.rated_agent_id).with_for_update())).scalar_one_or_none()
    if stats:
        stats.rating_count += 1
        stats.avg_rating = ((stats.avg_rating * (stats.rating_count - 1)) + data.overall_score) / stats.rating_count
        if response_ms:
            stats.avg_response_ms = ((stats.avg_response_ms * (stats.rating_count - 1)) + response_ms) / stats.rating_count
        # Update trust tier
        agent = (await db.execute(select(Agent).where(Agent.id == data.rated_agent_id))).scalar_one()
        agent.trust_tier = calculate_trust_tier(stats)

    await db.commit()
    await db.refresh(rating)
    return rating
