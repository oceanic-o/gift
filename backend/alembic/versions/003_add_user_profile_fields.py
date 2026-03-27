"""Add user profile fields

Revision ID: 003_add_user_profile_fields
Revises: 002_add_gift_urls
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_user_profile_fields"
down_revision = "002_add_gift_urls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("provider", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("given_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("family_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("locale", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locale")
    op.drop_column("users", "family_name")
    op.drop_column("users", "given_name")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "provider")
