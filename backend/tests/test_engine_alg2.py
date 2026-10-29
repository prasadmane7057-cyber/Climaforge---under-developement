"""Unit tests for Algorithm 2 — Flood Hotspot Detection."""

import pytest
from app.engine.alg2_hotspots import detect_hotspots


class TestAlgorithm2Hotspots:
    """Tests for hotspot qualification, ranking, and MONITORING_ONLY state."""

    def test_hotspot_threshold_qualification(self):
        """A zone qualifies as a hotspot if and only if score >= 50.0."""
        scored_zones = [
            {"zone_id": "Z1", "score": 49.9, "is_scorable": True},
            {"zone_id": "Z2", "score": 50.0, "is_scorable": True},
            {"zone_id": "Z3", "score": 75.5, "is_scorable": True},
        ]
        res = detect_hotspots(scored_zones, threshold=50.0)
        assert res["hotspot_count"] == 2
        assert res["is_monitoring_only"] is False
        assert res["status"] == "HOTSPOTS_DETECTED"
        # Ranked descending by score
        assert res["hotspots"][0]["zone_id"] == "Z3"
        assert res["hotspots"][1]["zone_id"] == "Z2"

    def test_no_hotspots_triggers_monitoring_only(self):
        """When no zone qualifies, returns empty list and MONITORING_ONLY."""
        scored_zones = [
            {"zone_id": "Z1", "score": 15.0, "is_scorable": True},
            {"zone_id": "Z2", "score": 38.5, "is_scorable": True},
            {"zone_id": "Z3", "score": 49.0, "is_scorable": True},
        ]
        res = detect_hotspots(scored_zones, threshold=50.0)
        assert res["hotspots"] == []
        assert res["hotspot_count"] == 0
        assert res["is_monitoring_only"] is True
        assert res["status"] == "MONITORING_ONLY"

    def test_unscorable_zones_excluded(self):
        scored_zones = [
            {"zone_id": "Z1", "score": None, "is_scorable": False},
            {"zone_id": "Z2", "score": 65.0, "is_scorable": True},
        ]
        res = detect_hotspots(scored_zones)
        assert res["hotspot_count"] == 1
        assert res["hotspots"][0]["zone_id"] == "Z2"
        assert len(res["ranked_zones"]) == 1

    def test_canonical_example_page_12(self):
        """Canonical example page 12: Assumed zones A (76.0), B (55.7), C (29.3)

        HOTSPOT_THRESHOLD = 50 -> hotspots A and B; C is not a hotspot.
        """
        zones = [
            {"zone_id": "Zone A", "score": 76.0, "is_scorable": True},
            {"zone_id": "Zone B", "score": 55.7, "is_scorable": True},
            {"zone_id": "Zone C", "score": 29.3, "is_scorable": True},
        ]
        res = detect_hotspots(zones, threshold=50.0)
        assert res["hotspot_count"] == 2
        hotspot_ids = [z["zone_id"] for z in res["hotspots"]]
        assert hotspot_ids == ["Zone A", "Zone B"]
