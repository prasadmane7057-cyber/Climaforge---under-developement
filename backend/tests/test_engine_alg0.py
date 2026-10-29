"""Unit tests for Algorithm 0 — System Input & Data Preparation."""

import math
import pytest
from app.engine.alg0_data_prep import clamp, normalize, prepare_all_zones, prepare_zone_data
from app.engine.constants import REF_RANGES


class TestAlgorithm0Normalization:
    """Tests for fixed reference range normalization and clamping."""

    def test_normalize_lower_and_upper_boundaries(self):
        # Rainfall range: (0.0, 150.0)
        lo, hi = REF_RANGES["rainfall"]
        assert normalize(lo, lo, hi) == 0.0
        assert normalize(hi, lo, hi) == 1.0
        assert normalize(75.0, lo, hi) == 0.5

    def test_normalize_clamping_out_of_bounds(self):
        lo, hi = REF_RANGES["drainage"]  # (0.0, 100.0)
        # Below lo
        assert normalize(-25.0, lo, hi) == 0.0
        # Above hi
        assert normalize(150.0, lo, hi) == 1.0

    def test_normalize_zero_range(self):
        assert normalize(10.0, 5.0, 5.0) == 0.0

    def test_clamp_non_finite_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            clamp(float("nan"), 0.0, 1.0)
        with pytest.raises(ValueError, match="finite"):
            clamp(float("inf"), 0.0, 1.0)


class TestAlgorithm0ZonePreparation:
    """Tests for zone telemetry validation, required fields, and flagging."""

    def test_valid_complete_zone(self):
        raw = {
            "zone_id": "ZONE-VALID-01",
            "name": "Validation District",
            "rainfall": 75.0,
            "drainage": 50.0,
            "elevation": 20.0,
            "water_level": 1.5,
            "history": 2.5,
            "population": 12500,
            "critical_infra": 3,
            "road_length": 5.0,
            "emergency_routes": 2,
        }
        res = prepare_zone_data(raw)
        assert res["status"] == "COMPLETE"
        assert res["is_scorable"] is True
        assert res["normalized"]["R"] == 0.5
        assert res["normalized"]["D"] == 0.5
        assert res["normalized"]["E"] == 0.5
        assert res["normalized"]["W"] == 0.5
        assert res["normalized"]["H"] == 0.5
        assert res["raw_exposure"]["P"] == 12500
        assert res["normalized_exposure"]["P"] == 0.5

    def test_missing_required_rainfall_produces_data_insufficient(self):
        raw = {
            "zone_id": "ZONE-NO-RAIN",
            "name": "No Rain Zone",
            "drainage": 45.0,
        }
        res = prepare_zone_data(raw)
        assert res["status"] == "DATA_INSUFFICIENT"
        assert res["is_scorable"] is False
        assert "missing_required_rainfall" in res["flags"]
        assert res["normalized"] == {}

    def test_missing_required_drainage_produces_data_insufficient(self):
        raw = {
            "zone_id": "ZONE-NO-DRAIN",
            "name": "No Drain Zone",
            "rainfall": 90.0,
        }
        res = prepare_zone_data(raw)
        assert res["status"] == "DATA_INSUFFICIENT"
        assert res["is_scorable"] is False
        assert "missing_required_drainage" in res["flags"]

    def test_negative_values_rejected(self):
        raw = {
            "zone_id": "ZONE-NEG-VAL",
            "rainfall": -10.0,
            "drainage": 50.0,
        }
        res = prepare_zone_data(raw)
        assert res["status"] == "DATA_INSUFFICIENT"
        assert res["is_scorable"] is False
        assert "rainfall_negative_rejected" in res["flags"]

    def test_missing_optional_fields_flagged_with_partial_status(self):
        raw = {
            "zone_id": "ZONE-OPT-MISSING",
            "name": "Optional Missing Zone",
            "rainfall": 80.0,
            "drainage": 40.0,
            # elevation, water_level, history are all omitted
        }
        res = prepare_zone_data(raw)
        assert res["status"] == "PARTIAL_OPTIONAL_MISSING"
        assert res["is_scorable"] is True
        assert "missing_optional_elevation" in res["flags"]
        assert "missing_optional_water_level" in res["flags"]
        assert "missing_optional_history" in res["flags"]
        assert res["normalized"]["R"] is not None
        assert res["normalized"]["D"] is not None
        assert res["normalized"]["E"] is None
        assert res["normalized"]["W"] is None
        assert res["normalized"]["H"] is None

    def test_soil_saturation_proxy_maps_to_history(self):
        raw = {
            "zone_id": "ZONE-SAT",
            "rainfall": 60.0,
            "drainage": 30.0,
            "soil_saturation_index": 0.80,  # 0.80 * 5.0 = 4.0
        }
        res = prepare_zone_data(raw)
        assert res["normalized"]["H"] == 0.80

    def test_no_undocumented_nominal_exposure_fallbacks(self):
        # Road length and emergency routes must NOT silently default to 6.0 and 2.0
        raw = {
            "zone_id": "ZONE-EXPOSURE-TEST",
            "rainfall": 50.0,
            "drainage": 50.0,
            # road_length and emergency_routes omitted
        }
        res = prepare_zone_data(raw)
        assert res["raw_exposure"]["Rd"] is None
        assert res["raw_exposure"]["Em"] is None
        assert "missing_exposure_road_length" in res["flags"]
        assert "missing_exposure_emergency_routes" in res["flags"]

    def test_prepare_all_zones_batch(self):
        zones = [
            {"zone_id": "Z1", "rainfall": 50.0, "drainage": 50.0},
            {"zone_id": "Z2", "rainfall": 100.0, "drainage": 20.0},
        ]
        results = prepare_all_zones(zones)
        assert len(results) == 2
        assert results[0]["zone_id"] == "Z1"
        assert results[1]["zone_id"] == "Z2"
