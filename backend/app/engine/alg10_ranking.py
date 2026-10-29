"""CLIMAFORGE Algorithm 10: Intervention Priority Ranking.

Ranks feasible catalogue interventions by a weighted multi-criteria score and
separates infeasible interventions (those whose resource requirements exceed
the allocated zone budget).

Implements Section 6.4 (Algorithm 10) of the CLIMAFORGE Algorithm Design &
Implementation Report v2.

Score formula:
    InterventionScore = a1*RiskReduction
                       + a2*CascadeReduction
                       + a3*PopulationProtection
                       + a4*EmergencyProtection
                       - a5*ResourceCost

Weights (WEIGHTS_ALG10):
    a1=0.30, a2=0.25, a3=0.20, a4=0.15, a5=0.10

Division-by-zero guards:
    If baseline CascadeLength = 0      → CascadeReduction = 0
    If baseline pPop = 0               → PopulationProtection = 0
    If baseline pEmerg = 0             → EmergencyProtection = 0
    If no resource types available > 0 → ResourceCost = 0
"""

from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from app.engine.alg5_cascade import simulate
from app.engine.constants import (
    CASCADE_THRESHOLD_TAU,
    INTERVENTION_CATALOGUE,
    WEIGHTS_ALG10,
)


# ---------------------------------------------------------------------------
# Feasibility check
# ---------------------------------------------------------------------------


def check_feasibility(
    action: Dict[str, Any],
    zone_budget: Dict[str, int],
) -> Tuple[bool, List[str]]:
    """Check whether a catalogue action can be funded from the zone budget.

    An action is feasible if every resource type it requires has sufficient
    granted units in ``zone_budget``.

    Args:
        action: A single catalogue entry with ``required_resources`` dict.
        zone_budget: {resource_type: granted_units} from Alg 8.

    Returns:
        (is_feasible, [blocker_reason_strings])
    """
    blockers: List[str] = []
    for resource, needed in action.get("required_resources", {}).items():
        granted = zone_budget.get(resource, 0)
        if granted < needed:
            blockers.append(
                f"Insufficient {resource}: need {needed}, budget has {granted}"
            )
    return (len(blockers) == 0, blockers)


# ---------------------------------------------------------------------------
# Intervention scoring
# ---------------------------------------------------------------------------


