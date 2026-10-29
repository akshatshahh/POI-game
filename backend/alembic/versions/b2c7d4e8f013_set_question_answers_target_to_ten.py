"""Store the Jaccard completion cap of 10 on every question.

answers_target was the old majority-vote floor of 3. The live rule completes
a question after 10 eligible responses, regardless of Jaccard, so the column
default and existing rows are set to 10.

Revision ID: b2c7d4e8f013
Revises: e7c9a1d3f502
Create Date: 2026-10-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c7d4e8f013"
down_revision: Union[str, Sequence[str], None] = "e7c9a1d3f502"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "questions",
        "answers_target",
        existing_type=sa.Integer(),
        server_default="10",
        existing_nullable=False,
    )
    # Only open questions need the new cap. Locked rows keep the target
    # they were collected under so exports can tell old 3/5 locks from
    # Jaccard-era completes at 10.
    op.execute(
        sa.text(
            "UPDATE questions SET answers_target = 10 WHERE locked_at IS NULL"
        )
    )


def downgrade() -> None:
    op.alter_column(
        "questions",
        "answers_target",
        existing_type=sa.Integer(),
        server_default="3",
        existing_nullable=False,
    )
