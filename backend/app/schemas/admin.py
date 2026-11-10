"""Pydantic schemas for administrative and RBAC management endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleItem(BaseModel):
    """Safe schema for RBAC role representation."""

    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class AssignRoleRequest(BaseModel):
    """Payload to assign a role to a user."""

    role: str = Field(..., min_length=2, max_length=50, description="Role name (e.g. VIEWER, ANALYST, OPERATOR, AUDITOR, ADMIN)")


class UserRolesResponse(BaseModel):
    """Response detailing assigned roles for a user."""

    user_id: str
    roles: List[str]


class ScenarioGrantRequest(BaseModel):
    """Payload to create or update an explicit scenario access grant."""

    user_id: str = Field(..., description="Target user UUID")
    scenario_id: str = Field(..., min_length=1, max_length=100, description="Target scenario identifier")
    permission: str = Field(..., min_length=1, max_length=100, description="Permission granted (e.g. scenario.read, scenario.run, intervention.deploy)")
    expires_at: Optional[datetime] = Field(None, description="Optional UTC expiration timestamp; null for non-expiring grant")


class ScenarioGrantResponse(BaseModel):
    """Safe schema representing a scenario access grant."""

    id: str
    user_id: str
    scenario_id: str
    permission: str
    granted_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    is_expired: bool = False


class UserAdminItem(BaseModel):
    """Administrative representation of a user account."""

    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: List[str] = Field(default_factory=list)
    created_at: datetime


class UpdateUserStatusRequest(BaseModel):
    """Payload to update account activation status."""

    is_active: bool

