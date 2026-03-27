"""add knowledge_based to modeltype enum

Revision ID: 005_add_modeltype_kb
Revises: 004_add_user_profiles
Create Date: 2026-03-14
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_modeltype_kb"
down_revision = "004_add_user_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE modeltype ADD VALUE IF NOT EXISTS 'knowledge_based'")


def downgrade() -> None:
    # Downgrade is a no-op because removing enum values is not supported safely.
    pass
