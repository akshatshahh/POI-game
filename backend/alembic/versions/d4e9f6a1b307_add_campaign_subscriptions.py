"""Add campaign notification subscriptions.

Revision ID: d4e9f6a1b307
Revises: c3d8e5f9a124
Create Date: 2026-10-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4e9f6a1b307"
down_revision: Union[str, Sequence[str], None] = "c3d8e5f9a124"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "consent_version",
            sa.String(length=50),
            server_default="campaign-notification-v1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_campaign_subscriptions_email"),
        "campaign_subscriptions",
        ["email"],
        unique=True,
    )
    op.create_index(
        op.f("ix_campaign_subscriptions_user_id"),
        "campaign_subscriptions",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_campaign_subscriptions_user_id"),
        table_name="campaign_subscriptions",
    )
    op.drop_index(
        op.f("ix_campaign_subscriptions_email"),
        table_name="campaign_subscriptions",
    )
    op.drop_table("campaign_subscriptions")
