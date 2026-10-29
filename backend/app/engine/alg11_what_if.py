"""CLIMAFORGE Algorithm 11: Counterfactual / What-If Simulation.

Runs paired simulations (baseline and post-intervention) using the shared
simulate() function from alg5_cascade.py, then computes before/after measures
and percentage reductions.

Implements Section 6.5 (Algorithm 11) of the CLIMAFORGE Algorithm Design &
Implementation Report v2.

Measures extracted from each simulation result:
    impact_index        — cascade_risk (consequence-weighted probability)
    cascade_length      — number of failing non-seed nodes
    population_risk     — p["Population"] (noisy-OR propagated probability)
    infrastructure_risk — Σ(p_v * infra_v) / Σ(infra_v) for non-seed nodes
    emergency_delay     — p["Emergency Access"] (proxy; dimensionless 0–1)

The simulate() function copies the graph internally, so G is never mutated.
"""

from typing import Any, Dict, List, Optional

import networkx as nx

from app.engine.alg5_cascade import simulate
from app.engine.constants import CASCADE_THRESHOLD_TAU


def _infrastructure_risk(
    node_risks: Dict[str, float],
    G: nx.DiGraph,
    seed_node: str,
) -> float:
    """Compute consequence-weighted infrastructure risk across non-seed nodes.

    infrastructure_risk = Σ(p_v * infra_v) / Σ(infra_v)

    where infra_v = G.nodes[v].get("infra", 0.0) for non-seed nodes.
    Nodes with infra_v = 0 contribute nothing to numerator or denominator.
    Returns 0.0 when no node has a positive infra weight.
    """
    numerator = 0.0
    denominator = 0.0
    for v, data in G.nodes(data=True):
        if v == seed_node:
            continue
        infra_v = float(data.get("infra", 0.0))
        if infra_v <= 0.0:
            continue
        p_v = float(node_risks.get(v, 0.0))
        numerator += p_v * infra_v
        denominator += infra_v
    return round(numerator / denominator, 4) if denominator > 0 else 0.0


def compute_measures(
    sim_result: Dict[str, Any],
    G: nx.DiGraph,
) -> Dict[str, float]:
    """Extract the five canonical measures from a simulate() result.

    Args:
        sim_result: Return value of simulate() or cascade().
        G: The consequence graph (used for infra weights).

    Returns:
        {
            "impact_index": float,        # cascade_risk 0–1
            "cascade_length": int,        # number of failing nodes
            "population_risk": float,     # p[Population] 0–1
            "infrastructure_risk": float, # infra-weighted avg 0–1
            "emergency_delay": float,     # p[Emergency Access] 0–1
        }
    """
    seed = sim_result.get("seed_node", "Flood")
    node_risks = sim_result.get("node_risks", {})

    return {
        "impact_index": round(float(sim_result.get("cascade_risk", 0.0)), 4),
        "cascade_length": int(sim_result.get("cascade_length", 0)),
        "population_risk": round(float(node_risks.get("Population", 0.0)), 4),
        "infrastructure_risk": _infrastructure_risk(node_risks, G, seed),
        "emergency_delay": round(
            float(node_risks.get("Emergency Access", 0.0)), 4
        ),
    }


def _reductions(
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> Dict[str, float]:
    """Compute absolute and relative reductions for each measure.

    Relative reduction = (before - after) / before  (floored at 0;
    negative reductions are clamped to 0 — interventions cannot worsen risk
    in the model).
    """
    reductions: Dict[str, Any] = {}
    for key in before:
        b = float(before[key])
        a = float(after[key])
        delta = b - a
        rel = (delta / b) if b > 0 else 0.0
        reductions[key] = {
            "absolute": round(delta, 4),
            "relative": round(max(0.0, rel), 4),
        }
    return reductions


def run_what_if(
    G: nx.DiGraph,
    flood_risk: float,
    intervention: Optional[Dict[str, Any]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Dict[str, Any]:
    """Run a paired baseline + intervention simulation and return before/after measures.

    Args:
        G: Consequence graph (not mutated).
        flood_risk: FloodRisk score (0–100) for the zone.
        intervention: Catalogue action dict with ``target_node`` and
            ``mitigation_m``.  If None, the post-intervention sim is the same
            as baseline (effectively comparing baseline to itself).
        tau: Cascade threshold.

    Returns:
        {
            "before": {impact_index, cascade_length, population_risk,
                       infrastructure_risk, emergency_delay},
            "after":  {same keys},
            "reductions": {key: {absolute, relative}},
            "intervention_applied": intervention dict or None,
            "baseline_simulation": full baseline simulate() dict,
            "post_simulation": full post-intervention simulate() dict,
        }
    """
    baseline_sim = simulate(G, flood_risk=flood_risk, intervention=None, tau=tau)
    post_sim = simulate(G, flood_risk=flood_risk, intervention=intervention, tau=tau)

    before = compute_measures(baseline_sim, G)
    after = compute_measures(post_sim, G)
    reductions = _reductions(before, after)

    return {
        "before": before,
        "after": after,
        "reductions": reductions,
        "intervention_applied": intervention,
        "baseline_simulation": baseline_sim,
        "post_simulation": post_sim,
    }
