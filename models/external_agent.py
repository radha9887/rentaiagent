"""External agent model — represents agents registered from outside the platform."""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from models import Base, TimestampMixin


class ExternalAgent(Base, TimestampMixin):
    """An agent hosted externally, discovered via its A2A agent card URL."""

    __tablename__ = "external_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_card_url = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    endpoint_url = Column(String(500), nullable=True)
    agent_card_cache = Column(JSONB, nullable=True)
    card_last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    verification_status = Column(String(20), default="pending")  # pending | verified | failed | suspended
    verification_error = Column(Text, nullable=True)
    health_status = Column(String(20), default="unknown")  # healthy | unhealthy | unknown
    health_last_checked_at = Column(DateTime(timezone=True), nullable=True)
    health_check_count = Column(Integer, default=0)
    health_fail_count = Column(Integer, default=0)
    trust_tier = Column(String(20), default="new")
    is_listed = Column(Boolean, default=False)
    pricing_model = Column(String(20), default="per_task")
    price_per_task = Column(Numeric(12, 4), nullable=True)
    currency = Column(String(3), default="INR")
    protocols = Column(ARRAY(String), nullable=True)
    skills = Column(JSONB, nullable=True)
    stats = Column(JSONB, default=lambda: {"total_tasks": 0, "completed": 0, "failed": 0, "avg_response_ms": 0, "success_rate": 0})

    max_concurrent_tasks = Column(Integer, default=5, nullable=False)
    active_task_count = Column(Integer, default=0, nullable=False)

    owner = relationship("User")
