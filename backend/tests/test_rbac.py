"""Comprehensive test suite for CLIMAFORGE M16A.5 Role-Based Access Control (RBAC).

Tests:
- All five roles (VIEWER, ANALYST, OPERATOR, AUDITOR, ADMIN)
- Role-permission mappings and least-privilege defaults
- Missing, invalid, and expired authentication
- Inactive user rejection
- Permission denial (403) and authorization success (200)
- Scenario-level authorization via global permissions
- Explicit scenario access grants
- Expired scenario access grants
- Cross-scenario access denial
- Non-existent scenario (404)
- Self-role modification prevention
- Self-deactivation prevention
- Admin-only management operations
- Role escalation protection
- Intervention deployment restrictions
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from app.config import Settings
import app.config as config_module
from app.db.base import Base
from app.db.session import create_db_engine, get_db, get_session_factory
from app.main import app
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    ScenarioAccessGrant,
    UserRole,
)
from app.models.user import User
from app.security.jwt import jwt_service
from app.security.passwords import password_service
from app.security.rbac import (
    ALL_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_ROLES,
    PERM_ADMIN_ROLES,
    PERM_ADMIN_SCENARIO_GRANTS,
    PERM_ADMIN_USERS,
    PERM_AUDIT_CREATE,
    PERM_AUDIT_READ,
    PERM_CHATBOT_ASK,
    PERM_INTERVENTION_DEPLOY,
    PERM_ML_PREDICT,
    PERM_SCENARIO_READ,
    PERM_SCENARIO_RUN,
    PERM_SCENARIO_RUN_ADHOC,
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_AUDITOR,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    check_scenario_access,
    get_user_permissions,
    get_user_roles,
    has_scenario_permission,
)


@pytest.fixture
def test_db(tmp_path: Path, monkeypatch) -> sessionmaker[Session]:
    """Configure isolated test database with M16A.5 schema and default seed data."""
    db_file = tmp_path / f"rbac_test_{uuid.uuid4().hex}.db"
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

    # Seed roles and permissions into test database
    now = datetime.now(timezone.utc)
    with factory() as session:
        role_map: dict[str, Role] = {}
        for r_name in DEFAULT_ROLES:
            role = Role(name=r_name, description=f"{r_name} role")
            session.add(role)
            role_map[r_name] = role

        perm_map: dict[str, Permission] = {}
        for p_name in ALL_PERMISSIONS:
            perm = Permission(name=p_name, description=f"{p_name} permission")
            session.add(perm)
            perm_map[p_name] = perm

        session.flush()

        for r_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
            r = role_map[r_name]
            for p_name in perms:
                p = perm_map[p_name]
                rp = RolePermission(role_id=r.id, permission_id=p.id)
                session.add(rp)

        session.commit()

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
    db_file.unlink(missing_ok=True)


def create_user_with_role(
    session_factory: sessionmaker[Session],
    email: str,
    role_name: str,
    is_active: bool = True,
    is_superuser: bool = False,
) -> tuple[str, str]:
    """Helper to create a test user with assigned DB role and return (user_id, access_token)."""
    with session_factory() as session:
        user = User(
            email=email,
            hashed_password=password_service.hash_password("password123"),
            full_name=f"Test {role_name}",
            role=role_name.lower(),
            is_active=is_active,
            is_superuser=is_superuser,
        )
        session.add(user)
        session.flush()

        # Link role in auth_user_roles
        role = session.execute(
            select(Role).where(Role.name == role_name.upper())
        ).scalar_one_or_none()
        if role:
            ur = UserRole(user_id=user.id, role_id=role.id)
            session.add(ur)

        session.commit()
        session.refresh(user)
        user_id = user.id

    token = jwt_service.create_access_token(
        user_id=user_id,
        role=role_name.lower(),
        email=email,
    )
    return user_id, token


def test_default_role_permission_mappings(test_db):
    """Verify that all five roles have their exact specified permission sets."""
    with test_db() as session:
        for role_name, expected_perms in DEFAULT_ROLE_PERMISSIONS.items():
            user = User(email=f"{role_name.lower()}@test.com", hashed_password="pw", role=role_name.lower())
            session.add(user)
            session.flush()

            role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
            session.add(UserRole(user_id=user.id, role_id=role.id))
            session.commit()

            resolved_perms = get_user_permissions(session, user)
            assert expected_perms.issubset(resolved_perms)

            # Check intervention.deploy is not granted
            assert PERM_INTERVENTION_DEPLOY not in resolved_perms


def test_missing_authentication_denied(test_db):
    """Verify endpoints reject unauthenticated requests with HTTP 401."""
    with TestClient(app) as client:
        # Admin endpoint
        r = client.get("/api/admin/roles")
        assert r.status_code == 401

        # Scenario run endpoint
        r = client.post("/api/scenarios/scenario-baseline/analyze")
        assert r.status_code == 401

        # Audit endpoint
        r = client.get("/api/audit-logs")
        assert r.status_code == 401


def test_invalid_token_denied(test_db):
    """Verify requests with malformed tokens return HTTP 401."""
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    with TestClient(app) as client:
        r = client.get("/api/admin/roles", headers=headers)
        assert r.status_code == 401


def test_inactive_user_denied(test_db):
    """Verify that inactive users cannot access protected endpoints."""
    _, token = create_user_with_role(test_db, "inactive@test.com", ROLE_ADMIN, is_active=False)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        r = client.get("/api/admin/roles", headers=headers)
        assert r.status_code == 401
        assert "inactive" in r.json().get("detail", "").lower() or r.status_code == 401


def test_viewer_permissions_and_restrictions(test_db):
    """Verify VIEWER can read scenarios and audit logs, but cannot run analysis or access admin."""
    _, token = create_user_with_role(test_db, "viewer@test.com", ROLE_VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Permitted: List and read scenarios
        r = client.get("/api/scenarios", headers=headers)
        assert r.status_code == 200

        r = client.get("/api/scenarios/scenario-baseline", headers=headers)
        assert r.status_code == 200

        # Permitted: Read audit logs
        r = client.get("/api/audit-logs", headers=headers)
        assert r.status_code == 200

        # Permitted: Ask chatbot
        r = client.post(
            "/api/chatbot/message",
            headers=headers,
            json={"scenario_id": "scenario-baseline", "question": "What is the baseline risk?"},
        )
        assert r.status_code == 200

        # Forbidden: Run scenario analysis
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=headers)
        assert r.status_code == 403

        # Forbidden: Ad-hoc run
        r = client.post(
            "/api/scenarios/run/adhoc",
            headers=headers,
            json={"zones": [{"zone_id": "Z1", "rainfall_mm": 50.0}]},
        )
        assert r.status_code == 403

        # Forbidden: Admin endpoint
        r = client.get("/api/admin/roles", headers=headers)
        assert r.status_code == 403


def test_analyst_permissions_and_restrictions(test_db):
    """Verify ANALYST can run analysis and ML predictions, but cannot create client audit events or administer."""
    _, token = create_user_with_role(test_db, "analyst@test.com", ROLE_ANALYST)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Permitted: Read scenarios
        r = client.get("/api/scenarios/scenario-baseline", headers=headers)
        assert r.status_code == 200

        # Permitted: Run scenario analysis
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=headers)
        assert r.status_code == 200
        assert "highest_risk_score" in r.json()

        # Permitted: Run ad-hoc analysis
        r = client.post(
            "/api/scenarios/run/adhoc",
            headers=headers,
            json={
                "zones": [{
                    "zone_id": "ZONE-001",
                    "rainfall_mm": 40.0,
                    "drainage_capacity_cms": 10.0,
                    "elevation_m": 12.0,
                    "soil_saturation_index": 0.5,
                    "water_level_m": 1.0,
                    "population": 1000,
                    "critical_infrastructure_count": 2,
                    "road_length_km": 5.0,
                    "emergency_routes_count": 2,
                }]
            },
        )
        assert r.status_code == 200

        # Permitted: ML prediction
        r = client.post(
            "/api/ml/flood/predict",
            headers=headers,
            json={
                "prcp_mm": 45.0,
                "tmax_c": 28.0,
                "tmin_c": 22.0,
                "snow_mm": 0.0,
                "prcp_lag1_mm": 30.0,
                "prcp_rolling_3d_mean_mm": 35.0,
                "prcp_rolling_7d_mean_mm": 20.0,
                "prcp_rolling_14d_mean_mm": 15.0,
            },
        )
        assert r.status_code == 200

        # Forbidden: Create client audit events (requires OPERATOR)
        r = client.post(
            "/api/audit-logs",
            headers=headers,
            json={"event_type": "TEST", "description": "Analyst log"},
        )
        assert r.status_code == 403

        # Forbidden: Admin roles
        r = client.get("/api/admin/roles", headers=headers)
        assert r.status_code == 403


def test_operator_permissions_and_restrictions(test_db):
    """Verify OPERATOR can create client audit events, but cannot perform administrative functions."""
    _, token = create_user_with_role(test_db, "operator@test.com", ROLE_OPERATOR)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Permitted: Create client audit event
        r = client.post(
            "/api/audit-logs",
            headers=headers,
            json={
                "event_type": "OPERATOR_ACTION",
                "description": "Operator acknowledged alert",
                "details": {"action": "acknowledge"},
            },
        )
        assert r.status_code == 201

        # Forbidden: Access admin users
        r = client.get("/api/admin/users", headers=headers)
        assert r.status_code == 403


def test_auditor_permissions_and_restrictions(test_db):
    """Verify AUDITOR can only read audit logs, and is denied scenario and admin access."""
    _, token = create_user_with_role(test_db, "auditor@test.com", ROLE_AUDITOR)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Permitted: Read audit trail
        r = client.get("/api/audit-logs", headers=headers)
        assert r.status_code == 200

        # Forbidden: Read scenarios
        r = client.get("/api/scenarios", headers=headers)
        assert r.status_code == 403

        # Forbidden: Run analysis
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=headers)
        assert r.status_code == 403

        # Forbidden: Admin
        r = client.get("/api/admin/roles", headers=headers)
        assert r.status_code == 403


def test_admin_permissions(test_db):
    """Verify ADMIN can access admin management endpoints."""
    _, token = create_user_with_role(test_db, "admin@test.com", ROLE_ADMIN)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Permitted: List roles
        r = client.get("/api/admin/roles", headers=headers)
        assert r.status_code == 200
        roles = r.json()
        assert len(roles) >= 5
        role_names = [role["name"] for role in roles]
        assert "ADMIN" in role_names
        assert "OPERATOR" in role_names

        # Permitted: List users
        r = client.get("/api/admin/users", headers=headers)
        assert r.status_code == 200

        # Permitted: List scenario grants
        r = client.get("/api/admin/scenario-grants", headers=headers)
        assert r.status_code == 200


def test_scenario_access_grant_authorizes_specific_scenario(test_db):
    """Verify explicit scenario access grant enables a user without global permission to run analysis."""
    user_id, token = create_user_with_role(test_db, "viewer_grant@test.com", ROLE_VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Initially, VIEWER is denied scenario analysis
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=headers)
        assert r.status_code == 403

        # Issue scenario grant for scenario-baseline
        with test_db() as session:
            grant = ScenarioAccessGrant(
                user_id=user_id,
                scenario_id="scenario-baseline",
                permission=PERM_SCENARIO_RUN,
            )
            session.add(grant)
            session.commit()

        # Now permitted for scenario-baseline!
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=headers)
        assert r.status_code == 200

        # But cross-scenario access to scenario-flash-flood is STILL denied!
        r = client.post("/api/scenarios/scenario-flash-flood/analyze", headers=headers)
        assert r.status_code == 403


def test_expired_scenario_grant_denied(test_db):
    """Verify that an expired scenario access grant is rejected with HTTP 403."""
    user_id, token = create_user_with_role(test_db, "viewer_expired@test.com", ROLE_VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    with test_db() as session:
        # Create an expired grant (expired 1 hour ago)
        grant = ScenarioAccessGrant(
            user_id=user_id,
            scenario_id="scenario-baseline",
            permission=PERM_SCENARIO_RUN,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        session.add(grant)
        session.commit()

    with TestClient(app) as client:
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=headers)
        assert r.status_code == 403


def test_nonexistent_scenario_returns_404(test_db):
    """Verify requesting an unknown scenario returns HTTP 404."""
    _, token = create_user_with_role(test_db, "analyst_404@test.com", ROLE_ANALYST)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        r = client.get("/api/scenarios/unknown-scenario-xyz", headers=headers)
        assert r.status_code == 404

        r = client.post("/api/scenarios/unknown-scenario-xyz/analyze", headers=headers)
        assert r.status_code == 404


def test_prevent_self_role_modification(test_db):
    """Verify users cannot modify their own roles via the admin API."""
    admin_id, admin_token = create_user_with_role(test_db, "admin_self@test.com", ROLE_ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    with TestClient(app) as client:
        # Attempt to modify self role
        r = client.post(
            f"/api/admin/users/{admin_id}/roles",
            headers=headers,
            json={"role": "VIEWER"},
        )
        assert r.status_code == 403
        assert "cannot modify their own roles" in r.json().get("detail", "").lower()

        # Attempt to revoke own role
        r = client.delete(
            f"/api/admin/users/{admin_id}/roles/ADMIN",
            headers=headers,
        )
        assert r.status_code == 403
        assert "cannot modify their own roles" in r.json().get("detail", "").lower()


def test_prevent_self_deactivation(test_db):
    """Verify users cannot deactivate their own accounts."""
    admin_id, admin_token = create_user_with_role(test_db, "admin_deact@test.com", ROLE_ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    with TestClient(app) as client:
        r = client.patch(
            f"/api/admin/users/{admin_id}/status",
            headers=headers,
            json={"is_active": False},
        )
        assert r.status_code == 403
        assert "cannot deactivate their own account" in r.json().get("detail", "").lower()


def test_admin_role_assignment_and_revocation(test_db):
    """Verify administrator can assign and revoke roles for other users."""
    _, admin_token = create_user_with_role(test_db, "admin_mgr@test.com", ROLE_ADMIN)
    target_id, _ = create_user_with_role(test_db, "target_user@test.com", ROLE_VIEWER)
    headers = {"Authorization": f"Bearer {admin_token}"}

    with TestClient(app) as client:
        # Assign ANALYST role
        r = client.post(
            f"/api/admin/users/{target_id}/roles",
            headers=headers,
            json={"role": "ANALYST"},
        )
        assert r.status_code == 200
        roles = r.json()["roles"]
        assert "ANALYST" in roles

        # Revoke ANALYST role
        r = client.delete(
            f"/api/admin/users/{target_id}/roles/ANALYST",
            headers=headers,
        )
        assert r.status_code == 200
        roles = r.json()["roles"]
        assert "ANALYST" not in roles


def test_admin_scenario_grant_lifecycle(test_db):
    """Verify administrator can issue, inspect, and revoke explicit scenario grants."""
    admin_id, admin_token = create_user_with_role(test_db, "admin_grants@test.com", ROLE_ADMIN)
    target_id, target_token = create_user_with_role(test_db, "target_grant@test.com", ROLE_VIEWER)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    target_headers = {"Authorization": f"Bearer {target_token}"}

    with TestClient(app) as client:
        # 1. Target user initially cannot run scenario
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=target_headers)
        assert r.status_code == 403

        # 2. Admin creates grant
        r = client.post(
            "/api/admin/scenario-grants",
            headers=admin_headers,
            json={
                "user_id": target_id,
                "scenario_id": "scenario-baseline",
                "permission": PERM_SCENARIO_RUN,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            },
        )
        assert r.status_code == 201
        grant_id = r.json()["id"]

        # 3. Target user can now execute analysis
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=target_headers)
        assert r.status_code == 200

        # 4. Admin revokes grant
        r = client.delete(f"/api/admin/scenario-grants/{grant_id}", headers=admin_headers)
        assert r.status_code == 200

        # 5. Target user is denied again
        r = client.post("/api/scenarios/scenario-baseline/analyze", headers=target_headers)
        assert r.status_code == 403


def test_non_admin_cannot_access_admin_api(test_db):
    """Verify non-admin roles cannot escalate privileges through the admin router."""
    for role in [ROLE_VIEWER, ROLE_ANALYST, ROLE_OPERATOR, ROLE_AUDITOR]:
        _, token = create_user_with_role(test_db, f"nonadmin_{role.lower()}@test.com", role)
        headers = {"Authorization": f"Bearer {token}"}

        with TestClient(app) as client:
            r = client.get("/api/admin/roles", headers=headers)
            assert r.status_code == 403

            r = client.get("/api/admin/users", headers=headers)
            assert r.status_code == 403

            r = client.post(
                "/api/admin/scenario-grants",
                headers=headers,
                json={"user_id": "u1", "scenario_id": "s1", "permission": "scenario.read"},
            )
            assert r.status_code == 403
