"""Tests for Milestone 7: Emergency Incident Synchronization & Offline SOS Outbox."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
import uuid

from fastapi import status
import pytest
from sqlalchemy import select
from starlette.testclient import TestClient

from app import config as config_module
from app.db.base import Base
from app.db.session import create_db_engine, get_db, get_session_factory
from app.main import app
from app.models.incident import Incident
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.models.user import User
from app.routers.audit import SESSION_AUDIT_LOGS
from app.schemas.contracts import IncidentRecord, IncidentStatus, UrgencyLevel
from app.schemas.incidents import IncidentSyncItem, IncidentSyncRequest
from app.security.jwt import jwt_service
from app.security.passwords import password_service
from app.security.rbac import (
    ALL_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_ROLES,
    ROLE_AUDITOR,
    ROLE_OPERATOR,
    ROLE_VIEWER,
)


@pytest.fixture
def incident_test_db(tmp_path: Path, monkeypatch):
    """Isolated test database with canonical roles and permissions for incident testing."""
    db_file = tmp_path / f"test_incidents_{uuid.uuid4().hex}.db"
    db_url = f"sqlite:///{db_file}"

    monkeypatch.setattr(config_module.settings, "jwt_signing_key", "k" * 32)
    monkeypatch.setattr(config_module.settings, "jwt_issuer", "climaforge")
    monkeypatch.setattr(config_module.settings, "jwt_audience", "climaforge-api")
    monkeypatch.setattr(config_module.settings, "refresh_token_pepper", "p" * 32)
    monkeypatch.setattr(config_module.settings, "access_token_minutes", 15)
    monkeypatch.setattr(config_module.settings, "refresh_token_days", 7)
    monkeypatch.setattr(config_module.settings, "database_url", db_url)

    engine = create_db_engine(db_url)
    Base.metadata.create_all(bind=engine)
    factory = get_session_factory(engine)

    with factory() as session:
        role_map: Dict[str, Role] = {}
        for r_name in DEFAULT_ROLES:
            role = Role(name=r_name, description=f"{r_name} role")
            session.add(role)
            role_map[r_name] = role

        perm_map: Dict[str, Permission] = {}
        for p_code in ALL_PERMISSIONS:
            perm = Permission(name=p_code, description=f"{p_code} permission")
            session.add(perm)
            perm_map[p_code] = perm

        session.flush()

        for r_name, p_codes in DEFAULT_ROLE_PERMISSIONS.items():
            role_obj = role_map[r_name]
            for p_code in p_codes:
                perm_obj = perm_map[p_code]
                session.add(RolePermission(role_id=role_obj.id, permission_id=perm_obj.id))

        # 1. Operator user (has scenario.read)
        operator_user = User(
            id=str(uuid.uuid4()),
            email="operator_incident@climaforge.test",
            hashed_password=password_service.hash_password("OperatorPass123!"),
            full_name="Incident Operator",
            role=ROLE_OPERATOR,
            is_active=True,
        )
        session.add(operator_user)
        session.flush()
        session.add(UserRole(user_id=operator_user.id, role_id=role_map[ROLE_OPERATOR].id))

        # 2. Auditor user (lacks scenario.read - only audit.read)
        auditor_user = User(
            id=str(uuid.uuid4()),
            email="auditor_incident@climaforge.test",
            hashed_password=password_service.hash_password("AuditorPass123!"),
            full_name="Compliance Auditor",
            role=ROLE_AUDITOR,
            is_active=True,
        )
        session.add(auditor_user)
        session.flush()
        session.add(UserRole(user_id=auditor_user.id, role_id=role_map[ROLE_AUDITOR].id))

        session.commit()

    def override_get_db():
        with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    yield factory, operator_user, auditor_user
    app.dependency_overrides.pop(get_db, None)


def _get_token(user: User) -> str:
    return jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


# -----------------------------------------------------------------------------
# Unit & Integration Tests
# -----------------------------------------------------------------------------

def test_sync_single_incident(incident_test_db):
    """Verify that a single queued incident syncs successfully and is stored in database."""
    factory, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    incident_id = str(uuid.uuid4())
    payload = {
        "incidents": [
            {
                "incident_id": incident_id,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "incident_type": "RISING_WATER",
                "urgency": "HIGH",
                "status": "NOT_SENT",
                "description": "Rapid water level rise observed near industrial embankment.",
            }
        ]
    }

    response = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["scenario_id"] == "scenario-flash-flood"
    assert incident_id in data["synced_incident_ids"]
    assert data["duplicate_incident_ids"] == []
    assert data["total_synced"] == 1
    assert data["status"] == "ACKNOWLEDGED"

    # Verify durable database persistence
    with factory() as session:
        stored = session.execute(
            select(Incident).where(Incident.incident_id == incident_id)
        ).scalar_one_or_none()
        assert stored is not None
        assert stored.scenario_id == "scenario-flash-flood"
        assert stored.incident_type == "RISING_WATER"
        assert stored.urgency == "HIGH"
        assert stored.status == "ACKNOWLEDGED"


def test_sync_batch_incidents(incident_test_db):
    """Verify that a batch of distinct incidents syncs atomically."""
    factory, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    id_1 = str(uuid.uuid4())
    id_2 = str(uuid.uuid4())
    id_3 = str(uuid.uuid4())

    payload = {
        "incidents": [
            {
                "incident_id": id_1,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "incident_type": "MEDICAL_EMERGENCY",
                "urgency": "CRITICAL",
                "status": "NOT_SENT",
                "description": "Elderly resident requires medical evacuation.",
            },
            {
                "incident_id": id_2,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-002",
                "incident_type": "ROAD_BLOCKED",
                "urgency": "MEDIUM",
                "status": "NOT_SENT",
                "description": "Downed tree blocking northbound access road.",
            },
            {
                "incident_id": id_3,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "incident_type": "STRANDED_PERSONS",
                "urgency": "HIGH",
                "status": "NOT_SENT",
                "description": "Two individuals stranded on high ground.",
            },
        ]
    }

    response = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_synced"] == 3
    assert set(data["synced_incident_ids"]) == {id_1, id_2, id_3}

    # Verify all 3 stored in DB
    with factory() as session:
        count = session.execute(
            select(Incident).where(Incident.incident_id.in_([id_1, id_2, id_3]))
        ).scalars().all()
        assert len(count) == 3


def test_sync_idempotency_duplicate_incident_ids(incident_test_db):
    """Verify that repeating the same sync request does not duplicate database rows."""
    factory, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    incident_id = str(uuid.uuid4())
    payload = {
        "incidents": [
            {
                "incident_id": incident_id,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "incident_type": "RISING_WATER",
                "urgency": "HIGH",
                "status": "NOT_SENT",
                "description": "Idempotency verification report.",
            }
        ]
    }

    # First submission: newly stored
    r1 = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r1.status_code == status.HTTP_200_OK
    assert incident_id in r1.json()["synced_incident_ids"]
    assert r1.json()["total_synced"] == 1
    assert r1.json()["total_duplicates"] == 0

    # Second submission: recognized as duplicate, NOT inserted again
    r2 = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r2.status_code == status.HTTP_200_OK
    assert incident_id in r2.json()["duplicate_incident_ids"]
    assert r2.json()["synced_incident_ids"] == []
    assert r2.json()["total_synced"] == 0
    assert r2.json()["total_duplicates"] == 1
    assert r2.json()["status"] == "NO_NEW_DATA"

    # Confirm only exactly one row exists in database
    with factory() as session:
        records = session.execute(
            select(Incident).where(Incident.incident_id == incident_id)
        ).scalars().all()
        assert len(records) == 1


def test_sync_partial_duplicate_batch(incident_test_db):
    """Verify that a batch with both new and previously synced items stores only the new ones."""
    _, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    id_old = str(uuid.uuid4())
    id_new = str(uuid.uuid4())

    # Pre-sync id_old
    client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "incidents": [
                {
                    "incident_id": id_old,
                    "reported_at": datetime.now(timezone.utc).isoformat(),
                    "zone_id": "ZONE-001",
                    "incident_type": "RISING_WATER",
                    "description": "Pre-existing item.",
                }
            ]
        },
    )

    # Batch with both id_old and id_new
    r = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "incidents": [
                {
                    "incident_id": id_old,
                    "reported_at": datetime.now(timezone.utc).isoformat(),
                    "zone_id": "ZONE-001",
                    "incident_type": "RISING_WATER",
                    "description": "Pre-existing item again.",
                },
                {
                    "incident_id": id_new,
                    "reported_at": datetime.now(timezone.utc).isoformat(),
                    "zone_id": "ZONE-002",
                    "incident_type": "ROAD_BLOCKED",
                    "description": "Brand new item.",
                },
            ]
        },
    )

    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["synced_incident_ids"] == [id_new]
    assert data["duplicate_incident_ids"] == [id_old]
    assert data["total_synced"] == 1
    assert data["total_duplicates"] == 1


def test_sync_invalid_uuid_rejected(incident_test_db):
    """Verify that an invalid UUID in request payload is rejected with 422."""
    _, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    payload = {
        "incidents": [
            {
                "incident_id": "not-a-valid-uuid",
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "incident_type": "RISING_WATER",
                "description": "Invalid UUID test.",
            }
        ]
    }

    response = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_sync_invalid_incident_type_rejected(incident_test_db):
    """Verify that an unrecognized incident category is rejected with 422."""
    _, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    payload = {
        "incidents": [
            {
                "incident_id": str(uuid.uuid4()),
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "incident_type": "UNSUPPORTED_CAT_DOG",
                "description": "Invalid category test.",
            }
        ]
    }

    response = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_sync_requires_authentication(incident_test_db):
    """Verify that incident sync rejects requests without valid JWT with 401."""
    client = TestClient(app)

    response = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        json={"incidents": []},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_sync_rbac_forbidden_for_auditor(incident_test_db):
    """Verify that a role lacking scenario.read (AUDITOR) receives 403 Forbidden."""
    _, _, auditor_user = incident_test_db
    token = _get_token(auditor_user)
    client = TestClient(app)

    response = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={"incidents": []},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_sync_nonexistent_scenario(incident_test_db):
    """Verify that syncing against a nonexistent scenario returns 404."""
    _, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    response = client.post(
        "/api/scenarios/scenario-nonexistent-999/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={"incidents": []},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_sync_emits_authentic_audit_event(incident_test_db):
    """Verify that successful synchronization appends an INCIDENT_SYNC event to SESSION_AUDIT_LOGS."""
    _, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    init_audit_count = len(SESSION_AUDIT_LOGS)
    inc_id = str(uuid.uuid4())

    client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "incidents": [
                {
                    "incident_id": inc_id,
                    "reported_at": datetime.now(timezone.utc).isoformat(),
                    "zone_id": "ZONE-001",
                    "incident_type": "RISING_WATER",
                    "description": "Emits audit event test.",
                }
            ]
        },
    )

    assert len(SESSION_AUDIT_LOGS) > init_audit_count
    latest_event = SESSION_AUDIT_LOGS[-1]
    assert latest_event.event_type == "INCIDENT_SYNC"
    assert latest_event.source == "INCIDENT_SERVICE"
    assert latest_event.details["synced_count"] == "1"
    assert latest_event.details["scenario_id"] == "scenario-flash-flood"


def test_get_scenario_incidents(incident_test_db):
    """Verify that GET /scenarios/{id}/incidents retrieves stored incidents ordered by reported_at desc."""
    _, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    id_1 = str(uuid.uuid4())
    id_2 = str(uuid.uuid4())

    # Sync two incidents for scenario-flash-flood
    client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "incidents": [
                {
                    "incident_id": id_1,
                    "reported_at": "2026-11-10T08:00:00Z",
                    "zone_id": "ZONE-001",
                    "incident_type": "RISING_WATER",
                    "urgency": "MEDIUM",
                    "description": "Earlier incident report.",
                },
                {
                    "incident_id": id_2,
                    "reported_at": "2026-11-10T08:30:00Z",
                    "zone_id": "ZONE-001",
                    "incident_type": "MEDICAL_EMERGENCY",
                    "urgency": "CRITICAL",
                    "description": "Later urgent incident report.",
                },
            ]
        },
    )

    # Fetch incidents
    response = client.get(
        "/api/scenarios/scenario-flash-flood/incidents",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    items = response.json()
    assert len(items) >= 2
    # Verify ordering: newer reported_at first
    returned_ids = [item["incident_id"] for item in items]
    assert returned_ids.index(id_2) < returned_ids.index(id_1)


def test_cross_scenario_isolation(incident_test_db):
    """Verify that incidents stored in scenario A are not exposed under scenario B."""
    _, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    inc_id = str(uuid.uuid4())

    # Store in scenario-flash-flood
    client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "incidents": [
                {
                    "incident_id": inc_id,
                    "reported_at": datetime.now(timezone.utc).isoformat(),
                    "zone_id": "ZONE-001",
                    "incident_type": "RISING_WATER",
                    "description": "Isolated to flash-flood scenario.",
                }
            ]
        },
    )

    # Query scenario-monsoon-alert: inc_id must NOT be present
    res_b = client.get(
        "/api/scenarios/scenario-monsoon-alert/incidents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_b.status_code == status.HTTP_200_OK
    b_ids = [item["incident_id"] for item in res_b.json()]
    assert inc_id not in b_ids


def test_concurrent_duplicate_sync(incident_test_db):
    """Verify that concurrent duplicate submissions handle idempotency safely."""
    import concurrent.futures

    factory, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    shared_id = str(uuid.uuid4())
    payload = {
        "incidents": [
            {
                "incident_id": shared_id,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "incident_type": "RISING_WATER",
                "urgency": "HIGH",
                "status": "NOT_SENT",
                "description": "Concurrent duplicate verification report.",
            }
        ]
    }

    def send_sync():
        return client.post(
            "/api/scenarios/scenario-flash-flood/incidents/sync",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_sync) for _ in range(3)]
        responses = [f.result() for f in futures]

    for r in responses:
        assert r.status_code == status.HTTP_200_OK

    total_synced = sum(r.json()["total_synced"] for r in responses)
    total_duplicates = sum(r.json()["total_duplicates"] for r in responses)
    assert total_synced == 1
    assert total_duplicates == 2

    # Exactly one record in database
    with factory() as session:
        rows = session.execute(
            select(Incident).where(Incident.incident_id == shared_id)
        ).scalars().all()
        assert len(rows) == 1


def test_database_failure_rollback(incident_test_db, monkeypatch):
    """Verify that a database failure during commit triggers rollback and HTTP 500 without acknowledging."""
    from sqlalchemy.orm import Session as SqlSession

    factory, operator_user, _ = incident_test_db
    token = _get_token(operator_user)
    client = TestClient(app)

    # Monkeypatch commit to fail
    def failing_commit(self):
        raise RuntimeError("Simulated catastrophic disk write failure")

    monkeypatch.setattr(SqlSession, "commit", failing_commit)

    inc_id = str(uuid.uuid4())
    payload = {
        "incidents": [
            {
                "incident_id": inc_id,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "zone_id": "ZONE-001",
                "incident_type": "MEDICAL_EMERGENCY",
                "urgency": "CRITICAL",
                "status": "NOT_SENT",
                "description": "Should fail and rollback.",
            }
        ]
    }

    response = client.post(
        "/api/scenarios/scenario-flash-flood/incidents/sync",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Durable database persistence failed" in response.json()["detail"]
