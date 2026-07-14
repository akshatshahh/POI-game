"""Add explicit score component columns to answers.

Previously only the total score_awarded was stored, and the consensus bonus
had to be decoded from the score's magnitude. This migration adds the
components and backfills them using that decoding one last time (with the
scoring constants as of this revision: base 5, distance bonus 1-5,
consensus bonus 10).

Revision ID: 7b3f5a1c9d20
Revises: 9ec3e7d8af47
Create Date: 2026-07-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b3f5a1c9d20"
down_revision: Union[str, Sequence[str], None] = "9ec3e7d8af47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "answers",
        sa.Column("base_points", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "answers",
        sa.Column("distance_bonus", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "answers",
        sa.Column("consensus_bonus", sa.Integer(), nullable=False, server_default="0"),
    )

    # Backfill from score_awarded. Totals above base + max distance bonus (10)
    # must include the consensus bonus (10); anything else has none.
    op.execute(
        """
        UPDATE answers SET
            base_points = 5,
            consensus_bonus = CASE WHEN score_awarded > 10 THEN 10 ELSE 0 END,
            distance_bonus = CASE
                WHEN score_awarded > 10 THEN score_awarded - 10 - 5
                WHEN score_awarded >= 5 THEN score_awarded - 5
                ELSE 0
            END
        """
    )


def downgrade() -> None:
    op.drop_column("answers", "consensus_bonus")
    op.drop_column("answers", "distance_bonus")
    op.drop_column("answers", "base_points")
