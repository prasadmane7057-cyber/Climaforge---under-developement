"""Add family_id to refresh_tokens for replay detection and family revocation.

Revision ID: 0002_add_token_family_id
Revises: 0001_initial_auth_tables
Create Date: 2026-11-05 21:55:00.000000

"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_add_token_family_id"
down_revision: Union[str, None] = "0001_initial_auth_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "family_id",
                sa.String(length=36),
                server_default="",
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_refresh_tokens_family_id"),
            ["family_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_refresh_tokens_family_id"))
        batch_op.drop_column("family_id")

