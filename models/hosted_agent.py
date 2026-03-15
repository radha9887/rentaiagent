import uuid
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from models import Base, TimestampMixin


class HostedAgent(Base, TimestampMixin):
    __tablename__ = "hosted_agents"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    lambda_arn = Column(Text, nullable=True)
    s3_code_key = Column(Text, nullable=True)
    runtime = Column(Text, default="python3.12")
    memory_mb = Column(Integer, default=256)
    timeout_sec = Column(Integer, default=60)
    max_concurrency = Column(Integer, default=5)
    env_vars_keys = Column(ARRAY(String), default=list)
    code_version = Column(Integer, default=0)
    code_size_bytes = Column(BigInteger, nullable=True)
    deploy_status = Column(Text, default="pending")
    deploy_error = Column(Text, nullable=True)
    last_health_at = Column(DateTime(timezone=True), nullable=True)
    last_invoked_at = Column(DateTime(timezone=True), nullable=True)
    invocation_count = Column(BigInteger, default=0)

    agent = relationship("Agent", backref="hosted_agent", uselist=False)
