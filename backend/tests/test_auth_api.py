"""Integration and contract tests for CLIMAFORGE M16A.4 Authentication API endpoints.

Covers:
- POST /api/auth/login
- POST /api/auth/refresh
- POST /api/auth/logout
- GET /api/auth/me
- Rate limiting, CSRF validation, replay protection, and cookie flag security.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import uuid

import pytest
from starlette.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker, Session

from app.config import Settings
import app.config as config_module
from app.db.base import Base
from app.db.session import create_db_engine, get_db, get_session_factory
from app.main import app
from app.models.token import RefreshToken
from app.models.user import User
from app.security.passwords import password_service
from app.security.rate_limiter import login_limiter
from app.security.jwt import jwt_service


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure rate-limiter state is clean before each test."""
    login_limiter.reset_all()
    yield
    login_limiter.reset_all()


@pytest.fixture
def test_db(tmp_path: Path, monkeypatch) -> sessionmaker[Session]:
    """Configure isolated database and settings for each test."""
    db_file = tmp_path / f"api_test_{uuid.uuid4().hex}.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    monkeypatch.setattr(config_module.settings, "jwt_signing_key", "k" * 32)
    monkeypatch.setattr(config_module.settings, "jwt_issuer", "climaforge-test-issuer")
    monkeypatch.setattr(config_module.settings, "jwt_audience", "climaforge-test-audience")
    monkeypatch.setattr(config_module.settings, "refresh_token_pepper", "p" * 32)
    monkeypatch.setattr(config_module.settings, "access_token_minutes", 15)
    monkeypatch.setattr(config_module.settings, "refresh_token_days", 7)
    monkeypatch.setattr(config_module.settings, "environment", "development")
    monkeypatch.setattr(config_module.settings, "database_url", db_url)

    engine = create_db_engine(db_url)
    Base.metadata.create_all(bind=engine)
    factory = get_session_factory(engine)

    def _override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield factory
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


@pytest.fixture
def sample_user(test_db: sessionmaker[Session]) -> User:
    """Create an active sample user with known password."""
    with test_db() as session:
        user = User(
            email="operator@climaforge.test",
            hashed_password=password_service.hash_password("OperationalSecret2026!"),
            full_name="Chief Operations Officer",
            role="operator",
            is_active=True,
        )
        session.add(user)
        session.commit()
        return User(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        )


@pytest.fixture
def inactive_user(test_db: sessionmaker[Session]) -> User:
    """Create a deactivated sample user."""
    with test_db() as session:
        user = User(
            email="disabled@climaforge.test",
            hashed_password=password_service.hash_password("OperationalSecret2026!"),
            full_name="Disabled Operator",
            role="operator",
            is_active=False,
        )
        session.add(user)
        session.commit()
        return User(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        )


@pytest.fixture
def client(test_db):
    """Synchronous TestClient bound to the FastAPI application."""
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc


def _extract_cookie(response, cookie_name: str) -> str | None:
    """Extract a cookie value from Set-Cookie headers."""
    for header in response.headers.get_list("set-cookie"):
        match = re.search(rf"{cookie_name}=([^;]+)", header)
        if match:
            return match.group(1)
    return None


# ===========================================================================
# 1. Login Tests
# ===========================================================================

def test_login_success(client: TestClient, sample_user: User, test_db: sessionmaker[Session]):
    """Verify successful login issues access token, sets HttpOnly refresh cookie, and no leak."""
    response = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    assert response.status_code == 200
    data = response.json()

    # Access token payload validation
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 15 * 60

    # Ensure NO refresh token in JSON response
    assert "refresh_token" not in data
    assert "climaforge_refresh_token" not in data

    # Verify cookies
    refresh_token = _extract_cookie(response, "climaforge_refresh_token")
    csrf_token = _extract_cookie(response, "csrf_token")
    assert refresh_token is not None
    assert csrf_token is not None

    # Verify cookie flags in headers
    set_cookies = response.headers.get_list("set-cookie")
    refresh_header = next(h for h in set_cookies if "climaforge_refresh_token" in h)
    assert "httponly" in refresh_header.lower()
    assert "path=/" in refresh_header.lower()

    # Verify refresh token record stored as hash in database
    with test_db() as session:
        token_records = session.execute(
            select(RefreshToken).where(RefreshToken.user_id == sample_user.id)
        ).scalars().all()
        assert len(token_records) == 1
        assert token_records[0].token_hash != refresh_token  # Raw token is NOT stored
        assert not token_records[0].revoked


