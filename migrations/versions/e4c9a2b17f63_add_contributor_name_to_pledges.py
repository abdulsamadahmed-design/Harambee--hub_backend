"""add contributor name to pledges

Revision ID: e4c9a2b17f63
Revises: c3a7e91b5d20
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa


revision = "e4c9a2b17f63"
down_revision = "c3a7e91b5d20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pledges",
        sa.Column("contributor_name", sa.String(length=100), nullable=True),
    )


def downgrade():
    op.drop_column("pledges", "contributor_name")
