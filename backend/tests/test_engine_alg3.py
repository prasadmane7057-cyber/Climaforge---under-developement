"""Unit tests for Algorithm 3 — Flood Impact / Exposure Calculation."""

import pytest
from app.engine.alg0_data_prep import prepare_zone_data
from app.engine.alg3_exposure import compute_hotspot_exposures, compute_zone_exposure


class TestAlgorithm3Exposure:
    """Tests for exposure normalization, ImpactScore weighting, and hotspot filtering."""

    def test_canonical_worked_example_page_13(self):
        """Canonical Worked Example Zone A from Report Page 13:

        Assumed Zone A:
        - 18,000 people (norm = 18000 / 25000 = 0.72)
        - 3 critical facilities (norm = 3 / 5 = 0.60)
        - 6 km road (norm = 6 / 10 = 0.60)
        - 2 emergency routes (norm = 2 / 3 = 0.667)
        Assumed weights u = (P: 0.35, I: 0.25, Rd: 0.20, Em: 0.20)
        ImpactScore = 0.35*0.72 + 0.25*0.60 + 0.20*0.60 + 0.20*(2/3)
                    = 0.252 + 0.150 + 0.120 + 0.1333 = 0.6553... -> round(0.655, 3)
        """
        raw = {
            "zone_id": "ZONE-A",
            "name": "Zone A Worked Example",
            "rainfall": 120.0,
            "drainage": 30.0,
            "population": 18000,
            "critical_infra": 3,
            "road_length": 6.0,
            "emergency_routes": 2,
        }
        prep = prepare_zone_data(raw)
        res = compute_zone_exposure(prep)

        assert res["impact_score"] == 0.655
        assert res["population_score"] == 0.72
        assert res["infrastructure_score"] == 0.6
        assert res["road_score"] == 0.6
        assert round(res["emergency_score"], 3) == 0.667
        assert res["status"] == "COMPLETE"
        # Verify raw counts are distinct from normalized scores
        assert res["raw_counts"]["population"] == 18000
        assert res["raw_counts"]["critical_infra"] == 3
        assert res["raw_counts"]["road_length_km"] == 6.0
        assert res["raw_counts"]["emergency_routes"] == 2

    def test_missing_exposure_component_rescaling(self):
        """When an exposure component is missing, available weights are rescaled."""
        raw = {
            "zone_id": "ZONE-EXP-PARTIAL",
            "rainfall": 100.0,
            "drainage": 20.0,
            "population": 25000,   # norm = 1.0 (weight 0.35)
            "critical_infra": 5,   # norm = 1.0 (weight 0.25)
            # road_length and emergency_routes missing
        }
        prep = prepare_zone_data(raw)
        res = compute_zone_exposure(prep)

        # Available weight sum = 0.35 + 0.25 = 0.60
        # ImpactScore = (0.35*1.0 + 0.25*1.0)/0.60 = 1.0
        assert res["impact_score"] == 1.0
        assert res["status"] == "PARTIAL_RESCALED"
        assert "missing_exposure_road_length" in res["flags"]
        assert "missing_exposure_emergency_routes" in res["flags"]
        assert res["road_score"] is None
        assert res["emergency_score"] is None

    def test_all_exposure_components_missing_yields_data_insufficient(self):
        raw = {
            "zone_id": "ZONE-NO-EXP",
            "rainfall": 90.0,
            "drainage": 30.0,
        }
        prep = prepare_zone_data(raw)
        res = compute_zone_exposure(prep)
        assert res["impact_score"] is None
        assert res["status"] == "DATA_INSUFFICIENT"
        assert "all_exposure_components_missing" in res["flags"]

    def test_hotspot_exposures_skipped_under_monitoring_only(self):
        """Per report page 12: If is_monitoring_only is True, downstream exposure is skipped."""
        res = compute_hotspot_exposures(
            hotspot_zones=[],
            prepared_zones_map={},
            is_monitoring_only=True,
        )
        assert res["status"] == "SKIPPED_MONITORING_ONLY"
        assert res["exposures"] == []
