import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from models import Base


class CreditAccount(Base):
    __tablename__ = "credit_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    balance = Column(Numeric(14, 4), default=0, nullable=False)
    total_earned = Column(Numeric(14, 4), default=0, nullable=False)
    total_spent = Column(Numeric(14, 4), default=0, nullable=False)
    total_fees_paid = Column(Numeric(14, 4), default=0, nullable=False)
    currency = Column(String(3), default="INR")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (CheckConstraint("balance >= 0", name="ck_balance_non_negative"),)

    user = relationship("User", back_populates="credit_account")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_account_id = Column(UUID(as_uuid=True), ForeignKey("credit_accounts.id"), nullable=True)
    to_account_id = Column(UUID(as_uuid=True), ForeignKey("credit_accounts.id"), nullable=True)
    type = Column(String(30), nullable=False)  # topup | escrow_hold | escrow_release | escrow_refund | fee
    amount = Column(Numeric(14, 4), nullable=False)
    currency = Column(String(3), default="INR")
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    escrow_id = Column(UUID(as_uuid=True), ForeignKey("escrows.id"), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    status = Column(String(20), default="completed")  # pending | completed | failed
    description = Column(String(500), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Escrow(Base):
    __tablename__ = "escrows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), unique=True, nullable=False)
    payer_account_id = Column(UUID(as_uuid=True), ForeignKey("credit_accounts.id"), nullable=False)
    amount = Column(Numeric(14, 4), nullable=False)
    platform_fee = Column(Numeric(14, 4), nullable=False)
    status = Column(String(20), default="held")  # held | released | refunded | expired
    held_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
