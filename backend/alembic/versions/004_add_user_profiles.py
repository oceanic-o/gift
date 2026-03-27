"""Add user_profiles table

Revision ID: 004_add_user_profiles
Revises: 003_add_user_profile_fields
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

revision = "004_add_user_profiles"
down_revision = "003_add_user_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("age", sa.String(length=20), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("hobbies", sa.Text(), nullable=True),
        sa.Column("relationship", sa.String(length=100), nullable=True),
        sa.Column("occasion", sa.String(length=100), nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")
