"""CLIMAFORGE Algorithm 7: Cascade-Break Point Detection & Simulation.

Evaluates catalogue-backed mitigation actions using the shared simulate() core
to locate the optimal intervention point that maximizes cascade risk attenuation.

Directly implements Section 6.3 (Algorithm 7), Section 5.3 (Catalogue),
and Section 9 of the CLIMAFORGE Algorithm Design & Implementation Report v2.
"""

from typing import Any, Dict, List, Optional
import networkx as nx

from app.engine.alg5_cascade import simulate
from app.engine.constants import CASCADE_THRESHOLD_TAU, INTERVENTION_CATALOGUE


def evaluate_break_points(
    G: nx.DiGraph,
    flood_risk: float,
    catalogue: Optional[List[Dict[str, Any]]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Dict[str, Any]:
    """Evaluates candidate interventions from the catalogue against the consequence graph.

    Formulas per Section 6.3:
    - Baseline: base = simulate(G, flood_risk, intervention=None, tau=tau)
    - For each action i in catalogue:
      sim_i = simulate(G, flood_risk, intervention=i, tau=tau)
      ImpactReduction = base.cascade_risk - sim_i.cascade_risk
      RelativeReduction = ImpactReduction / base.cascade_risk (if base.cascade_risk > 0)
    - Ranked descending by ImpactReduction.
    - Top pair is the Best Intervention Point (Break Point).
    """
    actions = catalogue or INTERVENTION_CATALOGUE

    # 1. Compute baseline cascade state
    baseline = simulate(G, flood_risk=flood_risk, intervention=None, tau=tau)
    base_risk = float(baseline["cascade_risk"])
    base_length = int(baseline["cascade_length"])
    base_chain = baseline["cascade_chain"]

    # 2. Simulate each catalogue intervention
    eval_rows: List[Dict[str, Any]] = []

    for action in actions:
        intv_id = action.get("intervention_id", "INTV-UNKNOWN")
        target_node = action.get("target_node") or action.get("target")
        action_title = action.get("action") or action.get("name", intv_id)
        m = float(action.get("mitigation_m") or action.get("m") or 0.0)

        # Execute shared simulation core on modified graph
        sim = simulate(G, flood_risk=flood_risk, intervention=action, tau=tau)
        mitigated_risk = float(sim["cascade_risk"])
        mitigated_length = int(sim["cascade_length"])
        mitigated_chain = sim["cascade_chain"]

        # Reduction metrics
        abs_reduction = round(max(0.0, base_risk - mitigated_risk), 4)
        rel_reduction = (
            round(abs_reduction / base_risk, 4) if base_risk > 0.0 else 0.0
        )
        length_reduction = max(0, base_length - mitigated_length)

        # Surviving non-seed nodes (below failure threshold tau)
        surviving = [
            v for v, p_val in sim["node_risks"].items()
            if v != sim["seed_node"] and p_val < tau
        ]

        # Target node specific risk shift
        target_orig_p = baseline["node_risks"].get(target_node, 0.0)
        target_mitigated_p = sim["node_risks"].get(target_node, 0.0)

        eval_rows.append({
            "intervention_id": intv_id,
            "action": action_title,
            "target_node": target_node,
            "mitigation_m": m,
            "required_resources": action.get("required_resources", {}),
            "cost_usd": action.get("cost_usd", 0.0),
            "lead_time_minutes": action.get("lead_time_minutes", 0),
            "baseline_cascade_risk": base_risk,
            "mitigated_cascade_risk": mitigated_risk,
            "impact_reduction_abs": abs_reduction,
            "impact_reduction_rel": rel_reduction,
            "impact_reduction_pct": round(rel_reduction * 100.0, 2),
            "baseline_cascade_length": base_length,
            "mitigated_cascade_length": mitigated_length,
            "cascade_length_delta": length_reduction,
            "mitigated_cascade_chain": mitigated_chain,
            "surviving_nodes": surviving,
            "target_node_risk_before": target_orig_p,
            "target_node_risk_after": target_mitigated_p,
            "target_node_exists": target_node in G.nodes,
        })

    # 3. Deterministic descending ranking by absolute impact reduction
    eval_rows.sort(
        key=lambda r: (
            r["impact_reduction_abs"],
            r["cascade_length_delta"],
            r["mitigation_m"],
            -len(r["intervention_id"]),
            r["intervention_id"],
        ),
        reverse=True,
    )

    for rank, r in enumerate(eval_rows, 1):
        r["rank"] = rank

    best_break_point = eval_rows[0] if eval_rows else None

    return {
        "baseline": {
            "cascade_risk": base_risk,
            "cascade_length": base_length,
            "cascade_chain": base_chain,
            "failing_nodes": baseline["failing_nodes"],
            "node_risks": baseline["node_risks"],
        },
        "best_break_point": best_break_point,
        "ranked_break_points": eval_rows,
        "evaluated_action_count": len(eval_rows),
    }
