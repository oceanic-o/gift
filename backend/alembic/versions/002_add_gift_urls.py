"""Add image_url and product_url to gifts

Revision ID: 002
Revises: 001
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_gift_urls"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gifts", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("gifts", sa.Column("product_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("gifts", "product_url")
    op.drop_column("gifts", "image_url")
