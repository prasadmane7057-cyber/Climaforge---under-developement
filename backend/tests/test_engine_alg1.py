"""Unit tests for Algorithm 1 — Flood Risk Score."""

import pytest
from app.engine.alg0_data_prep import prepare_zone_data
from app.engine.alg1_flood_risk import compute_all_flood_risks, compute_flood_risk


class TestAlgorithm1FloodRisk:
    """Tests for flood risk calculation, severity bands, and weight rescaling."""

    def test_canonical_worked_example_page_11(self):
        """Canonical Worked Example Zone A from Report Page 11:

        s = (R: 0.80, D: 0.70, W: 0.80, E: 0.70, H: 0.80)
        weights = (0.30, 0.25, 0.20, 0.15, 0.10)
        FloodRisk = 100 * (0.30*0.80 + 0.25*0.70 + 0.20*0.80 + 0.15*0.70 + 0.10*0.80)
                  = 100 * (0.24 + 0.175 + 0.16 + 0.105 + 0.08)
                  = 100 * 0.76 = 76.0 -> CRITICAL
        """
        # Reconstruct zone with raw values that normalize to these exact factors:
        # R = 0.80 * 150 = 120 mm
        # D: 1 - norm(D) = 0.70 => norm(D) = 0.30 => D = 30 cms
        # W = 0.80 * 3.0 = 2.4 m
        # E: 1 - norm(E) = 0.70 => norm(E) = 0.30 => E = 12 m
        # H = 0.80 * 5.0 = 4.0 events/yr
        raw = {
            "zone_id": "ZONE-A",
            "name": "Zone A Worked Example",
            "rainfall": 120.0,
            "drainage": 30.0,
            "water_level": 2.4,
            "elevation": 12.0,
            "history": 4.0,
        }
        prep = prepare_zone_data(raw)
        result = compute_flood_risk(prep)

        assert result is not None
        assert result["score"] == 76.0
        assert result["severity"] == "CRITICAL"
        assert result["is_hotspot"] is True
        assert result["dominant_cause"] in ["Rainfall Inundation", "River Water Stage"]

    def test_severity_boundaries(self):
        """Verify exact boundaries: >=75 CRITICAL, >=50 HIGH, >=25 MEDIUM, else LOW."""
        # Helper to create a synthetic zone with uniform factor values
        def make_uniform_zone(target_factor: float):
            return {
                "zone_id": f"ZONE-UNIFORM-{target_factor}",
                "is_scorable": True,
                "status": "COMPLETE",
                "normalized": {
                    "R": target_factor,
                    "D": 1.0 - target_factor,  # so factor = 1 - (1 - f) = f
                    "W": target_factor,
                    "E": 1.0 - target_factor,
                    "H": target_factor,
                },
                "flags": [],
            }

        # Test LOW (< 25.0)
        low_res = compute_flood_risk(make_uniform_zone(0.24))
        assert low_res["score"] == 24.0
        assert low_res["severity"] == "LOW"

        # Test MEDIUM boundary (25.0)
        med_res = compute_flood_risk(make_uniform_zone(0.25))
        assert med_res["score"] == 25.0
        assert med_res["severity"] == "MEDIUM"

        # Test HIGH boundary (50.0)
        high_res = compute_flood_risk(make_uniform_zone(0.50))
        assert high_res["score"] == 50.0
        assert high_res["severity"] == "HIGH"
        assert high_res["is_hotspot"] is True

        # Test CRITICAL boundary (75.0)
        crit_res = compute_flood_risk(make_uniform_zone(0.75))
        assert crit_res["score"] == 75.0
        assert crit_res["severity"] == "CRITICAL"

    def test_missing_optional_weights_dynamic_rescaling(self):
        """When optional fields are missing, available weights are dynamically rescaled."""
        # Zone with only rainfall (0.30) and drainage (0.25)
        # norm(R) = 1.0 (150 mm), norm(D) = 0.0 (0 cms -> 1 - 0 = 1.0 factor)
        # Total available weights = 0.30 + 0.25 = 0.55
        # Weighted score = (0.30 * 1.0 + 0.25 * 1.0) / 0.55 * 100 = 100.0
        raw = {
            "zone_id": "ZONE-ONLY-REQUIRED",
            "rainfall": 150.0,
            "drainage": 0.0,
        }
        prep = prepare_zone_data(raw)
        res = compute_flood_risk(prep)
        assert res["score"] == 100.0
        assert res["severity"] == "CRITICAL"
        assert "R" in res["breakdown"]
        assert "D" in res["breakdown"]
        assert "W" not in res["breakdown"]

    def test_unscorable_insufficient_zone_returns_none_score(self):
        raw = {
            "zone_id": "ZONE-INSUFFICIENT",
            "rainfall": None,
            "drainage": 40.0,
        }
        prep = prepare_zone_data(raw)
        res = compute_flood_risk(prep)
        assert res["score"] is None
        assert res["severity"] == "DATA_INSUFFICIENT"
        assert res["is_scorable"] is False

    def test_compute_all_flood_risks_batch(self):
        zones = [
            {"zone_id": "Z1", "rainfall": 20.0, "drainage": 80.0},
            {"zone_id": "Z2", "rainfall": 130.0, "drainage": 20.0},
        ]
        prepped = [prepare_zone_data(z) for z in zones]
        scored = compute_all_flood_risks(prepped)
        assert len(scored) == 2
        assert scored[0]["score"] < scored[1]["score"]
