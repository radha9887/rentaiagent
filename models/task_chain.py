"""Task chain model — tracks multi-hop task relationships."""

import uuid
from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from models import Base


class TaskChain(Base):
    """Links parent and child tasks in a multi-hop chain."""

    __tablename__ = "task_chain"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    root_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    child_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    depth = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
