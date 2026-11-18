"""remove anonymous pledge behavior

Revision ID: c3a7e91b5d20
Revises: b81d6f4a2c90
Create Date: 2026-11-18
"""
from alembic import op


revision = "c3a7e91b5d20"
down_revision = "b81d6f4a2c90"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE pledges SET is_anonymous = FALSE")


def downgrade():
    # Existing contributor identities cannot safely be made anonymous again.
    pass
