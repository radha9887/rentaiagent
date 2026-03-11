import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from models import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # user | admin
    is_active = Column(Boolean, default=True, nullable=False)

    api_keys = relationship("APIKey", back_populates="user", lazy="selectin")
    agents = relationship("Agent", back_populates="owner", lazy="selectin")
    credit_account = relationship("CreditAccount", back_populates="user", uselist=False, lazy="selectin")


class APIKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)
    key_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False, default="default")
    scopes = Column(ARRAY(String), default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="api_keys")