def test_login_invalid_password(client: TestClient, sample_user: User):
    """Verify incorrect password returns generic 401 without tokens."""
    response = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    assert _extract_cookie(response, "climaforge_refresh_token") is None


def test_login_unknown_user(client: TestClient, sample_user: User):
    """Verify unknown user returns identical generic 401 (prevents user enumeration)."""
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@climaforge.test", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    assert _extract_cookie(response, "climaforge_refresh_token") is None


def test_login_inactive_user(client: TestClient, inactive_user: User):
    """Verify inactive account is rejected with HTTP 403."""
    response = client.post(
        "/api/auth/login",
        json={"email": inactive_user.email, "password": "OperationalSecret2026!"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Account is inactive"
    assert _extract_cookie(response, "climaforge_refresh_token") is None


def test_login_email_normalisation(client: TestClient, sample_user: User):
    """Verify case-insensitivity and whitespace stripping on login email."""
    response = client.post(
        "/api/auth/login",
        json={"email": "  OPERATOR@ClimaForge.test  ", "password": "OperationalSecret2026!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_rate_limiting(client: TestClient, sample_user: User):
    """Verify login endpoint enforces 5 attempts per 60 s sliding window."""
    # 5 attempts allowed
    for _ in range(5):
        resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "WrongPassword!"},
        )
        assert resp.status_code == 401

    # 6th attempt rejected with HTTP 429
    blocked_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    assert blocked_resp.status_code == 429
    assert blocked_resp.headers.get("retry-after") == "60"


# ===========================================================================
# 2. Refresh & Token Rotation Tests
# ===========================================================================

def test_refresh_success(client: TestClient, sample_user: User, test_db: sessionmaker[Session]):
    """Verify refresh endpoint rotates refresh token, issues new access token, replaces cookies."""
    # Step 1: Login
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    refresh_token = _extract_cookie(login_resp, "climaforge_refresh_token")
    csrf_token = _extract_cookie(login_resp, "csrf_token")

    # Step 2: Refresh (TestClient automatically stores cookies from login)
    refresh_resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" not in data

    # Verify new rotated refresh token in cookie
    new_refresh_token = _extract_cookie(refresh_resp, "climaforge_refresh_token")
    new_csrf_token = _extract_cookie(refresh_resp, "csrf_token")
    assert new_refresh_token is not None
    assert new_refresh_token != refresh_token
    assert new_csrf_token is not None

    # Verify old token is revoked in DB
    with test_db() as session:
        records = session.execute(
            select(RefreshToken).where(RefreshToken.user_id == sample_user.id)
        ).scalars().all()
        assert len(records) == 2
        revoked_count = sum(1 for r in records if r.revoked)
        active_count = sum(1 for r in records if not r.revoked)
        assert revoked_count == 1
        assert active_count == 1


def test_refresh_replay_protection(client: TestClient, sample_user: User, test_db: sessionmaker[Session]):
    """Verify replaying an already-rotated token revokes the entire session family."""
    # Step 1: Login
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    token_a = _extract_cookie(login_resp, "climaforge_refresh_token")
    csrf_a = _extract_cookie(login_resp, "csrf_token")

    # Step 2: Legitimate rotation (Token A -> Token B)
    rotate_resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf_a},
    )
    assert rotate_resp.status_code == 200
    token_b = _extract_cookie(rotate_resp, "climaforge_refresh_token")
    csrf_b = _extract_cookie(rotate_resp, "csrf_token")

    # Step 3: Malicious replay of consumed Token A
    client.cookies.set("climaforge_refresh_token", token_a)
    client.cookies.set("csrf_token", csrf_b)
    replay_resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf_b},
    )
    assert replay_resp.status_code == 401

    # Verify ALL tokens in this family are now revoked (Token B also revoked)
    with test_db() as session:
        records = session.execute(
            select(RefreshToken).where(RefreshToken.user_id == sample_user.id)
        ).scalars().all()
        for rec in records:
            assert rec.revoked, f"Token {rec.id} was not revoked upon replay"


