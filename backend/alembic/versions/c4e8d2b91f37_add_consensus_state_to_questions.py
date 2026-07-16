"""Add consensus lifecycle state to questions and distance to answers.

Questions gain: a frozen candidate set (for reproducible exports), a
candidate-density difficulty proxy, a per-question annotation target,
vote totals, the consensus label + confidence, and a lock timestamp.
Answers gain the selected-POI distance as an ML covariate.

Existing questions are backfilled with their current vote totals; their
candidate sets are backfilled lazily on next access by the application.

Revision ID: c4e8d2b91f37
Revises: 7b3f5a1c9d20
Create Date: 2026-07-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c4e8d2b91f37"
down_revision: Union[str, Sequence[str], None] = "7b3f5a1c9d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("candidates", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("candidate_density", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "questions",
        sa.Column("answers_target", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "questions",
        sa.Column("votes_total", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "questions",
        sa.Column("consensus_poi_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("consensus_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "answers",
        sa.Column("selected_distance_meters", sa.Float(), nullable=True),
    )

    op.execute(
        """
        UPDATE questions SET votes_total = (
            SELECT COUNT(*) FROM answers WHERE answers.question_id = questions.id
        )
        """
    )


def downgrade() -> None:
    op.drop_column("answers", "selected_distance_meters")
    op.drop_column("questions", "locked_at")
    op.drop_column("questions", "consensus_confidence")
    op.drop_column("questions", "consensus_poi_id")
    op.drop_column("questions", "votes_total")
    op.drop_column("questions", "answers_target")
    op.drop_column("questions", "candidate_density")
    op.drop_column("questions", "candidates")
