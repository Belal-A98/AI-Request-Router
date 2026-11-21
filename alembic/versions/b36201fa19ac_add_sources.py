"""Add operator-provisioned source key registry.

Revision ID: b36201fa19ac
Revises: c421ad3e73e7
"""
from alembic import op
import sqlalchemy as sa

revision = 'b36201fa19ac'
down_revision = 'c421ad3e73e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sources',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('key_digest', sa.String(64), nullable=False, unique=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('sources')
