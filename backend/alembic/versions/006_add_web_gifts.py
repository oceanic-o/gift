"""add web_gifts table

Revision ID: 006_add_web_gifts
Revises: 005_add_modeltype_knowledge_based
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_add_web_gifts"
down_revision = "005_add_modeltype_knowledge_based"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_gifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gift_id", sa.Integer(), sa.ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("gift_id", name="uq_web_gifts_gift_id"),
        sa.UniqueConstraint("source_url", name="uq_web_gifts_source_url"),
    )
    op.create_index("ix_web_gifts_source_url", "web_gifts", ["source_url"])


def downgrade() -> None:
    op.drop_index("ix_web_gifts_source_url", table_name="web_gifts")
    op.drop_table("web_gifts")
