import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models import Base, TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    requester_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    provider_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    skill_requested = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    payload_size_bytes = Column(Integer, default=0)
    max_wait_seconds = Column(Integer, default=300)
    priority = Column(String(20), default="normal")  # low | normal | high | urgent
    status = Column(String(20), default="pending", index=True)  # pending | escrowed | routed | processing | completed | failed | cancelled
    escrowed_at = Column(DateTime(timezone=True), nullable=True)
    routed_at = Column(DateTime(timezone=True), nullable=True)
    processing_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    quoted_price = Column(Numeric(12, 4), nullable=False)
    actual_price = Column(Numeric(12, 4), nullable=True)
    platform_fee = Column(Numeric(12, 4), nullable=True)
    currency = Column(String(3), default="INR")
    result = Column(JSONB, nullable=True)
    result_size_bytes = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)

    # Multi-hop task chain fields
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    root_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    hop_depth = Column(Integer, default=0)
    is_subtask = Column(Boolean, default=False)
