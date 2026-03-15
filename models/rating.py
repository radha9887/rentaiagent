import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Text, Boolean, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models import Base


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    rater_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    rated_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    rater_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    accuracy_score = Column(Float, nullable=True)
    speed_score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    output_accepted = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentStats(Base):
    __tablename__ = "agent_stats"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    total_tasks = Column(Integer, default=0, nullable=False)
    completed_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    avg_rating = Column(Float, default=0.0, nullable=False)
    avg_response_ms = Column(Float, default=0.0, nullable=False)
    acceptance_rate = Column(Float, default=1.0, nullable=False)
    total_earned = Column(Numeric(14, 4), default=0, nullable=False)
    rating_count = Column(Integer, default=0, nullable=False)
    wilson_score = Column(Float, default=0.0)
    last_task_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    agent = relationship("Agent", back_populates="stats")
