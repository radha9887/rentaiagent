from sqlalchemy.orm import DeclarativeBase
import uuid
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


from models.user import User, APIKey  # noqa: E402, F401
from models.agent import Agent, AgentSkill  # noqa: E402, F401
from models.task import Task  # noqa: E402, F401
from models.credit import CreditAccount, Transaction, Escrow  # noqa: E402, F401
from models.rating import Rating, AgentStats  # noqa: E402, F401
