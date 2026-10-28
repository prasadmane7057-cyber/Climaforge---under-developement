"""Tests for Audit Log API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_audit_logs():
    """Verify GET /api/audit-logs returns genuine recorded system events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/audit-logs")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) >= 3

        types = [log["event_type"] for log in logs]
        assert "SYSTEM_BOOT" in types

        for log in logs:
            assert "event_id" in log
            assert "timestamp" in log
            assert "source" in log
            assert "description" in log


@pytest.mark.asyncio
async def test_post_client_audit_event():
    """Verify POST /api/audit-logs records authentic client actions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        new_event_payload = {
            "event_type": "USER_NAVIGATION",
            "description": "Operator viewed Risk Map panel",
            "details": {"tab": "risk-map", "scenario_id": "scenario-monsoon-alert"},
        }
        post_response = await client.post("/api/audit-logs", json=new_event_payload)
        assert post_response.status_code == 201

        created = post_response.json()
        assert created["source"] == "FRONTEND"
        assert created["event_type"] == "USER_NAVIGATION"
        assert created["description"] == "Operator viewed Risk Map panel"

        # Verify event appears in audit logs list
        get_response = await client.get("/api/audit-logs")
        logs = get_response.json()
        matching = [l for l in logs if l["event_id"] == created["event_id"]]
        assert len(matching) == 1
