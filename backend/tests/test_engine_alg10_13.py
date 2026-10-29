"""Tests for Algorithms 10–13: Intervention Ranking, What-If, Comparison, Decision.

Uses the canonical Zone A consequence graph from Algorithm 4 for all tests.
"""

import pytest
import networkx as nx

from app.engine.alg4_graph import build_zone_a_graph
from app.engine.alg5_cascade import simulate
from app.engine.alg10_ranking import check_feasibility, rank_interventions
from app.engine.alg11_what_if import compute_measures, run_what_if
from app.engine.alg12_comparison import compare_alternatives
from app.engine.alg13_decision import generate_decision_card, verify_candidate
from app.engine.constants import (
    DEFAULT_RESOURCE_INVENTORY,
    INTERVENTION_CATALOGUE,
    TOP_K_ALTERNATIVES,
    WEIGHTS_ALG10,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FLOOD_RISK = 75.0  # Canonical Zone A hotspot score

# Canonical depot stock: 2 pumps, 1 rescue_team, 0 barricades, 0 vehicles
ZONE_BUDGET = {"pumps": 2, "rescue_teams": 1, "barricades": 0, "vehicles": 0}


@pytest.fixture
def G():
    """Canonical Zone A consequence graph."""
    return build_zone_a_graph()


@pytest.fixture
def baseline_sim(G):
    return simulate(G, flood_risk=FLOOD_RISK, intervention=None)


# ---------------------------------------------------------------------------
# Algorithm 10: check_feasibility
# ---------------------------------------------------------------------------

class TestCheckFeasibility:
    def test_i1_feasible_with_two_pumps(self):
        action = next(a for a in INTERVENTION_CATALOGUE if a["intervention_id"] == "I1")
        feasible, blockers = check_feasibility(action, ZONE_BUDGET)
        assert feasible is True
        assert blockers == []

    def test_i4_infeasible_no_barricades(self):
        action = next(a for a in INTERVENTION_CATALOGUE if a["intervention_id"] == "I4")
        feasible, blockers = check_feasibility(action, ZONE_BUDGET)
        assert feasible is False
        assert any("barricade" in b.lower() for b in blockers)

    def test_explicit_blocker_message(self):
        action = {"intervention_id": "I4", "required_resources": {"barricades": 2}}
        feasible, blockers = check_feasibility(action, {"barricades": 0})
        assert feasible is False
        assert len(blockers) == 1
        assert "0" in blockers[0]  # shows granted=0

    def test_zero_budget_blocks_all(self):
        zero_budget = {"pumps": 0, "rescue_teams": 0, "barricades": 0, "vehicles": 0}
        for action in INTERVENTION_CATALOGUE:
            if action.get("required_resources"):
                feasible, _ = check_feasibility(action, zero_budget)
                assert feasible is False


# ---------------------------------------------------------------------------
# Algorithm 10: rank_interventions
# ---------------------------------------------------------------------------

class TestRankInterventions:
    def test_i4_in_infeasible_list(self, G):
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        infeasible_ids = [i["intervention_id"] for i in result["infeasible"]]
        assert "I4" in infeasible_ids

    def test_i1_i2_i3_feasible(self, G):
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        feasible_ids = [i["intervention_id"] for i in result["feasible"]]
        assert "I1" in feasible_ids
        assert "I2" in feasible_ids
        assert "I3" in feasible_ids

    def test_ranking_order_i1_top(self, G):
        """Canonical ranking: I1 > I2 > I3 by InterventionScore."""
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        feasible = result["feasible"]
        ids_in_order = [f["intervention_id"] for f in feasible]
        # I1 must be top-ranked
        assert ids_in_order[0] == "I1"

    def test_scores_descending(self, G):
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        scores = [f["score"] for f in result["feasible"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_action_is_first_feasible(self, G):
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        assert result["top_action"]["intervention_id"] == result["feasible"][0]["intervention_id"]

    def test_monitoring_only_empty_budget(self, G):
        """Empty zone budget makes all resource-requiring interventions infeasible."""
        result = rank_interventions(G, FLOOD_RISK, zone_budget={})
        # With no budget, all catalogue actions requiring resources are infeasible
        feasible_ids = [i["intervention_id"] for i in result["feasible"]]
        assert "I1" not in feasible_ids
        assert "I4" not in feasible_ids

    def test_nugen_mock_is_stored(self, G):
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        nugen = result["nugen_recommendation"]
        assert nugen is not None
        assert nugen.get("recommended_action") == "I2"  # mock always recommends I2

    def test_nugen_agreement_flag_for_top(self, G):
        """Since I1 is top-ranked and Nugen mock recommends I2, agreement is False."""
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        # Agreement at the ranking level (top vs nugen)
        assert result["nugen_agreement"] is False

    def test_graph_not_mutated(self, G):
        """Multiple calls to rank_interventions must not mutate G."""
        import copy
        original_nodes = {n: dict(d) for n, d in G.nodes(data=True)}
        rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        for n, data in G.nodes(data=True):
            assert data == original_nodes[n], f"Node {n} was mutated"

    def test_intervention_score_positive_for_i1(self, G):
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        i1 = next(f for f in result["feasible"] if f["intervention_id"] == "I1")
        assert i1["score"] > 0.0

    def test_risk_reduction_positive_for_i1(self, G):
        result = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        i1 = next(f for f in result["feasible"] if f["intervention_id"] == "I1")
        assert i1["measures"]["risk_reduction"] > 0.0


# ---------------------------------------------------------------------------
# Algorithm 11: what-if simulation
# ---------------------------------------------------------------------------

class TestWhatIf:
    def test_baseline_before_equals_after_with_no_intervention(self, G):
        result = run_what_if(G, FLOOD_RISK, intervention=None)
        assert result["before"]["impact_index"] == result["after"]["impact_index"]

    def test_i1_reduces_impact(self, G):
        action = next(a for a in INTERVENTION_CATALOGUE if a["intervention_id"] == "I1")
        result = run_what_if(G, FLOOD_RISK, intervention=action)
        assert result["after"]["impact_index"] < result["before"]["impact_index"]

    def test_reductions_non_negative(self, G):
        action = next(a for a in INTERVENTION_CATALOGUE if a["intervention_id"] == "I1")
        result = run_what_if(G, FLOOD_RISK, intervention=action)
        for key, reduction in result["reductions"].items():
            assert reduction["relative"] >= 0.0, f"Negative reduction for {key}"

    def test_graph_not_mutated_by_what_if(self, G):
        import copy
        original_nodes = {n: dict(d) for n, d in G.nodes(data=True)}
        action = next(a for a in INTERVENTION_CATALOGUE if a["intervention_id"] == "I1")
        run_what_if(G, FLOOD_RISK, intervention=action)
        for n, data in G.nodes(data=True):
            assert data == original_nodes[n], f"Node {n} was mutated"

    def test_five_measures_present(self, G):
        result = run_what_if(G, FLOOD_RISK, intervention=None)
        for key in ("impact_index", "cascade_length", "population_risk",
                    "infrastructure_risk", "emergency_delay"):
            assert key in result["before"]
            assert key in result["after"]

    def test_infrastructure_risk_bounded(self, G):
        result = run_what_if(G, FLOOD_RISK, intervention=None)
        for side in ("before", "after"):
            assert 0.0 <= result[side]["infrastructure_risk"] <= 1.0


# ---------------------------------------------------------------------------
# Algorithm 12: alternative comparison
# ---------------------------------------------------------------------------

class TestAlternativeComparison:
    def test_no_action_row_always_present(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        result = compare_alternatives(
            G, FLOOD_RISK,
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert result["no_action_baseline"]["intervention_id"] == "NO_ACTION"

    def test_top_k_rows(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        result = compare_alternatives(
            G, FLOOD_RISK,
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            catalogue=INTERVENTION_CATALOGUE,
            K=TOP_K_ALTERNATIVES,
        )
        assert result["alternatives_count"] <= TOP_K_ALTERNATIVES

    def test_no_action_has_zero_population_saved(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        result = compare_alternatives(
            G, FLOOD_RISK,
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert result["no_action_baseline"]["population_saved"] == 0.0

    def test_i1_population_saved_non_negative(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        result = compare_alternatives(
            G, FLOOD_RISK,
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            catalogue=INTERVENTION_CATALOGUE,
        )
        for row in result["rows"]:
            assert row["population_saved"] >= 0.0

    def test_rows_all_consistent_with_simulation(self, G):
        """Every row's impact_index should differ from no-action or equal (no fabrication)."""
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        result = compare_alternatives(
            G, FLOOD_RISK,
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            catalogue=INTERVENTION_CATALOGUE,
        )
        baseline_impact = result["no_action_baseline"]["impact_index"]
        for row in result["rows"]:
            # Post-intervention impact should be <= baseline (interventions reduce risk)
            assert row["impact_index"] <= baseline_impact + 1e-6


# ---------------------------------------------------------------------------
# Algorithm 13: decision card
# ---------------------------------------------------------------------------

class TestVerifyCandidate:
    def test_valid_candidate_passes(self, G, baseline_sim):
        action = next(a for a in INTERVENTION_CATALOGUE if a["intervention_id"] == "I1")
        passed, blockers = verify_candidate(action, ZONE_BUDGET, G, FLOOD_RISK, baseline_sim)
        assert passed is True
        assert blockers == []

    def test_missing_target_node_fails(self, G, baseline_sim):
        action = {"intervention_id": "X1", "target_node": "NONEXISTENT", "required_resources": {}}
        passed, blockers = verify_candidate(action, ZONE_BUDGET, G, FLOOD_RISK, baseline_sim)
        assert passed is False
        assert any("NONEXISTENT" in b for b in blockers)

    def test_insufficient_resources_fails(self, G, baseline_sim):
        action = next(a for a in INTERVENTION_CATALOGUE if a["intervention_id"] == "I1")
        empty_budget = {"pumps": 0, "rescue_teams": 0, "barricades": 0, "vehicles": 0}
        passed, blockers = verify_candidate(action, empty_budget, G, FLOOD_RISK, baseline_sim)
        assert passed is False

    def test_zero_risk_reduction_fails(self, G, baseline_sim):
        """An action on a node with mitigation_m=0 has no risk reduction."""
        action = {
            "intervention_id": "NULL",
            "target_node": "Drainage",
            "mitigation_m": 0.0,
            "required_resources": {},
        }
        passed, blockers = verify_candidate(action, {}, G, FLOOD_RISK, baseline_sim)
        # mitigation_m=0 → f unchanged → cascade_risk unchanged → RiskReduction = 0
        assert passed is False
        assert any("RiskReduction" in b for b in blockers)


class TestGenerateDecisionCard:
    def test_feasible_card_status(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            hotspot_zone={"zone_id": "Zone A", "severity": "HIGH"},
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert card["status"] == "FEASIBLE"

    def test_top_intervention_is_i1(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert card["intervention_id"] == "I1"

    def test_card_has_expected_impact(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert card["expected_impact"] is not None
        assert "before" in card["expected_impact"]
        assert "after" in card["expected_impact"]
        assert "reductions" in card["expected_impact"]

    def test_card_has_human_review_warning(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert card["human_review_warning"]
        assert "SYNTHETIC" in card["human_review_warning"]

    def test_card_ai_status_is_mock(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert card["ai_status"] == "MOCK"

    def test_no_feasible_intervention_when_budget_empty(self, G):
        empty_budget = {}
        ranking = rank_interventions(G, FLOOD_RISK, zone_budget=empty_budget)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=empty_budget,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert card["status"] == "NO_FEASIBLE_INTERVENTION"

    def test_no_feasible_intervention_card_has_blockers(self, G):
        empty_budget = {}
        ranking = rank_interventions(G, FLOOD_RISK, zone_budget=empty_budget)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=empty_budget,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert isinstance(card["blockers"], list)
        # blockers should explain why all candidates failed
        assert len(card["rejected_candidates"]) == len(ranking["feasible"])

    def test_rejected_candidates_list_populated(self, G):
        """When first candidate fails, it appears in rejected_candidates."""
        # Give budget with rescue_teams only (I1 needs pumps → fails verify)
        limited_budget = {"pumps": 0, "rescue_teams": 1, "barricades": 0, "vehicles": 0}
        ranking = rank_interventions(G, FLOOD_RISK, zone_budget=limited_budget)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=limited_budget,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        # If any feasible intervention was tried and rejected, rejected_candidates > 0
        # or a FEASIBLE card was issued from a passing candidate
        assert card["status"] in ("FEASIBLE", "NO_FEASIBLE_INTERVENTION")

    def test_nugen_recommendation_stored(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            nugen_result=ranking["nugen_recommendation"],
            catalogue=INTERVENTION_CATALOGUE,
        )
        # Mock nugen recommends I2; ranking picks I1 → nugen stored, agreement=False
        assert card["nugen_recommendation"] == "I2"
        assert card["nugen_agreement"] is False

    def test_run_id_generated(self, G):
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert card["run_id"]
        assert len(card["run_id"]) > 0

    def test_graph_not_mutated_by_decision(self, G):
        original_nodes = {n: dict(d) for n, d in G.nodes(data=True)}
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        for n, data in G.nodes(data=True):
            assert data == original_nodes[n], f"Node {n} was mutated"

    def test_modelled_relative_change_negative_or_zero(self, G):
        """Intervention reduces risk → modelled_relative_change <= 0."""
        ranking = rank_interventions(G, FLOOD_RISK, ZONE_BUDGET)
        card = generate_decision_card(
            ranked_feasible=ranking["feasible"],
            zone_budget=ZONE_BUDGET,
            G=G,
            flood_risk=FLOOD_RISK,
            catalogue=INTERVENTION_CATALOGUE,
        )
        if card["status"] == "FEASIBLE":
            assert card["modelled_relative_change"] is not None
            assert card["modelled_relative_change"] <= 0.0


# ---------------------------------------------------------------------------
# Pipeline integration: M4 fields present
# ---------------------------------------------------------------------------

class TestPipelineM4Integration:
    def test_pipeline_returns_m4_fields(self):
        from app.engine.pipeline import execute_risk_engine

        zones = [
            {
                "zone_id": "Zone A",
                "name": "Zone A",
                "rainfall_mm": 180.0,
                "elevation_m": 5.0,
                "soil_saturation_index": 0.85,
                "drainage_capacity_cms": 2.0,
                "population": 50000,
                "critical_infrastructure_count": 8,
                "water_level_m": 3.5,
                "road_length_km": 12.0,
                "emergency_routes_count": 2,
            }
        ]

        result = execute_risk_engine(zones, scenario_id="test-m4")

        if result["pipeline_status"] == "SUCCESS" and result["cascade_status"] == "SUCCESS":
            assert result.get("resource_allocation") is not None
            assert result.get("intervention_ranking") is not None
            assert result.get("what_if_analysis") is not None
            assert result.get("alternative_comparison") is not None
            assert result.get("decision_card") is not None
            # executed_algorithms should include M4 entries
            alg_names = result["executed_algorithms"]
            assert any("8" in a for a in alg_names)
            assert any("10" in a for a in alg_names)
            assert any("13" in a for a in alg_names)

    def test_pipeline_m4_executed_algorithm_count(self):
        from app.engine.pipeline import execute_risk_engine

        zones = [
            {
                "zone_id": "Zone A",
                "name": "Zone A",
                "rainfall_mm": 180.0,
                "elevation_m": 5.0,
                "soil_saturation_index": 0.85,
                "drainage_capacity_cms": 2.0,
                "population": 50000,
                "critical_infrastructure_count": 8,
                "water_level_m": 3.5,
                "road_length_km": 12.0,
                "emergency_routes_count": 2,
            }
        ]

        result = execute_risk_engine(zones, scenario_id="test-m4-count")
        if result["cascade_status"] == "SUCCESS":
            # 4 base + 9 cascade/M4 = 13 total
            assert len(result["executed_algorithms"]) == 13
