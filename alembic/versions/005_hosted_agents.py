"""Add hosted_agents table

Revision ID: 005
Revises: 004
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hosted_agents",
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("lambda_arn", sa.Text, nullable=True),
        sa.Column("s3_code_key", sa.Text, nullable=True),
        sa.Column("runtime", sa.Text, server_default="python3.12"),
        sa.Column("memory_mb", sa.Integer, server_default="256"),
        sa.Column("timeout_sec", sa.Integer, server_default="60"),
        sa.Column("max_concurrency", sa.Integer, server_default="5"),
        sa.Column("env_vars_keys", ARRAY(sa.String), server_default="{}"),
        sa.Column("code_version", sa.Integer, server_default="0"),
        sa.Column("code_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("deploy_status", sa.Text, server_default="pending"),
        sa.Column("deploy_error", sa.Text, nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_invoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invocation_count", sa.BigInteger, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("hosted_agents")
