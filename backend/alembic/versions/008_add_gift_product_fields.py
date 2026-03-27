"""Add gift product fields (placeholder).

Revision ID: 008_add_gift_product_fields
Revises: 007_add_preferences_and_gift_fields
Create Date: 2026-03-22
"""

revision = "008_add_gift_product_fields"
down_revision = "007_add_preferences_and_gift_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
	# No schema changes required; dataset fields are mapped into existing columns.
	pass


def downgrade() -> None:
	pass
