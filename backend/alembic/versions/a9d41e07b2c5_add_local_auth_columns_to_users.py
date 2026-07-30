"""Add local-auth columns to users (schema catch-up).

The local username/password login feature added username and password_hash
to the User model, and relaxed google_id to nullable (local accounts have
no Google identity) — but no migration was written at the time. Existing
databases were patched by hand; any database built purely from migrations
was missing the columns. This migration closes that drift.

Revision ID: a9d41e07b2c5
Revises: c4e8d2b91f37
Create Date: 2026-07-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9d41e07b2c5"
down_revision: Union[str, Sequence[str], None] = "c4e8d2b91f37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.alter_column("users", "google_id", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "google_id", existing_type=sa.String(length=255), nullable=False)
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
