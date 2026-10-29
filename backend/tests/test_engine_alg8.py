"""Tests for Algorithm 8: Resource Priority Optimization & Depot Allocation.

Canonical synthetic depot stock (DEFAULT_RESOURCE_INVENTORY):
    pumps=2, rescue_teams=1, barricades=0, vehicles=0

Canonical catalogue demand (max per resource over I1–I4):
    pumps=2 (I1), rescue_teams=1 (I2 & I3), barricades=2 (I4), vehicles=0
"""

import pytest

from app.engine.alg8_resources import allocate_resources, compute_zone_priority_score
from app.engine.constants import (
    DEFAULT_RESOURCE_INVENTORY,
    INTERVENTION_CATALOGUE,
    PRIORITY_EPSILON,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zone(zone_id: str, score: float = 75.0) -> dict:
    return {"zone_id": zone_id, "score": score}


def _cascade(cascade_risk: float = 0.4) -> dict:
    return {"cascade_risk": cascade_risk}


def _crit(top_score: float = 0.7) -> dict:
    return {"critical_nodes": [{"criticality_score": top_score}]}


# ---------------------------------------------------------------------------
# PriorityScore formula
# ---------------------------------------------------------------------------

class TestPriorityScore:
    def test_product_formula(self):
        """PriorityScore = product of max(ε, factor) for 5 factors."""
        score = compute_zone_priority_score(
            flood_risk=80.0,
            cascade_risk=0.45,
            top_criticality=0.70,
            impact_score=0.60,
            emergency_importance=0.80,
        )
        expected = (
            max(PRIORITY_EPSILON, 0.80)
            * max(PRIORITY_EPSILON, 0.45)
            * max(PRIORITY_EPSILON, 0.70)
            * max(PRIORITY_EPSILON, 0.60)
            * max(PRIORITY_EPSILON, 0.80)
        )
        assert abs(score - round(expected, 6)) < 1e-5

    def test_epsilon_floor(self):
        """All-zero inputs still produce a positive score (epsilon^5)."""
        score = compute_zone_priority_score(
            flood_risk=0.0,
            cascade_risk=0.0,
            top_criticality=0.0,
            impact_score=0.0,
            emergency_importance=0.0,
        )
        assert score >= (PRIORITY_EPSILON ** 5) - 1e-15
        assert score > 0.0

    def test_flood_risk_divided_by_100(self):
        """flood_risk is divided by 100 before applying epsilon floor."""
        score_50 = compute_zone_priority_score(
            flood_risk=50.0, cascade_risk=0.5, top_criticality=0.5,
            impact_score=0.5, emergency_importance=0.5,
        )
        score_100 = compute_zone_priority_score(
            flood_risk=100.0, cascade_risk=0.5, top_criticality=0.5,
            impact_score=0.5, emergency_importance=0.5,
        )
        assert score_100 > score_50


# ---------------------------------------------------------------------------
# Resource allocation
# ---------------------------------------------------------------------------

class TestAllocateResources:
    def test_no_hotspots_returns_no_hotspots_status(self):
        result = allocate_resources(hotspot_zones=[], resource_inventory=DEFAULT_RESOURCE_INVENTORY)
        assert result["status"] == "NO_HOTSPOTS"
        assert result["zone_budgets"] == {}
        assert result["remaining_inventory"] == dict(DEFAULT_RESOURCE_INVENTORY)

    def test_zone_a_receives_resources(self):
        """Zone A (single hotspot) should receive resources from the depot."""
        result = allocate_resources(
            hotspot_zones=[_zone("Zone A", score=75.0)],
            resource_inventory={"pumps": 2, "rescue_teams": 1, "barricades": 0, "vehicles": 0},
            catalogue=INTERVENTION_CATALOGUE,
            cascade_results_by_zone={"Zone A": _cascade(0.4)},
            critical_node_results_by_zone={"Zone A": _crit(0.7)},
        )
        assert result["status"] == "SUCCESS"
        budget = result["zone_budgets"]["Zone A"]
        # Zone A demand: pumps=2, rescue_teams=1, barricades=2, vehicles=0
        # Granted from depot: pumps=2 ✓, rescue_teams=1 ✓, barricades=0 (depot=0)
        assert budget["pumps"] == 2
        assert budget["rescue_teams"] == 1
        assert budget["barricades"] == 0

    def test_zero_inventory_all_unmet(self):
        """When depot is empty, all resource requests are unmet."""
        inventory = {"pumps": 0, "rescue_teams": 0, "barricades": 0, "vehicles": 0}
        result = allocate_resources(
            hotspot_zones=[_zone("Zone A", score=75.0)],
            resource_inventory=inventory,
            catalogue=INTERVENTION_CATALOGUE,
        )
        budget = result["zone_budgets"]["Zone A"]
        # All granted should be 0
        assert all(v == 0 for v in budget.values())
        unmet = result["unmet_demand"]
        # barricades demand=2 > 0 and rescue_teams demand=1 > 0
        unmet_resources = {u["resource_type"] for u in unmet}
        assert "pumps" in unmet_resources
        assert "rescue_teams" in unmet_resources

    def test_two_zones_priority_ordering(self):
        """Higher-scoring zone should appear first in allocation order."""
        # Zone B has higher flood score → higher priority → allocated first
        result = allocate_resources(
            hotspot_zones=[
                _zone("Zone A", score=60.0),
                _zone("Zone B", score=85.0),
            ],
            resource_inventory={"pumps": 2, "rescue_teams": 1, "barricades": 0, "vehicles": 0},
            catalogue=INTERVENTION_CATALOGUE,
            cascade_results_by_zone={
                "Zone A": _cascade(0.3),
                "Zone B": _cascade(0.5),
            },
            critical_node_results_by_zone={
                "Zone A": _crit(0.5),
                "Zone B": _crit(0.8),
            },
        )
        order = result["zone_allocation_order"]
        assert order[0] == "Zone B"
        assert order[1] == "Zone A"

    def test_first_zone_consumes_all_pumps(self):
        """First-priority zone takes all pumps; second zone gets none."""
        result = allocate_resources(
            hotspot_zones=[
                _zone("Zone A", score=60.0),
                _zone("Zone B", score=90.0),  # Zone B gets priority
            ],
            resource_inventory={"pumps": 2, "rescue_teams": 1, "barricades": 0, "vehicles": 0},
            catalogue=INTERVENTION_CATALOGUE,
            cascade_results_by_zone={
                "Zone A": _cascade(0.3),
                "Zone B": _cascade(0.6),
            },
            critical_node_results_by_zone={
                "Zone A": _crit(0.4),
                "Zone B": _crit(0.9),
            },
        )
        # Zone B is first; gets 2 pumps
        assert result["zone_budgets"]["Zone B"]["pumps"] == 2
        # Zone A is second; gets 0 pumps
        assert result["zone_budgets"]["Zone A"]["pumps"] == 0

    def test_remaining_inventory_tracked(self):
        """Remaining inventory decrements correctly after allocation."""
        result = allocate_resources(
            hotspot_zones=[_zone("Zone A", score=75.0)],
            resource_inventory={"pumps": 5, "rescue_teams": 3, "barricades": 0, "vehicles": 0},
            catalogue=INTERVENTION_CATALOGUE,
        )
        # Zone A demand: pumps=2, rescue_teams=1, barricades=2 (→0 granted)
        remaining = result["remaining_inventory"]
        assert remaining["pumps"] == 3     # 5 - 2
        assert remaining["rescue_teams"] == 2  # 3 - 1

    def test_priority_score_in_result(self):
        """Result includes priority_scores dict with a positive entry per zone."""
        result = allocate_resources(
            hotspot_zones=[_zone("Zone A", score=70.0)],
            resource_inventory=DEFAULT_RESOURCE_INVENTORY,
            catalogue=INTERVENTION_CATALOGUE,
        )
        assert "Zone A" in result["priority_scores"]
        assert result["priority_scores"]["Zone A"] > 0.0

    def test_deterministic_tie_breaking(self):
        """Zones with identical priority scores are broken alphabetically."""
        # Identical parameters → identical priority scores → alphabetical ordering
        result = allocate_resources(
            hotspot_zones=[
                _zone("Zone B", score=70.0),
                _zone("Zone A", score=70.0),
            ],
            resource_inventory={"pumps": 10, "rescue_teams": 10, "barricades": 10, "vehicles": 0},
            catalogue=INTERVENTION_CATALOGUE,
        )
        order = result["zone_allocation_order"]
        # Lower alphabetical zone comes first when scores are equal
        assert order[0] == "Zone A"
        assert order[1] == "Zone B"