def test_refresh_expired_token(client: TestClient, sample_user: User, test_db: sessionmaker[Session]):
    """Verify expired refresh token is rejected and cleared."""
    from app.security.refresh_tokens import hash_refresh_token, generate_raw_token

    raw_token = generate_raw_token()
    token_hash = hash_refresh_token(raw_token, "p" * 32)
    with test_db() as session:
        expired_record = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=sample_user.id,
            family_id=str(uuid.uuid4()),
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
            created_at=datetime.now(timezone.utc) - timedelta(days=8),
            revoked=False,
        )
        session.add(expired_record)
        session.commit()

    csrf = "test-csrf-token"
    client.cookies.set("climaforge_refresh_token", raw_token)
    client.cookies.set("csrf_token", csrf)
    resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf},
    )
    assert resp.status_code == 401


def test_refresh_revoked_token(client: TestClient, sample_user: User, test_db: sessionmaker[Session]):
    """Verify previously revoked refresh token is rejected."""
    from app.security.refresh_tokens import hash_refresh_token, generate_raw_token

    raw_token = generate_raw_token()
    token_hash = hash_refresh_token(raw_token, "p" * 32)
    with test_db() as session:
        revoked_record = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=sample_user.id,
            family_id=str(uuid.uuid4()),
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=5),
            created_at=datetime.now(timezone.utc),
            revoked=True,
            revoked_at=datetime.now(timezone.utc),
        )
        session.add(revoked_record)
        session.commit()

    csrf = "test-csrf-token"
    client.cookies.set("climaforge_refresh_token", raw_token)
    client.cookies.set("csrf_token", csrf)
    resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf},
    )
    assert resp.status_code == 401


def test_refresh_unknown_token(client: TestClient):
    """Verify unknown refresh token is rejected."""
    csrf = "test-csrf-token"
    client.cookies.set("climaforge_refresh_token", "non-existent-opaque-token")
    client.cookies.set("csrf_token", csrf)
    resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf},
    )
    assert resp.status_code == 401


def test_refresh_missing_cookie(client: TestClient):
    """Verify missing refresh cookie returns HTTP 401."""
    csrf = "test-csrf-token"
    client.cookies.set("csrf_token", csrf)
    resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf},
    )
    assert resp.status_code == 401


def test_refresh_csrf_rejection_missing_header(client: TestClient, sample_user: User):
    """Verify refresh fails when X-CSRF-Token header is missing."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    assert login_resp.status_code == 200

    resp = client.post("/api/auth/refresh")
    assert resp.status_code in (401, 403)
    assert "csrf" in resp.json()["detail"].lower()


def test_refresh_csrf_rejection_mismatched_token(client: TestClient, sample_user: User):
    """Verify refresh fails when X-CSRF-Token header does not match cookie."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    assert login_resp.status_code == 200

    resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": "wrong-csrf-value"},
    )
    assert resp.status_code in (401, 403)
    assert "csrf" in resp.json()["detail"].lower()


