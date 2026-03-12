from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class TaskCreate(BaseModel):
    provider_agent_id: UUID
    skill_requested: str
    description: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    max_wait_seconds: int = Field(default=300, ge=10, le=3600)
    priority: str = "normal"
    requester_agent_id: Optional[UUID] = None


class TaskResponse(BaseModel):
    id: UUID
    requester_agent_id: Optional[UUID] = None
    requester_user_id: UUID
    provider_agent_id: UUID
    skill_requested: str
    description: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    priority: str
    status: str
    quoted_price: Decimal
    actual_price: Optional[Decimal] = None
    platform_fee: Optional[Decimal] = None
    currency: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    escrowed_at: Optional[datetime] = None
    routed_at: Optional[datetime] = None
    processing_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskComplete(BaseModel):
    result: Dict[str, Any]
    actual_price: Optional[Decimal] = None


class AutoTaskCreate(BaseModel):
    skill_requested: str
    description: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    max_wait_seconds: int = Field(default=300, ge=10, le=3600)
    preferences: Optional[Dict[str, Any]] = None  # {max_price, min_rating, priority}
