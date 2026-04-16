"""add unique constraint on answers (user_id, question_id)

Revision ID: 9ec3e7d8af47
Revises: 2c86a2539939
Create Date: 2026-04-16 01:08:40.021589

"""
from typing import Sequence, Union

from alembic import op

revision: str = '9ec3e7d8af47'
down_revision: Union[str, Sequence[str], None] = '2c86a2539939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_answers_user_question", "answers", ["user_id", "question_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_answers_user_question", "answers", type_="unique")
