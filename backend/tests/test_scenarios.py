"""Tests for Scenarios API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_list_scenarios():
    """Verify GET /api/scenarios returns available scenarios with summary metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/scenarios")
        assert response.status_code == 200
        scenarios = response.json()
        assert len(scenarios) >= 3

        ids = [s["scenario_id"] for s in scenarios]
        assert "scenario-baseline" in ids
        assert "scenario-monsoon-alert" in ids
        assert "scenario-flash-flood" in ids

        for s in scenarios:
            assert "name" in s
            assert "severity" in s
            assert "zone_count" in s
            assert s["zone_count"] >= 1
            assert "hotspot_count" in s
            assert "highest_risk_score" in s
            assert 0.0 <= s["highest_risk_score"] <= 1.0
            assert "SYNTHETIC / ILLUSTRATIVE" in s["data_label"]


@pytest.mark.asyncio
async def test_get_scenario_detail():
    """Verify GET /api/scenarios/{id} returns comprehensive zone, node, and intervention data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/scenarios/scenario-flash-flood")
        assert response.status_code == 200
        detail = response.json()

        assert detail["scenario_id"] == "scenario-flash-flood"
        assert detail["severity"] == "CRITICAL"
        assert detail["hotspot_count"] == 2
        assert len(detail["zones"]) == 4
        assert len(detail["nodes"]) >= 4
        assert len(detail["interventions"]) >= 2
        assert "PENDING_MILESTONE_2" in detail["analysis_engine_status"]

        # Validate zone attributes
        for z in detail["zones"]:
            assert "zone_id" in z
            assert "risk_score" in z
            assert 0.0 <= z["risk_score"] <= 1.0
            assert "severity" in z
            assert "schematic_x" in z
            assert "schematic_y" in z
            assert z["data_provenance"] == "SYNTHETIC_SCENARIO_PROTOTYPE"


@pytest.mark.asyncio
async def test_get_nonexistent_scenario():
    """Verify 404 is returned when an invalid scenario ID is queried."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/scenarios/scenario-non-existent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
