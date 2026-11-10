"""FastAPI authentication router — login, refresh, logout, and current-user endpoints.

Security model:
- Access tokens are short-lived JWTs returned in the JSON response body.
- Refresh tokens are opaque, hashed, and transmitted exclusively via HttpOnly cookies.
- CSRF protection uses the double-submit cookie pattern for all cookie-authenticated requests.
- Cookie security flags are environment-aware (Secure + SameSite=Strict in production).
- Login endpoint is rate-limited (5 req / 60 s per IP) to slow credential-stuffing attacks.
- Generic 401 responses are returned for both unknown emails and wrong passwords to prevent
  user enumeration.  Timing attacks are mitigated by running the hash verification even when
  the user does not exist.
"""

import logging
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.dependencies.auth import require_authenticated_user
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, ErrorResponse, LoginRequest, TokenResponse
from app.security.exceptions import (
    InvalidRefreshTokenError,
    RefreshTokenError,
    TokenExpiredRefreshError,
    TokenReusedError,
    TokenRevokedError,
)
from app.security.jwt import jwt_service
from app.security.passwords import password_service
from app.security.rate_limiter import login_limiter
from app.security.refresh_tokens import (
    RefreshTokenService,
    hash_refresh_token,
    refresh_token_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Cookie / CSRF configuration
# ---------------------------------------------------------------------------
_REFRESH_COOKIE_NAME = "climaforge_refresh_token"
_CSRF_COOKIE_NAME = "csrf_token"
_CSRF_HEADER_NAME = "x-csrf-token"  # FastAPI normalises header names to lower-case

# Dummy hash used in constant-time password check for unknown users.
# Generated once at module load; value is irrelevant — only timing matters.
_DUMMY_HASH: str = password_service.hash_password("dummy-climaforge-sentinel-value")


def _is_production() -> bool:
    """Return True when running in a production-like environment."""
    return settings.environment.lower() not in {"development", "dev", "test", "testing"}


def _cookie_kwargs() -> dict:
    """Return environment-aware cookie security flags."""
    production = _is_production()
    return {
        "httponly": True,
        "samesite": "strict" if production else "lax",
        "secure": production,
        "path": "/",
    }


def _csrf_cookie_kwargs() -> dict:
    """Return flags for the CSRF double-submit cookie (must be JS-readable, so httponly=False)."""
    production = _is_production()
    return {
        "httponly": False,
        "samesite": "strict" if production else "lax",
        "secure": production,
        "path": "/",
    }


def _set_refresh_cookie(response: Response, raw_token: str, max_age: int) -> None:
    """Write the HttpOnly refresh-token cookie."""
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        **_cookie_kwargs(),
    )


def _set_csrf_cookie(response: Response, csrf_value: str, max_age: int) -> None:
    """Write the JS-readable CSRF double-submit cookie."""
    response.set_cookie(
        key=_CSRF_COOKIE_NAME,
        value=csrf_value,
        max_age=max_age,
        **_csrf_cookie_kwargs(),
    )


def _clear_auth_cookies(response: Response) -> None:
    """Expire both the refresh and CSRF cookies with matching environment-aware flags."""
    production = _is_production()
    response.delete_cookie(
        _REFRESH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="strict" if production else "lax",
        secure=production,
    )
    response.delete_cookie(
        _CSRF_COOKIE_NAME,
        path="/",
        httponly=False,
        samesite="strict" if production else "lax",
        secure=production,
    )


def _validate_csrf(request: Request) -> None:
    """Enforce CSRF double-submit protection.

    Compares the ``X-CSRF-Token`` request header against the ``csrf_token``
    cookie value using a constant-time comparison to prevent timing attacks.
    Raises HTTP 401 on any mismatch or missing value.
    """
    header_csrf = request.headers.get(_CSRF_HEADER_NAME, "")
    cookie_csrf = request.cookies.get(_CSRF_COOKIE_NAME, "")

    if not header_csrf or not cookie_csrf:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CSRF validation failed",
        )

    if not secrets.compare_digest(header_csrf, cookie_csrf):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CSRF validation failed",
        )


