"""CLIMAFORGE Algorithm 12: Alternative Intervention Comparison.

Builds a side-by-side comparison table of the top-K feasible interventions
plus the "No action" baseline, ranked by InterventionScore from Algorithm 10.

Implements Section 6.5 (Algorithm 12) of the CLIMAFORGE Algorithm Design &
Implementation Report v2.

Table columns:
    intervention_id, action_name, impact_index, cascade_length,
    population_risk, infrastructure_risk, emergency_delay,
    population_saved, infrastructure_protected, resource_cost, score

All values are derived from the shared simulate() function, ensuring they are
consistent with Algorithm 10 and Algorithm 11 outputs.
"""

from typing import Any, Dict, List, Optional

import networkx as nx

from app.engine.alg5_cascade import simulate
from app.engine.alg11_what_if import compute_measures
from app.engine.constants import CASCADE_THRESHOLD_TAU, TOP_K_ALTERNATIVES


def _resource_cost_fraction(
    action: Dict[str, Any],
    zone_budget: Dict[str, int],
) -> float:
    """Normalised resource cost fraction matching Algorithm 10 definition.

    ResourceCost = Σ(used_t / available_t) / T
    where T = number of resource types with available_t > 0.
    """
    types_with_stock = {r: q for r, q in zone_budget.items() if q > 0}
    T = len(types_with_stock)
    if T == 0:
        return 0.0
    total = 0.0
    for resource, needed in action.get("required_resources", {}).items():
        available = types_with_stock.get(resource, 0)
        if available > 0:
            total += needed / available
    return round(total / T, 4)


def compare_alternatives(
    G: nx.DiGraph,
    flood_risk: float,
    ranked_feasible: List[Dict[str, Any]],
    zone_budget: Optional[Dict[str, int]] = None,
    catalogue: Optional[List[Dict[str, Any]]] = None,
    K: int = TOP_K_ALTERNATIVES,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Dict[str, Any]:
    """Build a comparison table for the top-K feasible interventions + no-action.

    Args:
        G: Consequence graph (not mutated).
        flood_risk: FloodRisk score (0–100).
        ranked_feasible: Ordered list of feasible interventions from Alg 10
            (each dict must have ``intervention_id``, ``action``, ``name``,
            ``required_resources``, ``score``, ``target_node``, and
            ``mitigation_m`` accessible via the original catalogue entry or
            stored inline).
        zone_budget: Granted resources for resource-cost calculation.
        catalogue: Full catalogue for looking up ``mitigation_m`` and
            ``target_node`` if not already present in ranked_feasible entries.
        K: Maximum number of alternatives to include (default TOP_K_ALTERNATIVES).
        tau: Cascade threshold.

    Returns:
        {
            "no_action_baseline": {intervention_id: "NO_ACTION", ...measures...},
            "rows": [{intervention_id, action_name, ...measures,
                       population_saved, infrastructure_protected,
                       resource_cost, score}],
            "top_k": K,
            "alternatives_count": int,
        }
    """
    if zone_budget is None:
        zone_budget = {}

    # Build lookup for catalogue entries if needed
    catalogue_by_id: Dict[str, Dict[str, Any]] = {}
    if catalogue:
        for entry in catalogue:
            catalogue_by_id[entry["intervention_id"]] = entry

    # --- No-action baseline ---
    baseline_sim = simulate(G, flood_risk=flood_risk, intervention=None, tau=tau)
    baseline_measures = compute_measures(baseline_sim, G)

    no_action_row: Dict[str, Any] = {
        "intervention_id": "NO_ACTION",
        "action_name": "No action (baseline)",
        "score": 0.0,
        "resource_cost": 0.0,
        **baseline_measures,
        "population_saved": 0.0,
        "infrastructure_protected": 0.0,
    }

    # --- Top-K feasible interventions ---
    top_k_feasible = ranked_feasible[:K]
    rows: List[Dict[str, Any]] = []

    for entry in top_k_feasible:
        iid = entry["intervention_id"]

        # Resolve full action details (mitigation_m, target_node)
        catalogue_entry = catalogue_by_id.get(iid, {})
        action = {**catalogue_entry, **entry}  # entry fields override catalogue defaults

        # Post-intervention simulation
        post_sim = simulate(G, flood_risk=flood_risk, intervention=action, tau=tau)
        post_measures = compute_measures(post_sim, G)

        # Population saved = absolute reduction in population_risk
        pop_saved = max(
            0.0,
            round(baseline_measures["population_risk"] - post_measures["population_risk"], 4),
        )
        # Infrastructure protected = absolute reduction in infrastructure_risk
        infra_protected = max(
            0.0,
            round(
                baseline_measures["infrastructure_risk"] - post_measures["infrastructure_risk"],
                4,
            ),
        )

        resource_cost = _resource_cost_fraction(action, zone_budget)

        rows.append(
            {
                "intervention_id": iid,
                "action_name": entry.get("name") or entry.get("action", iid),
                "score": entry.get("score", 0.0),
                "resource_cost": resource_cost,
                **post_measures,
                "population_saved": pop_saved,
                "infrastructure_protected": infra_protected,
            }
        )

    return {
        "no_action_baseline": no_action_row,
        "rows": rows,
        "top_k": K,
        "alternatives_count": len(rows),
    }
