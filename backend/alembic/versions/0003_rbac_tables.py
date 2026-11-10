"""Create RBAC tables and scenario access grants with default seed data.

Revision ID: 0003_rbac_tables
Revises: 0002_add_token_family_id
Create Date: 2026-11-09 20:30:00.000000

"""
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Union
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_rbac_tables"
down_revision: Union[str, None] = "0002_add_token_family_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default roles and descriptions
DEFAULT_ROLES = [
    ("VIEWER", "Read-only access to scenarios, grounded chatbot, and audit trail"),
    ("ANALYST", "Analytical execution of scenarios, ad-hoc runs, and ML predictions"),
    ("OPERATOR", "Operational execution, intervention recommendations, and approvals"),
    ("AUDITOR", "Dedicated compliance read access to audit logs"),
    ("ADMIN", "Full administrative control of users, roles, and scenario access grants"),
]

# 15 Granular permissions
DEFAULT_PERMISSIONS = [
    ("scenario.read", "View scenario catalog and detailed parameters"),
    ("scenario.run", "Execute deterministic flood risk engine for scenarios"),
    ("scenario.create", "Create new scenario models and baselines"),
    ("scenario.update", "Modify existing scenario configurations"),
    ("scenario.run_adhoc", "Execute ad-hoc flood risk calculations on custom zone telemetry"),
    ("chatbot.ask", "Query grounded advisory chatbot for explanations"),
    ("ml.predict", "Invoke ML next-day rainfall flood-risk class predictions"),
    ("audit.read", "Read backend and client audit event records"),
    ("audit.create", "Record client-side user actions into audit log"),
    ("intervention.recommend", "Generate and evaluate flood interventions"),
    ("intervention.approve", "Approve pending operational flood interventions"),
    ("intervention.deploy", "Deploy operational interventions into live catchment (requires explicit grant)"),
    ("admin.users", "Manage user account status, credentials, and activation"),
    ("admin.roles", "Manage and assign RBAC roles to users"),
    ("admin.scenario_grants", "Issue and revoke explicit scenario access grants"),
]

