"""merge campaign and email verification migrations

Revision ID: daa9085ce83d
Revises: 4296890f297d, f2fffa369531
Create Date: 2026-11-15 00:18:14.689457

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'daa9085ce83d'
down_revision = ('4296890f297d', 'f2fffa369531')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
