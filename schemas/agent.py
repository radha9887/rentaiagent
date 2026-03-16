from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class SkillInput(BaseModel):
    skill_tag: str
    category: Optional[str] = None
    proficiency: float = Field(default=0.5, ge=0, le=1)


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9\-]+$")
    description: Optional[str] = None
    endpoint_url: Optional[str] = None
    endpoint_type: str = "rest"
    pricing_model: str = "per_task"
    price_per_task: Decimal = Decimal("0")
    currency: str = "credits"
    health_check_url: str
    version: Optional[str] = None
    framework: Optional[str] = None
    protocols: List[str] = []
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    skills: List[SkillInput] = []
    max_concurrent_tasks: int = 10


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    endpoint_url: Optional[str] = None
    endpoint_type: Optional[str] = None
    pricing_model: Optional[str] = None
    price_per_task: Optional[Decimal] = None
    currency: Optional[str] = None
    health_check_url: Optional[str] = None
    version: Optional[str] = None
    framework: Optional[str] = None
    protocols: Optional[List[str]] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    skills: Optional[List[SkillInput]] = None
    max_concurrent_tasks: Optional[int] = None
    status: Optional[str] = None


class SkillResponse(BaseModel):
    id: UUID
    skill_tag: str
    category: Optional[str] = None
    proficiency: float
    task_count: int
    avg_latency_ms: Optional[float] = None
    success_rate: float

    model_config = {"from_attributes": True}


class AgentStatsResponse(BaseModel):
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_rating: float = 0.0
    avg_response_ms: float = 0.0
    acceptance_rate: float = 1.0
    total_earned: Decimal = Decimal("0")
    rating_count: int = 0
    last_task_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    endpoint_url: Optional[str] = None
    endpoint_type: str
    pricing_model: str
    price_per_task: Decimal
    currency: str
    status: str
    trust_tier: str
    version: Optional[str] = None
    framework: Optional[str] = None
    protocols: List[str]
    skills: List[SkillResponse] = []
    stats: Optional[AgentStatsResponse] = None
    max_concurrent_tasks: int = 10
    active_task_count: int = 0
    health_status: str = "unknown"
    health_check_url: Optional[str] = None
    health_avg_latency_ms: Optional[float] = None
    health_last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    pricing_model: str
    price_per_task: Decimal
    currency: str
    status: str
    trust_tier: str
    framework: Optional[str] = None

    model_config = {"from_attributes": True}