def compute_intervention_score(
    G: nx.DiGraph,
    flood_risk: float,
    action: Dict[str, Any],
    baseline_sim: Dict[str, Any],
    zone_budget: Dict[str, int],
    weights: Optional[Dict[str, float]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Tuple[float, Dict[str, float]]:
    """Compute the weighted intervention score for a single feasible action.

    Uses the shared simulate() from alg5_cascade to obtain post-intervention
    metrics without mutating the original graph G.

    Args:
        G: Consequence graph (not mutated).
        flood_risk: AlgorithmScore from Alg 1 (0–100).
        action: Catalogue entry to evaluate.
        baseline_sim: simulate(G, flood_risk, intervention=None) result.
        zone_budget: Granted resource budget for this zone.
        weights: Weight dict (defaults to WEIGHTS_ALG10).
        tau: Cascade threshold (default CASCADE_THRESHOLD_TAU).

    Returns:
        (score, measures_dict) where measures_dict contains all sub-components.
    """
    if weights is None:
        weights = WEIGHTS_ALG10

    # Post-intervention simulation (does not mutate G)
    post_sim = simulate(G, flood_risk=flood_risk, intervention=action, tau=tau)

    # --- CascadeRisk (= cascade_risk from simulate output) ---
    baseline_impact = float(baseline_sim.get("cascade_risk", 0.0))
    post_impact = float(post_sim.get("cascade_risk", 0.0))

    # RiskReduction
    if baseline_impact > 0:
        risk_reduction = (baseline_impact - post_impact) / baseline_impact
    else:
        risk_reduction = 0.0
    risk_reduction = max(0.0, risk_reduction)

    # --- CascadeReduction ---
    baseline_len = float(baseline_sim.get("cascade_length", 0))
    post_len = float(post_sim.get("cascade_length", 0))
    if baseline_len > 0:
        cascade_reduction = (baseline_len - post_len) / baseline_len
    else:
        cascade_reduction = 0.0
    cascade_reduction = max(0.0, cascade_reduction)

    # --- PopulationProtection ---
    p_pop_0 = float(baseline_sim.get("node_risks", {}).get("Population", 0.0))
    p_pop_i = float(post_sim.get("node_risks", {}).get("Population", 0.0))
    if p_pop_0 > 0:
        pop_protection = (p_pop_0 - p_pop_i) / p_pop_0
    else:
        pop_protection = 0.0
    pop_protection = max(0.0, pop_protection)

    # --- EmergencyProtection ---
    p_emerg_0 = float(baseline_sim.get("node_risks", {}).get("Emergency Access", 0.0))
    p_emerg_i = float(post_sim.get("node_risks", {}).get("Emergency Access", 0.0))
    if p_emerg_0 > 0:
        emerg_protection = (p_emerg_0 - p_emerg_i) / p_emerg_0
    else:
        emerg_protection = 0.0
    emerg_protection = max(0.0, emerg_protection)

    # --- ResourceCost ---
    # Normalised fraction of available resource types consumed
    types_with_stock = {
        r: qty
        for r, qty in zone_budget.items()
        if qty > 0
    }
    T = len(types_with_stock)
    if T > 0:
        total_fraction = 0.0
        for resource, needed in action.get("required_resources", {}).items():
            available = types_with_stock.get(resource, 0)
            if available > 0:
                total_fraction += needed / available
            # If not in types_with_stock (available=0), skip (infeasibility already caught)
        resource_cost = total_fraction / T
    else:
        resource_cost = 0.0
    resource_cost = max(0.0, resource_cost)

    score = (
        weights["RiskReduction"] * risk_reduction
        + weights["CascadeReduction"] * cascade_reduction
        + weights["PopulationProtection"] * pop_protection
        + weights["EmergencyProtection"] * emerg_protection
        - weights["ResourceCost"] * resource_cost
    )

    measures = {
        "risk_reduction": round(risk_reduction, 4),
        "cascade_reduction": round(cascade_reduction, 4),
        "population_protection": round(pop_protection, 4),
        "emergency_protection": round(emerg_protection, 4),
        "resource_cost": round(resource_cost, 4),
        "baseline_cascade_risk": round(baseline_impact, 4),
        "post_cascade_risk": round(post_impact, 4),
        "baseline_cascade_length": int(baseline_len),
        "post_cascade_length": int(post_len),
        "baseline_p_pop": round(p_pop_0, 4),
        "post_p_pop": round(p_pop_i, 4),
        "baseline_p_emerg": round(p_emerg_0, 4),
        "post_p_emerg": round(p_emerg_i, 4),
    }

    return round(score, 4), measures


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

# Mock Nugen recommendation (M4: standby/mock only — no live API)
_MOCK_NUGEN_RESPONSE: Dict[str, Any] = {
    "recommended_action": "I2",
    "priority": "HIGH",
    "reason": "Main Junction A is the choke point for emergency access.",
    "cascade_to_break": "Road -> Main Junction A",
    "expected_impact": "Emergency access disruption reduced.",
    "source": "MOCK",
}


def rank_interventions(
    G: nx.DiGraph,
    flood_risk: float,
    zone_budget: Dict[str, int],
    catalogue: Optional[List[Dict[str, Any]]] = None,
    nugen_recommendation: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Dict[str, Any]:
    """Rank all catalogue interventions for a zone, split by feasibility.

    Args:
        G: Consequence graph for this zone.
        flood_risk: FloodRisk score (0–100) for this zone.
        zone_budget: Granted resources {resource_type: count} from Alg 8.
        catalogue: Intervention catalogue (defaults to INTERVENTION_CATALOGUE).
        nugen_recommendation: Optional Nugen AI result; uses mock if None.
        weights: Scoring weights (defaults to WEIGHTS_ALG10).
        tau: Cascade threshold.

    Returns:
        {
            "feasible": [{intervention_id, action, score, measures,
                          required_resources, nugen_agreement}],
            "infeasible": [{intervention_id, action, required_resources, blockers}],
            "top_action": feasible[0] or None,
            "nugen_recommendation": nugen result dict,
            "nugen_agreement": bool | None,
            "baseline_simulation": baseline_sim dict,
        }
    """
    if catalogue is None:
        catalogue = INTERVENTION_CATALOGUE
    if weights is None:
        weights = WEIGHTS_ALG10

    # Use mock Nugen if no live recommendation provided
    nugen_rec = nugen_recommendation or _MOCK_NUGEN_RESPONSE
    nugen_action_id = nugen_rec.get("recommended_action")

    # Baseline (no intervention)
    baseline_sim = simulate(G, flood_risk=flood_risk, intervention=None, tau=tau)

    feasible: List[Dict[str, Any]] = []
    infeasible: List[Dict[str, Any]] = []

    for action in catalogue:
        intervention_id = action["intervention_id"]
        is_feasible, blockers = check_feasibility(action, zone_budget)

        if not is_feasible:
            infeasible.append(
                {
                    "intervention_id": intervention_id,
                    "action": action.get("action", ""),
                    "name": action.get("name", ""),
                    "required_resources": action.get("required_resources", {}),
                    "blockers": blockers,
                }
            )
        else:
            score, measures = compute_intervention_score(
                G=G,
                flood_risk=flood_risk,
                action=action,
                baseline_sim=baseline_sim,
                zone_budget=zone_budget,
                weights=weights,
                tau=tau,
            )
            nugen_agreement = (
                nugen_action_id == intervention_id if nugen_action_id else None
            )
            feasible.append(
                {
                    "intervention_id": intervention_id,
                    "action": action.get("action", ""),
                    "name": action.get("name", ""),
                    "target_node": action.get("target_node", ""),
                    "required_resources": action.get("required_resources", {}),
                    "score": score,
                    "measures": measures,
                    "nugen_agreement": nugen_agreement,
                    "cost_usd": action.get("cost_usd"),
                    "lead_time_minutes": action.get("lead_time_minutes"),
                }
            )

    # Sort feasible descending by score, break ties by intervention_id
    feasible.sort(key=lambda x: (-x["score"], x["intervention_id"]))

    top_action = feasible[0] if feasible else None

    # Determine whether Nugen agrees with the top-ranked action
    if top_action and nugen_action_id:
        nugen_agreement = nugen_action_id == top_action["intervention_id"]
    else:
        nugen_agreement = None

    return {
        "feasible": feasible,
        "infeasible": infeasible,
        "top_action": top_action,
        "nugen_recommendation": nugen_rec,
        "nugen_agreement": nugen_agreement,
        "baseline_simulation": baseline_sim,
    }
