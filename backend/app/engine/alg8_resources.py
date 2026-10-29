"""CLIMAFORGE Algorithm 8: Resource Priority Optimization.

Computes a PriorityScore for each hotspot zone and greedily allocates depot
resources in descending priority order.

Implements Section 6.4 (Algorithm 8) and Section 12 of the CLIMAFORGE
Algorithm Design & Implementation Report v2.

Formula:
    PriorityScore(z) = max(ε, FloodRisk/100)
                       * max(ε, CascadeRisk)
                       * max(ε, Criticality)
                       * max(ε, ImpactScore)
                       * max(ε, EmergImportance)

    ε = PRIORITY_EPSILON = 0.01  (floor to keep all factors non-zero)

Allocation:
  1. Sort zones descending by PriorityScore.
  2. For each zone, zone demand = max required units per resource type over all
     catalogue actions applicable to that zone.
  3. Grant min(demand, remaining) per resource type; subtract from depot.
  4. If a required resource type has 0 remaining → record UNAVAILABLE; continue.
"""

from typing import Any, Dict, List, Optional

from app.engine.constants import (
    DEFAULT_EMERGENCY_IMPORTANCE,
    DEFAULT_RESOURCE_INVENTORY,
    INTERVENTION_CATALOGUE,
    PRIORITY_EPSILON,
)


def compute_zone_priority_score(
    flood_risk: float,
    cascade_risk: float,
    top_criticality: float,
    impact_score: float,
    emergency_importance: float,
    epsilon: float = PRIORITY_EPSILON,
) -> float:
    """Compute PriorityScore for a single zone using the product formula.

    Each factor is floored to epsilon so that zones with some missing data
    still receive a small but non-zero score rather than zero.

    Args:
        flood_risk: AlgorithmScore from Alg 1, scale 0–100. Divided by 100.
        cascade_risk: CascadeRisk from Alg 5, scale 0–1.
        top_criticality: Highest criticality_score from Alg 6, scale 0–1.
        impact_score: ImpactScore from Alg 3, scale 0–1 (or raw if needed).
        emergency_importance: Emergency importance weight for the zone, 0–1.
        epsilon: Floor applied to every factor (default 0.01).

    Returns:
        PriorityScore ≥ epsilon^5 (always positive).
    """
    factors = [
        max(epsilon, float(flood_risk) / 100.0),
        max(epsilon, float(cascade_risk)),
        max(epsilon, float(top_criticality)),
        max(epsilon, float(impact_score)),
        max(epsilon, float(emergency_importance)),
    ]
    score = 1.0
    for f in factors:
        score *= f
    return score


