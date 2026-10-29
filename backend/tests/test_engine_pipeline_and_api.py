"""Integration tests for Risk Engine Pipeline and Scenario Analysis API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.engine.pipeline import execute_risk_engine
from app.main import app
from app.schemas.scenario_data import get_scenario_by_id


class TestPipelineDeterminismAndExecution:
    """Tests for pure deterministic calculation pipeline."""

    def test_deterministic_repeatability(self):
        """Identical inputs must produce strictly identical outputs."""
        zones = [
            {
                "zone_id": "ZONE-REP-1",
                "name": "Repeat Zone 1",
                "rainfall": 115.0,
                "drainage": 35.0,
                "elevation": 5.0,
                "water_level": 2.1,
                "population": 15000,
                "critical_infra": 3,
                "road_length": 6.0,
                "emergency_routes": 2,
            },
            {
                "zone_id": "ZONE-REP-2",
                "name": "Repeat Zone 2",
                "rainfall": 40.0,
                "drainage": 80.0,
                "elevation": 25.0,
                "water_level": 0.4,
                "population": 5000,
                "critical_infra": 1,
                "road_length": 3.0,
                "emergency_routes": 1,
            },
        ]
        run1 = execute_risk_engine(zones, scenario_id="repeat-test")
        run2 = execute_risk_engine(zones, scenario_id="repeat-test")

        assert run1["highest_risk_score"] == run2["highest_risk_score"]
        assert run1["hotspot_count"] == run2["hotspot_count"]
        assert run1["pipeline_status"] == run2["pipeline_status"]
        for z1, z2 in zip(run1["zones"], run2["zones"]):
            assert z1["score"] == z2["score"]
            assert z1["severity"] == z2["severity"]
            assert z1["dominant_cause"] == z2["dominant_cause"]
        for e1, e2 in zip(run1["exposure_results"], run2["exposure_results"]):
            assert e1["impact_score"] == e2["impact_score"]

    def test_baseline_scenario_triggers_monitoring_only(self):
        scenario = get_scenario_by_id("scenario-baseline")
        assert scenario is not None

        raw_zones = [z.model_dump() for z in scenario.zones]
        result = execute_risk_engine(raw_zones, scenario_id=scenario.scenario_id)

        assert result["is_monitoring_only"] is True
        assert result["pipeline_status"] == "MONITORING_ONLY"
        assert result["hotspot_count"] == 0
        assert result["exposure_results"] == []


class TestScenarioAnalysisAPI:
    """Tests for POST /api/scenarios/{id}/analyze and ad-hoc endpoints."""

    @pytest.mark.asyncio
    async def test_analyze_valid_scenario(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/scenarios/scenario-monsoon-alert/analyze")
            assert response.status_code == 200
            data = response.json()

            assert data["scenario_id"] == "scenario-monsoon-alert"
            assert "CLIMAFORGE-ALGORITHMS-0-5-v2.0" in data["spec_version"]
            assert "SYNTHETIC / ILLUSTRATIVE" in data["data_label"]
            assert len(data["executed_algorithms"]) == 13
            assert data["cascade_status"] == "SUCCESS"
            assert data["consequence_graph"] is not None
            assert data["cascade_analysis"] is not None
            assert data["critical_nodes"] is not None
            assert data["break_points"] is not None
            assert data["critical_nodes"]["critical_node"] is not None
            assert len(data["break_points"]["ranked_break_points"]) > 0
            assert data["zone_count"] == 4
            assert data["scorable_zone_count"] == 4
            assert data["hotspot_count"] >= 1
            assert len(data["zones"]) == 4
            assert len(data["exposure_results"]) == data["hotspot_count"]

            # Validate structure of individual zone result
            zone1 = data["zones"][0]
            assert "score" in zone1
            assert 0.0 <= zone1["score"] <= 100.0
            assert zone1["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert zone1["dominant_cause"] is not None

    @pytest.mark.asyncio
    async def test_analyze_flash_flood_critical_scenario(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/scenarios/scenario-flash-flood/analyze")
            assert response.status_code == 200
            data = response.json()

            assert data["pipeline_status"] in ["SUCCESS", "HOTSPOTS_DETECTED"]
            assert data["hotspot_count"] >= 2
            assert data["highest_risk_score"] >= 75.0  # CRITICAL peak
            assert len(data["exposure_results"]) >= 2
            for exp in data["exposure_results"]:
                assert 0.0 <= exp["impact_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_unknown_scenario_returns_404(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/scenarios/non-existent-scenario-999/analyze")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_adhoc_analysis_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "scenario_id": "adhoc-test",
                "scenario_name": "Ad-Hoc River Sector",
                "hotspot_threshold": 50.0,
                "zones": [
                    {
                        "zone_id": "ADHOC-1",
                        "name": "Custom Inundation Basin",
                        "rainfall": 130.0,
                        "drainage": 20.0,
                        "elevation": 3.5,
                        "water_level": 2.5,
                        "population": 22000,
                        "critical_infra": 4,
                        "road_length": 8.0,
                        "emergency_routes": 2,
                    }
                ],
            }
            response = await client.post("/api/scenarios/run/adhoc", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["zone_count"] == 1
            assert data["hotspot_count"] == 1
            assert data["zones"][0]["score"] >= 75.0

    @pytest.mark.asyncio
    async def test_adhoc_empty_zones_returns_422(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/scenarios/run/adhoc", json={"zones": []})
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_analysis_records_authentic_audit_event(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Run analysis
            await client.post("/api/scenarios/scenario-baseline/analyze")

            # Check audit logs
            log_res = await client.get("/api/audit-logs")
            assert log_res.status_code == 200
            logs = log_res.json()
            analysis_events = [l for l in logs if l["event_type"] == "ANALYSIS_RUN"]
            assert len(analysis_events) >= 1
            assert "Dry Season Baseline" in analysis_events[0]["description"]
