"""add h3_cell to gps_points and questions

Revision ID: 2c86a2539939
Revises: 2d8c7899bb9e
Create Date: 2026-04-08 20:47:29.726655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2c86a2539939'
down_revision: Union[str, Sequence[str], None] = '2d8c7899bb9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('gps_points', sa.Column('h3_cell', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_gps_points_h3_cell'), 'gps_points', ['h3_cell'], unique=False)
    op.add_column('questions', sa.Column('h3_cell', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_questions_h3_cell'), 'questions', ['h3_cell'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_questions_h3_cell'), table_name='questions')
    op.drop_column('questions', 'h3_cell')
    op.drop_index(op.f('ix_gps_points_h3_cell'), table_name='gps_points')
    op.drop_column('gps_points', 'h3_cell')
