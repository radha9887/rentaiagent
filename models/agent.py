import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import relationship
from models import Base, TimestampMixin

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    endpoint_url = Column(String(500), nullable=True)
    endpoint_type = Column(String(20), default="rest")  # rest | mcp | a2a
    pricing_model = Column(String(20), default="per_task")  # per_task | per_minute | subscription
    price_per_task = Column(Numeric(12, 4), default=0)
    price_reserved = Column(Numeric(12, 4), default=0)
    currency = Column(String(10), default="credits")
    status = Column(String(20), default="pending", index=True)  # pending | online | offline | suspended
    health_check_url = Column(String(500), nullable=True)
    last_health_at = Column(DateTime(timezone=True), nullable=True)
    trust_tier = Column(String(20), default="new")  # new | bronze | silver | gold | platinum
    version = Column(String(50), nullable=True)
    framework = Column(String(50), nullable=True)
    protocols = Column(ARRAY(String), default=list)
    metadata_ = Column("metadata", JSONB, default=dict)
    skills_vector = Column(TSVECTOR, nullable=True)
    description_embedding = Column(Vector(1536), nullable=True) if Vector else None

    # Concurrency & health monitoring
    max_concurrent_tasks = Column(Integer, default=10, nullable=False)
    active_task_count = Column(Integer, default=0, nullable=False)
    health_status = Column(String(20), default="unknown")  # healthy | unhealthy | unknown
    health_consecutive_fails = Column(Integer, default=0)
    health_last_checked_at = Column(DateTime(timezone=True), nullable=True)
    health_last_success_at = Column(DateTime(timezone=True), nullable=True)
    health_avg_latency_ms = Column(Float, nullable=True)
    auto_offline_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="agents")
    skills = relationship("AgentSkill", back_populates="agent", lazy="selectin", cascade="all, delete-orphan")
    stats = relationship("AgentStats", back_populates="agent", uselist=False, lazy="selectin")


class AgentSkill(Base, TimestampMixin):
    __tablename__ = "agent_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_tag = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True)
    proficiency = Column(Float, default=0.5)
    task_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, nullable=True)
    success_rate = Column(Float, default=1.0)

    agent = relationship("Agent", back_populates="skills")
