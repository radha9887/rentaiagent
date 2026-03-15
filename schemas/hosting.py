from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class HostedAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9\-]+$")
    description: Optional[str] = None
    skills: List[str] = Field(min_length=1)
    price_per_task: Decimal = Field(ge=0)
    runtime: str = "python3.12"
    timeout_sec: int = Field(default=60, ge=5, le=300)
    memory_mb: int = Field(default=256, ge=128, le=1024)


class HostedAgentResponse(BaseModel):
    agent_id: UUID
    runtime: str
    memory_mb: int
    timeout_sec: int
    max_concurrency: int
    code_version: int
    code_size_bytes: Optional[int] = None
    deploy_status: str
    deploy_error: Optional[str] = None
    last_health_at: Optional[datetime] = None
    last_invoked_at: Optional[datetime] = None
    invocation_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnvVarsUpdate(BaseModel):
    env_vars: Dict[str, str]


class CodeUploadResponse(BaseModel):
    version: int
    deploy_status: str
    message: str


class LogEntry(BaseModel):
    timestamp: Optional[datetime] = None
    message: str


class HostedAgentLogsResponse(BaseModel):
    logs: List[LogEntry]
    function_name: str
