"""add knowledge_based to modeltype enum

Revision ID: 005_add_modeltype_knowledge_based
Revises: 004_add_user_profiles
Create Date: 2026-03-14
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_modeltype_knowledge_based"
down_revision = "005_add_modeltype_kb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: kept only to preserve history when the kb migration already ran.
    pass


def downgrade() -> None:
    # Downgrade is a no-op because removing enum values is not supported safely.
    pass
