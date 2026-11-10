"""RBAC security constants, permission definitions, and resolution services."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    ScenarioAccessGrant,
    UserRole,
)
from app.models.user import User
from app.schemas.scenario_data import get_scenario_by_id
from app.schemas.scenarios import ScenarioDetail

# 5 Server-controlled canonical roles
ROLE_VIEWER = "VIEWER"
ROLE_ANALYST = "ANALYST"
ROLE_OPERATOR = "OPERATOR"
ROLE_AUDITOR = "AUDITOR"
ROLE_ADMIN = "ADMIN"

DEFAULT_ROLES = [
    ROLE_VIEWER,
    ROLE_ANALYST,
    ROLE_OPERATOR,
    ROLE_AUDITOR,
    ROLE_ADMIN,
]

# 15 Granular action permissions
PERM_SCENARIO_READ = "scenario.read"
PERM_SCENARIO_RUN = "scenario.run"
PERM_SCENARIO_CREATE = "scenario.create"
PERM_SCENARIO_UPDATE = "scenario.update"
PERM_SCENARIO_RUN_ADHOC = "scenario.run_adhoc"
PERM_CHATBOT_ASK = "chatbot.ask"
PERM_ML_PREDICT = "ml.predict"
PERM_AUDIT_READ = "audit.read"
PERM_AUDIT_CREATE = "audit.create"
PERM_INTERVENTION_RECOMMEND = "intervention.recommend"
PERM_INTERVENTION_APPROVE = "intervention.approve"
PERM_INTERVENTION_DEPLOY = "intervention.deploy"
PERM_ADMIN_USERS = "admin.users"
PERM_ADMIN_ROLES = "admin.roles"
PERM_ADMIN_SCENARIO_GRANTS = "admin.scenario_grants"

ALL_PERMISSIONS = [
    PERM_SCENARIO_READ,
    PERM_SCENARIO_RUN,
    PERM_SCENARIO_CREATE,
    PERM_SCENARIO_UPDATE,
    PERM_SCENARIO_RUN_ADHOC,
    PERM_CHATBOT_ASK,
    PERM_ML_PREDICT,
    PERM_AUDIT_READ,
    PERM_AUDIT_CREATE,
    PERM_INTERVENTION_RECOMMEND,
    PERM_INTERVENTION_APPROVE,
    PERM_INTERVENTION_DEPLOY,
    PERM_ADMIN_USERS,
    PERM_ADMIN_ROLES,
    PERM_ADMIN_SCENARIO_GRANTS,
]

# Canonical role-to-permission mapping dictionary (least-privilege defaults)
# Note: PERM_INTERVENTION_DEPLOY is explicitly omitted from all default roles.
DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_VIEWER: {
        PERM_SCENARIO_READ,
        PERM_CHATBOT_ASK,
        PERM_AUDIT_READ,
    },
    ROLE_ANALYST: {
        PERM_SCENARIO_READ,
        PERM_CHATBOT_ASK,
        PERM_AUDIT_READ,
        PERM_SCENARIO_RUN,
        PERM_SCENARIO_RUN_ADHOC,
        PERM_ML_PREDICT,
    },
    ROLE_OPERATOR: {
        PERM_SCENARIO_READ,
        PERM_CHATBOT_ASK,
        PERM_AUDIT_READ,
        PERM_SCENARIO_RUN,
        PERM_SCENARIO_RUN_ADHOC,
        PERM_ML_PREDICT,
        PERM_INTERVENTION_RECOMMEND,
        PERM_INTERVENTION_APPROVE,
        PERM_AUDIT_CREATE,
    },
    ROLE_AUDITOR: {
        PERM_AUDIT_READ,
    },
    ROLE_ADMIN: {
        PERM_SCENARIO_READ,
        PERM_SCENARIO_RUN,
        PERM_SCENARIO_CREATE,
        PERM_SCENARIO_UPDATE,
        PERM_SCENARIO_RUN_ADHOC,
        PERM_CHATBOT_ASK,
        PERM_ML_PREDICT,
        PERM_AUDIT_READ,
        PERM_AUDIT_CREATE,
        PERM_INTERVENTION_RECOMMEND,
        PERM_INTERVENTION_APPROVE,
        PERM_ADMIN_USERS,
        PERM_ADMIN_ROLES,
        PERM_ADMIN_SCENARIO_GRANTS,
    },
}


def normalize_role_name(role: str) -> str:
    """Normalize role names to uppercase canonical format."""
    return role.strip().upper()


def get_user_roles(session: Session, user: User) -> Set[str]:
    """Retrieve all assigned role names for a user from the database.

    Resolution:
    1. Query auth_user_roles joined with auth_roles.
    2. Fall back to user.role if no auth_user_roles records exist.
    """
    db_roles = session.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    ).scalars().all()

    roles = {normalize_role_name(r) for r in db_roles}
    if not roles and user.role:
        roles.add(normalize_role_name(user.role))

    if user.is_superuser:
        roles.add(ROLE_ADMIN)

    return roles


def get_user_permissions(session: Session, user: User) -> Set[str]:
    """Resolve the complete set of effective global permissions for a user.

    Resolution:
    1. Query permissions linked through auth_user_roles -> auth_role_permissions -> auth_permissions.
    2. Merge with static fallback mappings for assigned roles (ensuring robust defaults).
    3. Respect least-privilege: intervention.deploy is NEVER granted automatically by role.
    """
    if not user.is_active:
        return set()

    # Query database permissions
    db_perms = session.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id)
    ).scalars().all()

    permissions: Set[str] = set(db_perms)

    # Merge permissions from default role mappings for each assigned role
    user_roles = get_user_roles(session, user)
    for r in user_roles:
        if r in DEFAULT_ROLE_PERMISSIONS:
            permissions.update(DEFAULT_ROLE_PERMISSIONS[r])

    return permissions


def has_scenario_permission(
    session: Session,
    user: User,
    scenario_id: str,
    required_permission: str,
) -> bool:
    """Check whether a user has permission for a specific scenario.

    Authorization succeeds if:
    1. User has the required global permission, OR
    2. User has an active (unexpired) scenario-specific access grant for (user, scenario, permission).
    """
    if not user.is_active:
        return False

    # 1. Global permission check
    global_perms = get_user_permissions(session, user)
    if required_permission in global_perms:
        return True

    # 2. Explicit scenario access grant check
    now = datetime.now(timezone.utc)
    grant = session.execute(
        select(ScenarioAccessGrant).where(
            ScenarioAccessGrant.user_id == user.id,
            ScenarioAccessGrant.scenario_id == scenario_id,
            ScenarioAccessGrant.permission == required_permission,
        )
    ).scalar_one_or_none()

    if grant is not None:
        if grant.expires_at is None:
            return True
        expires = grant.expires_at if grant.expires_at.tzinfo is not None else grant.expires_at.replace(tzinfo=timezone.utc)
        if expires > now:
            return True

    return False


def check_scenario_access(
    session: Session,
    user: User,
    scenario_id: str,
    required_permission: str,
    hide_existence: bool = False,
) -> ScenarioDetail:
    """Validate scenario access and return the scenario detail.

    Returns:
    - 401 if user is inactive.
    - 404 if scenario does not exist.
    - 403 if user lacks global permission and scenario grant.
    - 404 if scenario existence must remain hidden on denial.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scenario = get_scenario_by_id(scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' was not found in the demonstrator catalog.",
        )

    if not has_scenario_permission(session, user, scenario_id, required_permission):
        if hide_existence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario '{scenario_id}' was not found in the demonstrator catalog.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for scenario '{scenario_id}' (required: '{required_permission}').",
        )

    return scenario

