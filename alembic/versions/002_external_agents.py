"""external agents, task chains, webhooks

Revision ID: 002
Revises: 001
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── external_agents ──────────────────────────────────────────────────
    op.create_table(
        "external_agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("agent_card_url", sa.String(500), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("endpoint_url", sa.String(500), nullable=True),
        sa.Column("agent_card_cache", postgresql.JSONB(), nullable=True),
        sa.Column("card_last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(20), server_default="pending"),
        sa.Column("verification_error", sa.Text(), nullable=True),
        sa.Column("health_status", sa.String(20), server_default="unknown"),
        sa.Column("health_last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("health_check_count", sa.Integer(), server_default="0"),
        sa.Column("health_fail_count", sa.Integer(), server_default="0"),
        sa.Column("trust_tier", sa.String(20), server_default="new"),
        sa.Column("is_listed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("pricing_model", sa.String(20), server_default="per_task"),
        sa.Column("price_per_task", sa.Numeric(12, 4), nullable=True),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("protocols", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("skills", postgresql.JSONB(), nullable=True),
        sa.Column("stats", postgresql.JSONB(), server_default='{"total_tasks":0,"completed":0,"failed":0,"avg_response_ms":0,"success_rate":0}'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_external_agents_owner_id", "external_agents", ["owner_id"])
    op.create_index("ix_external_agents_verification_status", "external_agents", ["verification_status"])
    op.create_index("ix_external_agents_is_listed", "external_agents", ["is_listed"])

    # ── task chain columns on tasks ──────────────────────────────────────
    op.add_column("tasks", sa.Column("parent_task_id", sa.UUID(), nullable=True))
    op.add_column("tasks", sa.Column("root_task_id", sa.UUID(), nullable=True))
    op.add_column("tasks", sa.Column("hop_depth", sa.Integer(), server_default="0"))
    op.add_column("tasks", sa.Column("is_subtask", sa.Boolean(), server_default=sa.text("false")))
    op.create_foreign_key("fk_tasks_parent_task", "tasks", "tasks", ["parent_task_id"], ["id"])
    op.create_foreign_key("fk_tasks_root_task", "tasks", "tasks", ["root_task_id"], ["id"])

    # ── task_chain ───────────────────────────────────────────────────────
    op.create_table(
        "task_chain",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("root_task_id", sa.UUID(), nullable=False),
        sa.Column("parent_task_id", sa.UUID(), nullable=False),
        sa.Column("child_task_id", sa.UUID(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["root_task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["parent_task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["child_task_id"], ["tasks.id"]),
    )
    op.create_index("ix_task_chain_root_task_id", "task_chain", ["root_task_id"])
    op.create_index("ix_task_chain_parent_task_id", "task_chain", ["parent_task_id"])

    # ── webhook_subscriptions ────────────────────────────────────────────
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("callback_url", sa.String(500), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("secret", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
    )
    op.create_index("ix_webhook_subscriptions_user_id", "webhook_subscriptions", ["user_id"])
    op.create_index("ix_webhook_subscriptions_task_id", "webhook_subscriptions", ["task_id"])


def downgrade() -> None:
    op.drop_table("webhook_subscriptions")
    op.drop_table("task_chain")
    op.drop_column("tasks", "is_subtask")
    op.drop_column("tasks", "hop_depth")
    op.drop_constraint("fk_tasks_root_task", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_parent_task", "tasks", type_="foreignkey")
    op.drop_column("tasks", "root_task_id")
    op.drop_column("tasks", "parent_task_id")
    op.drop_table("external_agents")
