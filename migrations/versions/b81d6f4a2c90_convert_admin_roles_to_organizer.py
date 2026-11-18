"""
Preserve existing administrator roles.

Revision ID: b81d6f4a2c90
Revises: 725bcf67ad35
Create Date: 2026-11-17
"""

revision = "b81d6f4a2c90"
down_revision = "725bcf67ad35"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve existing admin accounts.
    # Admin privileges are required by the application.
    pass


def downgrade():
    # No database changes were made.
    pass