def _get_client_ip(request: Request) -> str:
    """Extract the best-effort client IP for rate-limiting purposes."""
    # Respect X-Forwarded-For set by a trusted reverse proxy if present.
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and obtain tokens",
)
def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    session: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange credentials for an access token and an HttpOnly refresh cookie.

    Security properties:
    - Both unknown-user and wrong-password cases return an identical 401 to
      prevent user enumeration.
    - Argon2id verification runs even when the user is not found (timing
      equalisation).
    - Inactive accounts return HTTP 403 (distinct from unauthenticated 401).
    - Rate-limited to 5 attempts / 60 s per client IP.
    - Refresh token is set in an HttpOnly cookie only — never in the JSON body.
    - Credentials are never logged.
    """
    # 1. Rate limiting
    client_ip = _get_client_ip(request)
    if not login_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": "60"},
        )

    # 2. Look up user by email (case-insensitively normalised by LoginRequest)
    user = session.execute(
        select(User).where(User.email == body.email)
    ).scalar_one_or_none()

    # 3. Constant-time verification regardless of user existence
    candidate_hash = user.hashed_password if user else _DUMMY_HASH
    password_valid = password_service.verify_password(body.password, candidate_hash)

    # Generic 401 — identical for unknown user and wrong password
    if user is None or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Reject inactive accounts
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # 5. Issue access token (short-lived JWT)
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    # 6. Issue refresh token (opaque, stored hashed, delivered via cookie only)
    rt_service = RefreshTokenService(settings)
    raw_refresh, _token_record = rt_service.create_refresh_token(session, user_id=user.id)
    session.commit()

    # 7. Set cookies
    max_age_refresh = int(settings.refresh_token_days * 86400)
    max_age_access = int(settings.access_token_minutes * 60)
    csrf_value = secrets.token_urlsafe(32)

    _set_refresh_cookie(response, raw_refresh, max_age=max_age_refresh)
    _set_csrf_cookie(response, csrf_value, max_age=max_age_refresh)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=max_age_access,
    )


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue a new access token",
)
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    climaforge_refresh_token: str | None = Cookie(default=None),
) -> TokenResponse:
    """Rotate the refresh token and return a new access token.

    CSRF protection is enforced via the double-submit cookie pattern.
    Invalid or replayed tokens clear both cookies immediately.
    """
    # 1. CSRF check
    _validate_csrf(request)

    # 2. Require refresh cookie
    if not climaforge_refresh_token:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rt_service = RefreshTokenService(settings)

    # 3. Atomic rotation
    try:
        new_raw_token, new_token_record = rt_service.rotate_refresh_token(
            session, climaforge_refresh_token
        )
    except (
        TokenReusedError,
        TokenExpiredRefreshError,
        TokenRevokedError,
        InvalidRefreshTokenError,
        RefreshTokenError,
    ):
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Resolve user to obtain current role (never trust stale token claims)
    user = session.execute(
        select(User).where(User.id == new_token_record.user_id)
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        # Revoke the freshly issued token; don't leave it dangling
        try:
            rt_service.revoke_refresh_token(session, new_raw_token)
        except Exception:
            pass
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Issue new access token
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    # 6. Replace cookies
    max_age_refresh = int(settings.refresh_token_days * 86400)
    max_age_access = int(settings.access_token_minutes * 60)
    csrf_value = secrets.token_urlsafe(32)

    _set_refresh_cookie(response, new_raw_token, max_age=max_age_refresh)
    _set_csrf_cookie(response, csrf_value, max_age=max_age_refresh)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=max_age_access,
    )


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------
@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke the current session and clear auth cookies",
)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    climaforge_refresh_token: str | None = Cookie(default=None),
) -> dict:
    """Revoke the active refresh-token session and clear all auth cookies.

    CSRF validation is enforced where cookie authentication is involved.
    Absent cookies are tolerated (idempotent logout).
    Internal token details are never disclosed in the response.
    """
    # 1. CSRF check (required where cookie authentication is involved)
    if climaforge_refresh_token or request.cookies.get(_CSRF_COOKIE_NAME):
        _validate_csrf(request)

    # 2. Revoke session family if cookie is present
    if climaforge_refresh_token:
        rt_service = RefreshTokenService(settings)
        try:
            token_hash = hash_refresh_token(climaforge_refresh_token, rt_service.pepper)
            token = session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            ).scalar_one_or_none()
            if token is not None:
                rt_service.revoke_session(session, token.family_id)
            else:
                rt_service.revoke_refresh_token(session, climaforge_refresh_token)
        except Exception:
            # Swallow all errors — logout must always succeed from the client's perspective
            pass

    # 3. Clear cookies unconditionally
    _clear_auth_cookies(response)

    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the authenticated user's public profile",
)
def get_me(
    session: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> CurrentUserResponse:
    """Return the current authenticated user's profile.

    Performs a fresh database read to reflect any in-flight changes to
    ``is_active`` or other fields.  Internal fields (hashed_password,
    is_superuser, refresh_tokens) are never exposed.
    """
    # Fresh load to capture any administrative changes since the token was issued
    user = session.execute(
        select(User).where(User.id == current_user.id)
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUserResponse.model_validate(user)

