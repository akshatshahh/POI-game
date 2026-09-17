"""Add selected_poi_ids JSON column to answers for multi-select.

Players can now select multiple POIs they consider likely. The existing
selected_poi_id column stays as the primary pick (first in the list);
selected_poi_ids stores the full set as a JSON array.

Revision ID: f1a2b3c4d5e6
Revises: a9d41e07b2c5
Create Date: 2026-09-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "a9d41e07b2c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "answers",
        sa.Column("selected_poi_ids", postgresql.JSONB(), nullable=True),
    )
    # Backfill: wrap existing single selections into a one-element array.
    op.execute("UPDATE answers SET selected_poi_ids = jsonb_build_array(selected_poi_id)")


def downgrade() -> None:
    op.drop_column("answers", "selected_poi_ids")