# Explicit role-to-permission mapping (least-privilege defaults)
# Note: 'intervention.deploy' is intentionally omitted from all default roles
ROLE_PERMISSION_MAP = {
    "VIEWER": [
        "scenario.read",
        "chatbot.ask",
        "audit.read",
    ],
    "ANALYST": [
        "scenario.read",
        "chatbot.ask",
        "audit.read",
        "scenario.run",
        "scenario.run_adhoc",
        "ml.predict",
    ],
    "OPERATOR": [
        "scenario.read",
        "chatbot.ask",
        "audit.read",
        "scenario.run",
        "scenario.run_adhoc",
        "ml.predict",
        "intervention.recommend",
        "intervention.approve",
        "audit.create",
    ],
    "AUDITOR": [
        "audit.read",
    ],
    "ADMIN": [
        "scenario.read",
        "scenario.run",
        "scenario.create",
        "scenario.update",
        "scenario.run_adhoc",
        "chatbot.ask",
        "ml.predict",
        "audit.read",
        "audit.create",
        "intervention.recommend",
        "intervention.approve",
        "admin.users",
        "admin.roles",
        "admin.scenario_grants",
    ],
}


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    # 1. Create auth_roles table
    op.create_table(
        "auth_roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_roles")),
        sa.UniqueConstraint("name", name=op.f("uq_auth_roles_name")),
    )
    op.create_index(op.f("ix_auth_roles_name"), "auth_roles", ["name"], unique=True)

    # 2. Create auth_permissions table
    op.create_table(
        "auth_permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_permissions")),
        sa.UniqueConstraint("name", name=op.f("uq_auth_permissions_name")),
    )
    op.create_index(op.f("ix_auth_permissions_name"), "auth_permissions", ["name"], unique=True)

    # 3. Create auth_role_permissions association table
    op.create_table(
        "auth_role_permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("permission_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["auth_roles.id"],
            name=op.f("fk_auth_role_permissions_role_id_auth_roles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["auth_permissions.id"],
            name=op.f("fk_auth_role_permissions_permission_id_auth_permissions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_role_permissions")),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_auth_role_permissions_role_perm"),
    )
    op.create_index(op.f("ix_auth_role_permissions_permission_id"), "auth_role_permissions", ["permission_id"], unique=False)
    op.create_index(op.f("ix_auth_role_permissions_role_id"), "auth_role_permissions", ["role_id"], unique=False)

    # 4. Create auth_user_roles association table
    op.create_table(
        "auth_user_roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["auth_roles.id"],
            name=op.f("fk_auth_user_roles_role_id_auth_roles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_auth_user_roles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_user_roles")),
        sa.UniqueConstraint("user_id", "role_id", name="uq_auth_user_roles_user_role"),
    )
    op.create_index(op.f("ix_auth_user_roles_role_id"), "auth_user_roles", ["role_id"], unique=False)
    op.create_index(op.f("ix_auth_user_roles_user_id"), "auth_user_roles", ["user_id"], unique=False)

    # 5. Create scenario_access_grants table
    op.create_table(
        "scenario_access_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("permission", sa.String(length=100), nullable=False),
        sa.Column("granted_by", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
            name=op.f("fk_scenario_access_grants_granted_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_scenario_access_grants_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenario_access_grants")),
        sa.UniqueConstraint("user_id", "scenario_id", "permission", name="uq_scenario_grants_user_scenario_perm"),
    )
    op.create_index(op.f("ix_scenario_access_grants_expires_at"), "scenario_access_grants", ["expires_at"], unique=False)
    op.create_index(op.f("ix_scenario_access_grants_permission"), "scenario_access_grants", ["permission"], unique=False)
    op.create_index(op.f("ix_scenario_access_grants_scenario_id"), "scenario_access_grants", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_scenario_access_grants_user_id"), "scenario_access_grants", ["user_id"], unique=False)

    # Seed data
    bind = op.get_bind()
    roles_table = sa.table(
        "auth_roles",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    permissions_table = sa.table(
        "auth_permissions",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    role_permissions_table = sa.table(
        "auth_role_permissions",
        sa.column("id", sa.String),
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    user_roles_table = sa.table(
        "auth_user_roles",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("role_id", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    users_table = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("role", sa.String),
    )

    role_id_map: dict[str, str] = {}
    for role_name, description in DEFAULT_ROLES:
        r_id = str(uuid.uuid4())
        role_id_map[role_name] = r_id
        bind.execute(
            roles_table.insert().values(
                id=r_id,
                name=role_name,
                description=description,
                created_at=now,
                updated_at=now,
            )
        )

    perm_id_map: dict[str, str] = {}
    for perm_name, description in DEFAULT_PERMISSIONS:
        p_id = str(uuid.uuid4())
        perm_id_map[perm_name] = p_id
        bind.execute(
            permissions_table.insert().values(
                id=p_id,
                name=perm_name,
                description=description,
                created_at=now,
            )
        )

    for role_name, perms in ROLE_PERMISSION_MAP.items():
        role_id = role_id_map[role_name]
        for p_name in perms:
            p_id = perm_id_map[p_name]
            bind.execute(
                role_permissions_table.insert().values(
                    id=str(uuid.uuid4()),
                    role_id=role_id,
                    permission_id=p_id,
                    created_at=now,
                )
            )

    # Backfill auth_user_roles for existing user rows based on user.role
    existing_users = bind.execute(sa.select(users_table.c.id, users_table.c.role)).fetchall()
    for u_id, u_role in existing_users:
        canonical_role = (u_role or "OPERATOR").upper()
        if canonical_role in role_id_map:
            bind.execute(
                user_roles_table.insert().values(
                    id=str(uuid.uuid4()),
                    user_id=u_id,
                    role_id=role_id_map[canonical_role],
                    created_at=now,
                )
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_scenario_access_grants_user_id"), table_name="scenario_access_grants")
    op.drop_index(op.f("ix_scenario_access_grants_scenario_id"), table_name="scenario_access_grants")
    op.drop_index(op.f("ix_scenario_access_grants_permission"), table_name="scenario_access_grants")
    op.drop_index(op.f("ix_scenario_access_grants_expires_at"), table_name="scenario_access_grants")
    op.drop_table("scenario_access_grants")

    op.drop_index(op.f("ix_auth_user_roles_user_id"), table_name="auth_user_roles")
    op.drop_index(op.f("ix_auth_user_roles_role_id"), table_name="auth_user_roles")
    op.drop_table("auth_user_roles")

    op.drop_index(op.f("ix_auth_role_permissions_role_id"), table_name="auth_role_permissions")
    op.drop_index(op.f("ix_auth_role_permissions_permission_id"), table_name="auth_role_permissions")
    op.drop_table("auth_role_permissions")

    op.drop_index(op.f("ix_auth_permissions_name"), table_name="auth_permissions")
    op.drop_table("auth_permissions")

    op.drop_index(op.f("ix_auth_roles_name"), table_name="auth_roles")
    op.drop_table("auth_roles")

