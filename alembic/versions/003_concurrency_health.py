"""Add concurrency limits and health monitoring columns.

Revision ID: 003
Revises: 002
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agents table
    op.add_column("agents", sa.Column("max_concurrent_tasks", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("agents", sa.Column("active_task_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agents", sa.Column("health_status", sa.String(20), nullable=False, server_default="unknown"))
    op.add_column("agents", sa.Column("health_consecutive_fails", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agents", sa.Column("health_last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agents", sa.Column("health_last_success_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agents", sa.Column("health_avg_latency_ms", sa.Float(), nullable=True))
    op.add_column("agents", sa.Column("auto_offline_at", sa.DateTime(timezone=True), nullable=True))

    # external_agents table
    op.add_column("external_agents", sa.Column("max_concurrent_tasks", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("external_agents", sa.Column("active_task_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("external_agents", "active_task_count")
    op.drop_column("external_agents", "max_concurrent_tasks")

    op.drop_column("agents", "auto_offline_at")
    op.drop_column("agents", "health_avg_latency_ms")
    op.drop_column("agents", "health_last_success_at")
    op.drop_column("agents", "health_last_checked_at")
    op.drop_column("agents", "health_consecutive_fails")
    op.drop_column("agents", "health_status")
    op.drop_column("agents", "active_task_count")
    op.drop_column("agents", "max_concurrent_tasks")