def _zone_demand(catalogue: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compute maximum required units per resource type over all catalogue actions.

    This represents the highest single-action demand the zone could need for
    any individual intervention.  Greedy allocation uses this as the ask.
    """
    demand: Dict[str, int] = {}
    for action in catalogue:
        for resource, qty in action.get("required_resources", {}).items():
            demand[resource] = max(demand.get(resource, 0), int(qty))
    return demand


def allocate_resources(
    hotspot_zones: List[Dict[str, Any]],
    resource_inventory: Optional[Dict[str, int]] = None,
    catalogue: Optional[List[Dict[str, Any]]] = None,
    cascade_results_by_zone: Optional[Dict[str, Dict[str, Any]]] = None,
    critical_node_results_by_zone: Optional[Dict[str, Dict[str, Any]]] = None,
    emergency_importance_by_zone: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Greedily allocate depot resources to hotspot zones by priority.

    Args:
        hotspot_zones: List of hotspot zone dicts from Alg 2 (must include
            ``zone_id`` and ``score`` fields).
        resource_inventory: Depot stock {resource_type: count}.  Defaults to
            DEFAULT_RESOURCE_INVENTORY if None.
        catalogue: Intervention catalogue.  Defaults to INTERVENTION_CATALOGUE.
        cascade_results_by_zone: {zone_id: cascade() result dict} for CascadeRisk.
        critical_node_results_by_zone: {zone_id: identify_critical_nodes() dict}.
        emergency_importance_by_zone: {zone_id: float 0–1}.

    Returns:
        {
            "priority_scores": {zone_id: float},
            "zone_allocation_order": [zone_id, ...],   # descending priority
            "zone_budgets": {zone_id: {resource: granted}},
            "unmet_demand": [{zone_id, resource_type, needed, granted}],
            "remaining_inventory": {resource: count},
            "status": "SUCCESS" | "NO_HOTSPOTS",
        }
    """
    if resource_inventory is None:
        resource_inventory = DEFAULT_RESOURCE_INVENTORY
    if catalogue is None:
        catalogue = INTERVENTION_CATALOGUE
    if cascade_results_by_zone is None:
        cascade_results_by_zone = {}
    if critical_node_results_by_zone is None:
        critical_node_results_by_zone = {}
    if emergency_importance_by_zone is None:
        emergency_importance_by_zone = {}

    if not hotspot_zones:
        return {
            "priority_scores": {},
            "zone_allocation_order": [],
            "zone_budgets": {},
            "unmet_demand": [],
            "remaining_inventory": dict(resource_inventory),
            "status": "NO_HOTSPOTS",
        }

    # --- 1. Compute PriorityScore per zone ---
    priority_scores: Dict[str, float] = {}
    for zone in hotspot_zones:
        zone_id = zone["zone_id"]
        flood_risk = float(zone.get("score") or 0.0)

        # CascadeRisk from Alg 5 result for this zone
        cascade_res = cascade_results_by_zone.get(zone_id, {})
        cascade_risk = float(cascade_res.get("cascade_risk", 0.0))

        # Top criticality from Alg 6 result for this zone
        crit_res = critical_node_results_by_zone.get(zone_id, {})
        critical_nodes_list = crit_res.get("critical_nodes", [])
        top_criticality = 0.0
        if critical_nodes_list:
            top_criticality = float(
                max(n.get("criticality_score", 0.0) for n in critical_nodes_list)
            )

        # ImpactScore from zone dict (Alg 3 stores it there)
        impact_score = float(zone.get("impact_score", 0.0))
        if impact_score == 0.0:
            # Fallback: use normalized flood score as proxy
            impact_score = min(1.0, flood_risk / 100.0)

        emergency_importance = float(
            emergency_importance_by_zone.get(zone_id, DEFAULT_EMERGENCY_IMPORTANCE)
        )

        priority_scores[zone_id] = compute_zone_priority_score(
            flood_risk=flood_risk,
            cascade_risk=cascade_risk,
            top_criticality=top_criticality,
            impact_score=impact_score,
            emergency_importance=emergency_importance,
        )

    # --- 2. Sort zones descending by priority; break ties by zone_id ---
    sorted_zones = sorted(
        hotspot_zones,
        key=lambda z: (-priority_scores[z["zone_id"]], z["zone_id"]),
    )
    zone_allocation_order = [z["zone_id"] for z in sorted_zones]

    # --- 3. Greedy allocation ---
    remaining = dict(resource_inventory)
    zone_budgets: Dict[str, Dict[str, int]] = {}
    unmet_demand: List[Dict[str, Any]] = []

    # Compute per-zone demand from catalogue (max over all actions)
    zone_demand = _zone_demand(catalogue)

    for zone in sorted_zones:
        zone_id = zone["zone_id"]
        granted: Dict[str, int] = {}

        for resource, needed in zone_demand.items():
            available = remaining.get(resource, 0)
            given = min(needed, available)
            granted[resource] = given
            remaining[resource] = available - given

            if given < needed:
                unmet_demand.append(
                    {
                        "zone_id": zone_id,
                        "resource_type": resource,
                        "needed": needed,
                        "granted": given,
                        "status": "UNAVAILABLE" if available == 0 else "PARTIAL",
                    }
                )

        zone_budgets[zone_id] = granted

    return {
        "priority_scores": priority_scores,
        "zone_allocation_order": zone_allocation_order,
        "zone_budgets": zone_budgets,
        "unmet_demand": unmet_demand,
        "remaining_inventory": remaining,
        "status": "SUCCESS",
    }
