"""FastAPI authentication and RBAC authorization dependencies for CLIMAFORGE M16A.5.

Provides reusable dependency functions for bearer-token validation, role verification,
granular permission enforcement, and scenario-level access authorization.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.scenario_data import get_scenario_by_id
from app.schemas.scenarios import ScenarioDetail
from app.security.exceptions import InvalidTokenError, TokenExpiredError
from app.security.jwt import jwt_service
from app.security.rbac import (
    check_scenario_access,
    get_user_permissions,
    get_user_roles,
    normalize_role_name,
    PERM_SCENARIO_READ,
    PERM_CHATBOT_ASK,
)

# Declares the token endpoint for OpenAPI; actual validation is explicit below.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required",
    headers={"WWW-Authenticate": "Bearer"},
)

_INACTIVE_USER = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="User account is inactive",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: Session = Depends(get_db),
) -> User:
    """Validate a bearer access token and return the corresponding active User.

    Resolution order:
    1. Verify the JWT signature, claims, issuer, audience, and expiry.
    2. Query the database by sub (user UUID) — never trust token-embedded roles.
    3. Reject missing or inactive users with HTTP 401.
    """
    if not token:
        raise _UNAUTHENTICATED

    try:
        payload = jwt_service.verify_access_token(token)
    except (InvalidTokenError, TokenExpiredError):
        raise _UNAUTHENTICATED

    user = session.execute(
        select(User).where(User.id == payload.sub)
    ).scalar_one_or_none()

    if user is None:
        raise _UNAUTHENTICATED

    if not user.is_active:
        raise _INACTIVE_USER

    return user


def require_authenticated_user(
    user: User = Depends(get_current_user),
) -> User:
    """Alias dependency that explicitly requires an authenticated, active user.

    Exists as a named, discoverable dependency to make endpoint signatures
    self-documenting without duplicating validation logic.
    """
    return user


def require_role(*allowed_roles: str) -> Callable[[User, Session], User]:
    """Dependency factory requiring the authenticated user to hold at least one of the specified roles."""
    normalized_allowed = {normalize_role_name(r) for r in allowed_roles}

    def role_dependency(
        user: User = Depends(get_current_user),
        session: Session = Depends(get_db),
    ) -> User:
        user_roles = get_user_roles(session, user)
        if not user_roles.intersection(normalized_allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: User lacks required role. Allowed: {', '.join(sorted(normalized_allowed))}",
            )
        return user

    return role_dependency


def require_permission(*required_permissions: str) -> Callable[..., User | None]:
    """Dependency factory requiring the authenticated user to possess all specified permissions.

    In strict configured mode (settings.jwt_signing_key is not None), unauthenticated
    requests are denied with 401. If settings.jwt_signing_key is unconfigured (demonstrator mode)
    and no token is sent, requests are allowed to preserve compatibility with demonstrator tests.
    """
    def permission_dependency(
        token: str | None = Depends(oauth2_scheme),
        session: Session = Depends(get_db),
    ) -> User | None:
        # Check demonstrator fallback
        if token is None:
            if set(required_permissions).issubset({PERM_SCENARIO_READ, PERM_CHATBOT_ASK}):
                return None
            if settings.jwt_signing_key is None:
                return None
            raise _UNAUTHENTICATED

        # Authenticate and resolve user
        user = get_current_user(token=token, session=session)
        user_perms = get_user_permissions(session, user)

        for perm in required_permissions:
            if perm not in user_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Missing required permission '{perm}'.",
                )
        return user

    return permission_dependency


def require_scenario_access(
    required_permission: str,
    hide_existence: bool = False,
) -> Callable[..., ScenarioDetail]:
    """Dependency factory verifying scenario-scoped authorization.

    Checks:
    1. Scenario existence (404 if missing).
    2. Active user status (401 if inactive).
    3. Global permission or active, unexpired scenario access grant (403 if unauthorized).
    4. hide_existence hides scenario existence behind 404 when unauthorized.
    """
    def scenario_access_dependency(
        scenario_id: str,
        token: str | None = Depends(oauth2_scheme),
        session: Session = Depends(get_db),
    ) -> ScenarioDetail:
        # Demonstrator fallback when auth is unconfigured or read-only/chatbot and no token is present
        if token is None:
            if required_permission in {PERM_SCENARIO_READ, PERM_CHATBOT_ASK} or settings.jwt_signing_key is None:
                scenario = get_scenario_by_id(scenario_id)
                if not scenario:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Scenario '{scenario_id}' was not found in the demonstrator catalog.",
                    )
                return scenario
            raise _UNAUTHENTICATED

        user = get_current_user(token=token, session=session)
        return check_scenario_access(
            session=session,
            user=user,
            scenario_id=scenario_id,
            required_permission=required_permission,
            hide_existence=hide_existence,
        )

    return scenario_access_dependency


def require_scenario_access_with_user(
    required_permission: str,
    hide_existence: bool = False,
) -> Callable[..., tuple[User | None, ScenarioDetail]]:
    """Dependency factory returning both the authenticated User and the verified ScenarioDetail."""
    def scenario_access_user_dependency(
        scenario_id: str,
        token: str | None = Depends(oauth2_scheme),
        session: Session = Depends(get_db),
    ) -> tuple[User | None, ScenarioDetail]:
        if token is None:
            if required_permission in {PERM_SCENARIO_READ, PERM_CHATBOT_ASK} or settings.jwt_signing_key is None:
                scenario = get_scenario_by_id(scenario_id)
                if not scenario:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Scenario '{scenario_id}' was not found in the demonstrator catalog.",
                    )
                return None, scenario
            raise _UNAUTHENTICATED

        user = get_current_user(token=token, session=session)
        scenario = check_scenario_access(
            session=session,
            user=user,
            scenario_id=scenario_id,
            required_permission=required_permission,
            hide_existence=hide_existence,
        )
        return user, scenario

    return scenario_access_user_dependency
