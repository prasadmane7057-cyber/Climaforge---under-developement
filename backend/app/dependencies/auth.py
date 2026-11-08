"""FastAPI authentication dependencies for CLIMAFORGE M16A.4.

Provides reusable dependency functions for bearer-token validation and
user resolution from the database.  Role/permission resolution is deferred
to future milestones.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.security.exceptions import InvalidTokenError, TokenExpiredError
from app.security.jwt import jwt_service

# Declares the token endpoint for OpenAPI; actual validation is explicit below.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: Session = Depends(get_db),
) -> User:
    """Validate a bearer access token and return the corresponding active User.

    Resolution order:
    1. Verify the JWT signature, claims, issuer, audience, and expiry.
    2. Query the database by ``sub`` (user UUID) — never trust token-embedded roles.
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
        raise _UNAUTHENTICATED

    return user


def require_authenticated_user(
    user: User = Depends(get_current_user),
) -> User:
    """Alias dependency that explicitly requires an authenticated, active user.

    Exists as a named, discoverable dependency to make endpoint signatures
    self-documenting without duplicating validation logic.
    """
    return user

