"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("endpoint_url", sa.String(500), nullable=True),
        sa.Column("endpoint_type", sa.String(20), server_default="rest"),
        sa.Column("pricing_model", sa.String(20), server_default="per_task"),
        sa.Column("price_per_task", sa.Numeric(12, 4), server_default="0"),
        sa.Column("price_reserved", sa.Numeric(12, 4), server_default="0"),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("health_check_url", sa.String(500), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trust_tier", sa.String(20), server_default="new"),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("framework", sa.String(50), nullable=True),
        sa.Column("protocols", postgresql.ARRAY(sa.String())),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("skills_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agents_slug", "agents", ["slug"], unique=True)
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])
    op.create_index("ix_agents_status", "agents", ["status"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default="default"),
        sa.Column("scopes", postgresql.ARRAY(sa.String())),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    op.create_table(
        "credit_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("balance", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("total_fees_paid", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("balance >= 0", name="ck_balance_non_negative"),
    )
    op.create_index("ix_credit_accounts_user_id", "credit_accounts", ["user_id"], unique=True)

    op.create_table(
        "agent_skills",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("skill_tag", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("proficiency", sa.Float(), server_default="0.5"),
        sa.Column("task_count", sa.Integer(), server_default="0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("success_rate", sa.Float(), server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_skills_agent_id", "agent_skills", ["agent_id"])

    op.create_table(
        "agent_stats",
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("total_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_response_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("acceptance_rate", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("total_earned", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_task_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("agent_id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("requester_agent_id", sa.UUID(), nullable=True),
        sa.Column("requester_user_id", sa.UUID(), nullable=False),
        sa.Column("provider_agent_id", sa.UUID(), nullable=False),
        sa.Column("skill_requested", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("payload_size_bytes", sa.Integer()),
        sa.Column("max_wait_seconds", sa.Integer(), server_default="300"),
        sa.Column("priority", sa.String(20), server_default="normal"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("escrowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("routed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quoted_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("actual_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("platform_fee", sa.Numeric(12, 4), nullable=True),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("result_size_bytes", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["requester_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["provider_agent_id"], ["agents.id"]),
    )
    op.create_index("ix_tasks_requester_user_id", "tasks", ["requester_user_id"])
    op.create_index("ix_tasks_provider_agent_id", "tasks", ["provider_agent_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    op.create_table(
        "escrows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("payer_account_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("platform_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(20), server_default="held"),
        sa.Column("held_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["payer_account_id"], ["credit_accounts.id"]),
    )

    op.create_table(
        "ratings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("rater_agent_id", sa.UUID(), nullable=True),
        sa.Column("rated_agent_id", sa.UUID(), nullable=False),
        sa.Column("rater_user_id", sa.UUID(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("speed_score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("output_accepted", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["rater_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["rated_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["rater_user_id"], ["users.id"]),
    )
    op.create_index("ix_ratings_task_id", "ratings", ["task_id"])
    op.create_index("ix_ratings_rated_agent_id", "ratings", ["rated_agent_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("from_account_id", sa.UUID(), nullable=True),
        sa.Column("to_account_id", sa.UUID(), nullable=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("escrow_id", sa.UUID(), nullable=True),
        sa.Column("razorpay_payment_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="completed"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["from_account_id"], ["credit_accounts.id"]),
        sa.ForeignKeyConstraint(["to_account_id"], ["credit_accounts.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["escrow_id"], ["escrows.id"]),
    )


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("ratings")
    op.drop_table("escrows")
    op.drop_table("tasks")
    op.drop_table("agent_stats")
    op.drop_table("agent_skills")
    op.drop_table("credit_accounts")
    op.drop_table("api_keys")
    op.drop_table("agents")
    op.drop_table("users")
