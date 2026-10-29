"""Unit tests for CLIMAFORGE Algorithm 6: Critical Node Identification.

Verifies:
- Candidates filter: seed node excluded from candidates.
- Evaluation of the 6 features: Direct, Pop, Infra, Emerg, Downstream, DepCount.
- 0-1 max-scaling across candidate nodes.
- Criticality scoring using weights v (WEIGHTS_ALG6).
- Canonical Zone A benchmark: Drainage is the #1 Critical Node (Drainage > Road > Main Junction A...).
- Deterministic tie-breaking behavior.
"""

import pytest

from app.engine.alg4_graph import build_zone_a_graph
from app.engine.alg5_cascade import cascade
from app.engine.alg6_critical_nodes import identify_critical_nodes
from app.engine.constants import WEIGHTS_ALG6


class TestAlgorithm6CriticalNodes:
    """Tests for critical node ranking, feature scaling, and tie-breaking."""

    def test_seed_node_excluded(self):
        G = build_zone_a_graph()
        p_risks = {
            "Flood": 0.76,
            "Drainage": 0.69,
            "Road": 0.56,
            "Main Junction A": 0.45,
            "Emergency Access": 0.39,
            "Hospital": 0.25,
            "Population": 0.55,
        }
        res = identify_critical_nodes(G, p_risks)

        candidate_ids = [n["node_id"] for n in res["ranked_nodes"]]
        assert "Flood" not in candidate_ids
        assert len(candidate_ids) == 6

    def test_feature_scaling_and_weights_sum(self):
        G = build_zone_a_graph()
        p_risks = {
            "Flood": 0.76,
            "Drainage": 0.69,
            "Road": 0.56,
            "Main Junction A": 0.45,
            "Emergency Access": 0.39,
            "Hospital": 0.25,
            "Population": 0.55,
        }
        res = identify_critical_nodes(G, p_risks)

        # Check weights sum to 1.0
        assert sum(res["weights_applied"].values()) == pytest.approx(1.0, abs=1e-5)

        # Check each scaled feature is within [0.0, 1.0]
        for node in res["ranked_nodes"]:
            for fname, val in node["scaled_features"].items():
                assert 0.0 <= val <= 1.0001

            # Composite score is in [0.0, 1.0]
            assert 0.0 <= node["criticality_score"] <= 1.0

    def test_canonical_zone_a_benchmark_ranking(self):
        # From Report v2 Section 6.3 & Section 9:
        # Drainage > Road > Main Junction A > Emergency Access > Population > Hospital
        # Top node is Drainage
        G = build_zone_a_graph()
        casc = cascade(G, flood_risk=76.0)
        res = identify_critical_nodes(G, casc["node_risks"])

        assert res["critical_node"] == "Drainage"
        ranked_ids = [n["node_id"] for n in res["ranked_nodes"]]

        # Verify Drainage is rank 1
        assert ranked_ids[0] == "Drainage"
        # Verify Hospital is rank 6
        assert ranked_ids[-1] == "Hospital"

        # Check relative ordering of top nodes
        assert ranked_ids.index("Drainage") < ranked_ids.index("Road")
        assert ranked_ids.index("Road") < ranked_ids.index("Hospital")

    def test_downstream_impact_computation(self):
        # A node with no descendants has downstream_impact = 0.0
        G = build_zone_a_graph()
        casc = cascade(G, flood_risk=76.0)
        res = identify_critical_nodes(G, casc["node_risks"])

        # Hospital and Population have no outgoing edges in Zone A
        hosp_item = next(n for n in res["ranked_nodes"] if n["node_id"] == "Hospital")
        drainage_item = next(n for n in res["ranked_nodes"] if n["node_id"] == "Drainage")

        assert hosp_item["downstream_impact"] == 0.0
        assert drainage_item["downstream_impact"] > 0.0

    def test_tie_breaking_deterministic(self):
        G = build_zone_a_graph()
        # Artificial identical risks
        p_risks = {nid: 0.50 for nid in G.nodes}
        res1 = identify_critical_nodes(G, p_risks)
        res2 = identify_critical_nodes(G, p_risks)

        # Repeated runs must produce identical ordering
        assert [n["node_id"] for n in res1["ranked_nodes"]] == [n["node_id"] for n in res2["ranked_nodes"]]
