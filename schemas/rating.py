from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class RatingCreate(BaseModel):
    task_id: UUID
    rated_agent_id: Optional[UUID] = None
    overall_score: float = Field(ge=1, le=5)
    accuracy_score: Optional[float] = Field(default=None, ge=1, le=5)
    speed_score: Optional[float] = Field(default=None, ge=1, le=5)
    feedback: Optional[str] = None
    output_accepted: bool = True


class RatingResponse(BaseModel):
    id: UUID
    task_id: UUID
    rater_user_id: UUID
    rated_agent_id: UUID
    overall_score: float
    accuracy_score: Optional[float] = None
    speed_score: Optional[float] = None
    feedback: Optional[str] = None
    response_time_ms: Optional[int] = None
    output_accepted: bool
    created_at: datetime

    model_config = {"from_attributes": True}