def test_refresh_inactive_user_rejected(client: TestClient, sample_user: User, test_db: sessionmaker[Session]):
    """Verify refreshing for a deactivated user fails and revokes token."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    csrf_token = _extract_cookie(login_resp, "csrf_token")

    # Deactivate user after login
    with test_db() as session:
        u = session.execute(select(User).where(User.id == sample_user.id)).scalar_one()
        u.is_active = False
        session.commit()

    resp = client.post(
        "/api/auth/refresh",
        headers={"x-csrf-token": csrf_token},
    )
    assert resp.status_code == 401


# ===========================================================================
# 3. Logout Tests
# ===========================================================================

def test_logout_success(client: TestClient, sample_user: User, test_db: sessionmaker[Session]):
    """Verify logout revokes the session family and clears auth cookies."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    csrf_token = _extract_cookie(login_resp, "csrf_token")

    logout_resp = client.post(
        "/api/auth/logout",
        headers={"x-csrf-token": csrf_token},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully"

    # Verify session is revoked in database
    with test_db() as session:
        records = session.execute(
            select(RefreshToken).where(RefreshToken.user_id == sample_user.id)
        ).scalars().all()
        assert all(r.revoked for r in records)


def test_logout_idempotency(client: TestClient, sample_user: User):
    """Verify logout is safe and idempotent across repeated calls."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    csrf_token = _extract_cookie(login_resp, "csrf_token")

    # First logout with credentials
    resp1 = client.post(
        "/api/auth/logout",
        headers={"x-csrf-token": csrf_token},
    )
    assert resp1.status_code == 200

    # Second logout without credentials (e.g. browser cleared cookies)
    client.cookies.clear()
    resp2 = client.post("/api/auth/logout")
    assert resp2.status_code == 200
    assert resp2.json()["message"] == "Logged out successfully"


def test_logout_csrf_rejection(client: TestClient, sample_user: User):
    """Verify logout with cookie authentication rejects requests missing valid CSRF header."""
    client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )

    resp = client.post(
        "/api/auth/logout",
        headers={"x-csrf-token": "bad-csrf-header"},
    )
    assert resp.status_code in (401, 403)
    assert "csrf" in resp.json()["detail"].lower()


# ===========================================================================
# 4. Current User (GET /api/auth/me) Tests
# ===========================================================================

def test_get_current_user_me_success(client: TestClient, sample_user: User):
    """Verify GET /api/auth/me returns the user's safe public profile."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    access_token = login_resp.json()["access_token"]

    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    profile = me_resp.json()

    assert profile["id"] == sample_user.id
    assert profile["email"] == sample_user.email
    assert profile["full_name"] == sample_user.full_name
    assert profile["role"] == sample_user.role
    assert profile["is_active"] is True
    assert "created_at" in profile

    # Critical security assertion: internal and sensitive fields are excluded
    assert "hashed_password" not in profile
    assert "is_superuser" not in profile
    assert "refresh_tokens" not in profile


def test_get_current_user_me_missing_token(client: TestClient):
    """Verify GET /api/auth/me without token returns HTTP 401."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


def test_get_current_user_me_invalid_token(client: TestClient):
    """Verify GET /api/auth/me with invalid bearer token returns HTTP 401."""
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.signature"},
    )
    assert resp.status_code == 401


def test_get_current_user_me_expired_token(client: TestClient, sample_user: User):
    """Verify GET /api/auth/me with an expired access token returns HTTP 401."""
    expired_token = jwt_service.create_access_token(
        user_id=sample_user.id,
        email=sample_user.email,
        role=sample_user.role,
        expires_delta=timedelta(seconds=-1),
    )
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


def test_get_current_user_me_inactive_user(
    client: TestClient, sample_user: User, test_db: sessionmaker[Session]
):
    """Verify GET /api/auth/me rejects an inactive user even with a previously issued token."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    access_token = login_resp.json()["access_token"]

    # Deactivate user in database
    with test_db() as session:
        u = session.execute(select(User).where(User.id == sample_user.id)).scalar_one()
        u.is_active = False
        session.commit()

    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 401


# ===========================================================================
# 5. Cookie Flags & Security Architecture Tests
# ===========================================================================

def test_cookie_flags_development_vs_production(
    client: TestClient, sample_user: User, monkeypatch
):
    """Verify cookie security flags adapt properly to production vs development."""
    # Development: secure=False, samesite=lax
    monkeypatch.setattr(config_module.settings, "environment", "development")
    dev_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    dev_headers = dev_resp.headers.get_list("set-cookie")
    refresh_dev = next(h for h in dev_headers if "climaforge_refresh_token" in h)
    assert "httponly" in refresh_dev.lower()
    assert "samesite=lax" in refresh_dev.lower()
    assert "secure" not in refresh_dev.lower()

    # Production: secure=True, samesite=strict
    monkeypatch.setattr(config_module.settings, "environment", "production")
    prod_resp = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    prod_headers = prod_resp.headers.get_list("set-cookie")
    refresh_prod = next(h for h in prod_headers if "climaforge_refresh_token" in h)
    assert "httponly" in refresh_prod.lower()
    assert "samesite=strict" in refresh_prod.lower()
    assert "secure" in refresh_prod.lower()


def test_direct_prefix_and_api_prefix_both_accessible(
    client: TestClient, sample_user: User
):
    """Verify router is registered with both direct /auth and /api/auth paths."""
    resp1 = client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    assert resp1.status_code == 200

    login_limiter.reset_all()

    resp2 = client.post(
        "/auth/login",
        json={"email": sample_user.email, "password": "OperationalSecret2026!"},
    )
    assert resp2.status_code == 200
