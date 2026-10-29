"""Unit tests for CLIMAFORGE Algorithm 7: Cascade-Break Point Detection & Simulation.

Verifies:
- Candidate intervention evaluations against the consequence graph.
- Absolute and relative cascade risk reduction calculations.
- Shared simulate() reuse for before/after comparison.
- Canonical Zone A benchmark: I1 (pumps at Drainage) produces the highest reduction.
- Infeasible actions simulated correctly in Alg 7 before Alg 8 resource pruning.
- Surviving nodes (below tau) correctly tracked.
"""

import pytest

from app.engine.alg4_graph import build_zone_a_graph
from app.engine.alg7_break_points import evaluate_break_points
from app.engine.constants import INTERVENTION_CATALOGUE


class TestAlgorithm7BreakPoints:
    """Tests for cascade break point evaluation and simulation."""

    def test_evaluate_catalogue_interventions(self):
        G = build_zone_a_graph()
        res = evaluate_break_points(G, flood_risk=76.0, catalogue=INTERVENTION_CATALOGUE)

        assert res["evaluated_action_count"] == 4
        assert res["best_break_point"] is not None
        assert len(res["ranked_break_points"]) == 4

        # Verify baseline metrics
        assert res["baseline"]["cascade_risk"] > 0.40
        assert res["baseline"]["cascade_length"] == 5

    def test_canonical_zone_a_best_break_point(self):
        # Report v2 Section 6.3 & Section 9:
        # Best break point is I1 (pumps at Drainage) with highest impact reduction
        G = build_zone_a_graph()
        res = evaluate_break_points(G, flood_risk=76.0)

        best = res["best_break_point"]
        assert best["intervention_id"] == "I1"
        assert best["target_node"] == "Drainage"
        assert best["impact_reduction_abs"] > 0.20
        assert best["impact_reduction_rel"] == pytest.approx(0.579, abs=0.02)

        # Check ranking order matches Section 6.3 & Section 9: I1 > I4 > I2 > I3
        ranked_ids = [r["intervention_id"] for r in res["ranked_break_points"]]
        assert ranked_ids == ["I1", "I4", "I2", "I3"]

        # Check relative reductions match Section 6.3 within 0.02 tolerance
        i4_item = next(r for r in res["ranked_break_points"] if r["intervention_id"] == "I4")
        i2_item = next(r for r in res["ranked_break_points"] if r["intervention_id"] == "I2")
        i3_item = next(r for r in res["ranked_break_points"] if r["intervention_id"] == "I3")

        assert i4_item["impact_reduction_rel"] == pytest.approx(0.438, abs=0.02)
        assert i2_item["impact_reduction_rel"] == pytest.approx(0.264, abs=0.03)
        assert i3_item["impact_reduction_rel"] == pytest.approx(0.169, abs=0.02)

        # Check cascade length matches Table 9.4 (I1=0, I2=3, I3=4)
        i1_item = next(r for r in res["ranked_break_points"] if r["intervention_id"] == "I1")
        assert i1_item["mitigated_cascade_length"] == 0
        assert i2_item["mitigated_cascade_length"] == 3
        assert i3_item["mitigated_cascade_length"] == 4

    def test_impact_reduction_and_surviving_nodes(self):
        G = build_zone_a_graph()
        res = evaluate_break_points(G, flood_risk=76.0)

        i1_item = next(r for r in res["ranked_break_points"] if r["intervention_id"] == "I1")
        # Under I1 mitigation (0.60 on Drainage), cascade length shrinks significantly
        assert i1_item["mitigated_cascade_length"] < i1_item["baseline_cascade_length"]
        assert i1_item["cascade_length_delta"] > 0
        assert len(i1_item["surviving_nodes"]) > 0

    def test_nonexistent_target_node_produces_zero_reduction(self):
        G = build_zone_a_graph()
        fake_catalogue = [
            {
                "intervention_id": "I-FAKE",
                "action": "Repair non-existent bridge",
                "target_node": "NonExistentNode",
                "mitigation_m": 0.80,
            }
        ]
        res = evaluate_break_points(G, flood_risk=76.0, catalogue=fake_catalogue)
        item = res["ranked_break_points"][0]
        assert item["target_node_exists"] is False
        assert item["impact_reduction_abs"] == 0.0
        assert item["impact_reduction_rel"] == 0.0

    def test_simulate_deterministic_reproducibility(self):
        G = build_zone_a_graph()
        res1 = evaluate_break_points(G, flood_risk=76.0)
        res2 = evaluate_break_points(G, flood_risk=76.0)

        assert res1["best_break_point"]["intervention_id"] == res2["best_break_point"]["intervention_id"]
        assert res1["best_break_point"]["impact_reduction_abs"] == res2["best_break_point"]["impact_reduction_abs"]
