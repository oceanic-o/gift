"""Add user preference fields and gift tags/age_group

Revision ID: 007_add_preferences_and_gift_fields
Revises: 006_add_web_gifts
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision = "007_add_preferences_and_gift_fields"
down_revision = "006_add_web_gifts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("favorite_categories", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("occasions", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("gifting_for_ages", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("interests", sa.JSON(), nullable=True))

    op.add_column("gifts", sa.Column("age_group", sa.String(length=50), nullable=True))
    op.add_column("gifts", sa.Column("tags", sa.Text(), nullable=True))
    op.create_index("ix_gifts_age_group", "gifts", ["age_group"])


def downgrade() -> None:
    op.drop_index("ix_gifts_age_group", table_name="gifts")
    op.drop_column("gifts", "tags")
    op.drop_column("gifts", "age_group")

    op.drop_column("user_profiles", "interests")
    op.drop_column("user_profiles", "gifting_for_ages")
    op.drop_column("user_profiles", "occasions")
    op.drop_column("user_profiles", "favorite_categories")
