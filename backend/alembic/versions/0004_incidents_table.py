"""Create incidents table for Milestone 7 offline SOS synchronization.

Revision ID: 0004_incidents_table
Revises: 0003_rbac_tables
Create Date: 2026-11-10 11:30:00.000000

"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_incidents_table"
down_revision: Union[str, None] = "0003_rbac_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("zone_id", sa.String(length=64), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("incident_type", sa.String(length=64), nullable=False),
        sa.Column("urgency", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACKNOWLEDGED"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incidents_scenario_id", "incidents", ["scenario_id"], unique=False)
    op.create_index("ix_incidents_zone_id", "incidents", ["zone_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_incidents_zone_id", table_name="incidents")
    op.drop_index("ix_incidents_scenario_id", table_name="incidents")
    op.drop_table("incidents")

