"""Add pgvector embeddings and wilson_score

Revision ID: 004
Revises: 003
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS description_embedding vector(1536)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS agents_embedding_idx ON agents "
        "USING hnsw (description_embedding vector_cosine_ops)"
    )
    op.add_column("agent_stats", sa.Column("wilson_score", sa.Float, server_default="0"))


def downgrade() -> None:
    op.drop_column("agent_stats", "wilson_score")
    op.execute("DROP INDEX IF EXISTS agents_embedding_idx")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS description_embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
