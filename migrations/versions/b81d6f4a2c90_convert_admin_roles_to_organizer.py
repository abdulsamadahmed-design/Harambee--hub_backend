"""convert legacy admin roles to organizer

Revision ID: b81d6f4a2c90
Revises: 725bcf67ad35
Create Date: 2026-11-17
"""
from alembic import op


revision = "b81d6f4a2c90"
down_revision = "725bcf67ad35"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE user SET role = 'organizer' WHERE role = 'admin'"
    )


def downgrade():
    # Intentionally irreversible: existing organizers must not be
    # incorrectly changed back to admin.
    pass
