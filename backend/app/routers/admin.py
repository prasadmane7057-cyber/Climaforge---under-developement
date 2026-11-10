"""Administrative API router for CLIMAFORGE backend.

Provides administrative controls for user management, role assignments,
and explicit scenario-level access grants.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_permission
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    ScenarioAccessGrant,
    UserRole,
)
from app.models.user import User
from app.schemas.admin import (
    AssignRoleRequest,
    RoleItem,
    ScenarioGrantRequest,
    ScenarioGrantResponse,
    UpdateUserStatusRequest,
    UserAdminItem,
    UserRolesResponse,
)
from app.schemas.scenario_data import get_scenario_by_id
from app.security.rbac import (
    ALL_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_ROLES,
    PERM_ADMIN_ROLES,
    PERM_ADMIN_SCENARIO_GRANTS,
    PERM_ADMIN_USERS,
    get_user_roles,
    normalize_role_name,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/roles",
    response_model=List[RoleItem],
    summary="List RBAC Roles",
    description="Retrieve all system roles and their assigned permissions.",
)
def list_roles(
    _: User = Depends(require_permission(PERM_ADMIN_ROLES)),
    session: Session = Depends(get_db),
) -> List[RoleItem]:
    """Retrieve catalog of roles and their effective permissions."""
    db_roles = session.execute(select(Role)).scalars().all()

    items: List[RoleItem] = []
    seen_roles = set()

    for r in db_roles:
        seen_roles.add(r.name)
        perms = [p.name for p in r.permissions] if r.permissions else list(DEFAULT_ROLE_PERMISSIONS.get(r.name, []))
        items.append(RoleItem(name=r.name, description=r.description, permissions=sorted(perms)))

    for default_r in DEFAULT_ROLES:
        if default_r not in seen_roles:
            items.append(
                RoleItem(
                    name=default_r,
                    description=None,
                    permissions=sorted(list(DEFAULT_ROLE_PERMISSIONS.get(default_r, []))),
                )
            )

    return sorted(items, key=lambda x: x.name)


@router.post(
    "/users/{user_id}/roles",
    response_model=UserRolesResponse,
    summary="Assign Role to User",
    description="Assign a server-controlled RBAC role to a target user.",
)
def assign_role(
    user_id: str,
    payload: AssignRoleRequest,
    current_user: User = Depends(require_permission(PERM_ADMIN_ROLES)),
    session: Session = Depends(get_db),
) -> UserRolesResponse:
    """Assign role to target user, preventing self-role escalation."""
    # Prevent users from modifying their own roles
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users cannot modify their own roles.",
        )

    target_user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target user '{user_id}' was not found.",
        )

    canonical_role_name = normalize_role_name(payload.role)
    if canonical_role_name not in DEFAULT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Must be one of: {', '.join(DEFAULT_ROLES)}",
        )

    # Ensure role exists in auth_roles
    role = session.execute(
        select(Role).where(Role.name == canonical_role_name)
    ).scalar_one_or_none()

    if role is None:
        role = Role(name=canonical_role_name)
        session.add(role)
        session.flush()

    # Check if assignment already exists
    existing_user_role = session.execute(
        select(UserRole).where(
            UserRole.user_id == target_user.id,
            UserRole.role_id == role.id,
        )
    ).scalar_one_or_none()

    if existing_user_role is None:
        new_assignment = UserRole(user_id=target_user.id, role_id=role.id)
        session.add(new_assignment)

    # Update fallback user.role column as well
    target_user.role = canonical_role_name.lower()
    session.commit()

    roles = get_user_roles(session, target_user)
    return UserRolesResponse(user_id=target_user.id, roles=sorted(list(roles)))


@router.delete(
    "/users/{user_id}/roles/{role_name}",
    response_model=UserRolesResponse,
    summary="Revoke Role from User",
    description="Remove an assigned RBAC role from a target user.",
)
def revoke_role(
    user_id: str,
    role_name: str,
    current_user: User = Depends(require_permission(PERM_ADMIN_ROLES)),
    session: Session = Depends(get_db),
) -> UserRolesResponse:
    """Revoke role from user, preventing self-role modification."""
    # Prevent users from modifying their own roles
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users cannot modify their own roles.",
        )

    target_user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target user '{user_id}' was not found.",
        )

    canonical_role = normalize_role_name(role_name)
    role = session.execute(
        select(Role).where(Role.name == canonical_role)
    ).scalar_one_or_none()

    if role is not None:
        session.execute(
            delete(UserRole).where(
                UserRole.user_id == target_user.id,
                UserRole.role_id == role.id,
            )
        )
        session.commit()

    roles = get_user_roles(session, target_user)
    return UserRolesResponse(user_id=target_user.id, roles=sorted(list(roles)))


@router.post(
    "/scenario-grants",
    response_model=ScenarioGrantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Scenario Access Grant",
    description="Issue an explicit or temporal access grant for a specific scenario.",
)
def create_scenario_grant(
    payload: ScenarioGrantRequest,
    current_user: User = Depends(require_permission(PERM_ADMIN_SCENARIO_GRANTS)),
    session: Session = Depends(get_db),
) -> ScenarioGrantResponse:
    """Issue a scenario grant to a target user."""
    # Validate target user exists
    target_user = session.execute(
        select(User).where(User.id == payload.user_id)
    ).scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target user '{payload.user_id}' was not found.",
        )

    # Validate scenario exists
    scenario = get_scenario_by_id(payload.scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{payload.scenario_id}' was not found in catalog.",
        )

    # Validate permission is valid
    if payload.permission not in ALL_PERMISSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission '{payload.permission}'. Must be one of: {', '.join(ALL_PERMISSIONS)}",
        )

    # Check for existing grant (user_id, scenario_id, permission)
    grant = session.execute(
        select(ScenarioAccessGrant).where(
            ScenarioAccessGrant.user_id == payload.user_id,
            ScenarioAccessGrant.scenario_id == payload.scenario_id,
            ScenarioAccessGrant.permission == payload.permission,
        )
    ).scalar_one_or_none()

    if grant is None:
        grant = ScenarioAccessGrant(
            user_id=payload.user_id,
            scenario_id=payload.scenario_id,
            permission=payload.permission,
            granted_by=current_user.id,
            expires_at=payload.expires_at,
        )
        session.add(grant)
    else:
        grant.granted_by = current_user.id
        grant.expires_at = payload.expires_at

    session.commit()
    session.refresh(grant)

    return ScenarioGrantResponse(
        id=grant.id,
        user_id=grant.user_id,
        scenario_id=grant.scenario_id,
        permission=grant.permission,
        granted_by=grant.granted_by,
        expires_at=grant.expires_at,
        created_at=grant.created_at,
        is_expired=grant.is_expired(),
    )


@router.get(
    "/scenario-grants",
    response_model=List[ScenarioGrantResponse],
    summary="List Scenario Access Grants",
    description="Retrieve scenario-scoped access grants, optionally filtered by user or scenario.",
)
def list_scenario_grants(
    user_id: Optional[str] = Query(None, description="Filter by user UUID"),
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    _: User = Depends(require_permission(PERM_ADMIN_SCENARIO_GRANTS)),
    session: Session = Depends(get_db),
) -> List[ScenarioGrantResponse]:
    """Retrieve filtered or complete scenario access grants."""
    stmt = select(ScenarioAccessGrant)
    if user_id:
        stmt = stmt.where(ScenarioAccessGrant.user_id == user_id)
    if scenario_id:
        stmt = stmt.where(ScenarioAccessGrant.scenario_id == scenario_id)

    grants = session.execute(stmt).scalars().all()

    return [
        ScenarioGrantResponse(
            id=g.id,
            user_id=g.user_id,
            scenario_id=g.scenario_id,
            permission=g.permission,
            granted_by=g.granted_by,
            expires_at=g.expires_at,
            created_at=g.created_at,
            is_expired=g.is_expired(),
        )
        for g in grants
    ]


@router.delete(
    "/scenario-grants/{grant_id}",
    summary="Revoke Scenario Access Grant",
    description="Revoke an explicit scenario access grant by ID.",
)
def revoke_scenario_grant(
    grant_id: str,
    _: User = Depends(require_permission(PERM_ADMIN_SCENARIO_GRANTS)),
    session: Session = Depends(get_db),
) -> dict:
    """Delete a scenario grant by ID."""
    grant = session.execute(
        select(ScenarioAccessGrant).where(ScenarioAccessGrant.id == grant_id)
    ).scalar_one_or_none()

    if grant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario grant '{grant_id}' was not found.",
        )

    session.delete(grant)
    session.commit()
    return {"success": True, "deleted_id": grant_id}


@router.get(
    "/users",
    response_model=List[UserAdminItem],
    summary="List Users (Admin)",
    description="Retrieve all user accounts and their assigned roles.",
)
def list_users(
    _: User = Depends(require_permission(PERM_ADMIN_USERS)),
    session: Session = Depends(get_db),
) -> List[UserAdminItem]:
    """List safe user representations for administration."""
    users = session.execute(select(User)).scalars().all()
    results: List[UserAdminItem] = []

    for u in users:
        roles = get_user_roles(session, u)
        results.append(
            UserAdminItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                roles=sorted(list(roles)),
                created_at=u.created_at,
            )
        )

    return sorted(results, key=lambda x: x.created_at)


@router.patch(
    "/users/{user_id}/status",
    response_model=UserAdminItem,
    summary="Update User Status",
    description="Activate or deactivate a user account.",
)
def update_user_status(
    user_id: str,
    payload: UpdateUserStatusRequest,
    current_user: User = Depends(require_permission(PERM_ADMIN_USERS)),
    session: Session = Depends(get_db),
) -> UserAdminItem:
    """Update active status of user, preventing self-deactivation."""
    # Prevent self-deactivation
    if current_user.id == user_id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users cannot deactivate their own account.",
        )

    target_user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target user '{user_id}' was not found.",
        )

    target_user.is_active = payload.is_active
    session.commit()
    session.refresh(target_user)

    roles = get_user_roles(session, target_user)
    return UserAdminItem(
        id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        is_active=target_user.is_active,
        is_superuser=target_user.is_superuser,
        roles=sorted(list(roles)),
        created_at=target_user.created_at,
    )

