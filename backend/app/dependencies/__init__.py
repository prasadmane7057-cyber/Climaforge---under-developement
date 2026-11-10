"""Reusable FastAPI dependencies package for CLIMAFORGE."""

from app.dependencies.auth import (
    get_current_user,
    oauth2_scheme,
    require_authenticated_user,
    require_permission,
    require_role,
    require_scenario_access,
    require_scenario_access_with_user,
)

__all__ = [
    "get_current_user",
    "oauth2_scheme",
    "require_authenticated_user",
    "require_permission",
    "require_role",
    "require_scenario_access",
    "require_scenario_access_with_user",
]
