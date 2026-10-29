"""Store the ordered place ids each player was shown.

The frozen candidate set on the question is a superset. Each player sees at
most eight of those places. Persist that slice on the answer so exports can
reconstruct the choice set. Historical rows stay null.

Revision ID: c3d8e5f9a124
Revises: b2c7d4e8f013
Create Date: 2026-10-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c3d8e5f9a124"
down_revision: Union[str, Sequence[str], None] = "b2c7d4e8f013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "answers",
        sa.Column("displayed_poi_ids", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("answers", "displayed_poi_ids")
