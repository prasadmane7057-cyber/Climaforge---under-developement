"""CLIMAFORGE Algorithm 6: Critical Node Identification.

Evaluates and ranks urban infrastructure nodes to isolate the single point of
failure whose disruption inflicts the most cascading damage across the city.

Directly implements Section 6.3 (Algorithm 6) and Section 9 of
the CLIMAFORGE Algorithm Design & Implementation Report v2.
"""

from typing import Any, Dict, List, Optional
import networkx as nx

from app.engine.constants import WEIGHTS_ALG6


def identify_critical_nodes(
    G: nx.DiGraph,
    p_risks: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Identifies the critical node in the consequence graph.

    Formulas per Section 6.3:
    Candidates = non-seed nodes.
    Raw features per candidate v:
    1. Direct = p_v
    2. Pop = p_v * pop_v
    3. Infra = p_v * infra_v
    4. Emerg = p_v * emerg_v
    5. Downstream = sum_{d in desc(v)} p_d * c_d / sum_{u} c_u  (0 if no descendants)
    6. DepCount = indegree(v) + outdegree(v)

    Each feature is max-scaled across candidates to [0, 1].
    Combined with configurable weights v (default WEIGHTS_ALG6):
    v = (Direct: 0.15, Pop: 0.20, Infra: 0.15, Emerg: 0.20, Downstream: 0.20, DepCount: 0.10)
    Ties broken deterministically: Downstream impact, then Direct risk, then node ID.
    """
    v_weights = weights or WEIGHTS_ALG6

    candidates = [
        str(n) for n, d in G.nodes(data=True)
        if not d.get("seed", False)
    ]

    if not candidates:
        return {
            "critical_node": None,
            "ranked_nodes": [],
            "scores": {},
            "weights_applied": v_weights,
            "max_factors": {},
        }

    # Total consequence weight sum across all candidate system nodes
    c_map = {
        v: float(G.nodes[v].get("c", (
            float(G.nodes[v].get("pop", 0.0)) +
            float(G.nodes[v].get("infra", 0.0)) +
            float(G.nodes[v].get("emerg", 0.0))
        ) / 3.0))
        for v in candidates
    }
    total_c = sum(c_map.values()) or 1.0

    raw_matrix: Dict[str, List[float]] = {}
    for v in candidates:
        pv = float(p_risks.get(v, 0.0))
        pop_v = float(G.nodes[v].get("pop", 0.0))
        infra_v = float(G.nodes[v].get("infra", 0.0))
        emerg_v = float(G.nodes[v].get("emerg", 0.0))

        # Downstream consequence-weighted sum
        descendants = list(nx.descendants(G, v))
        if descendants:
            downstream_val = sum(
                float(p_risks.get(d, 0.0)) * c_map.get(d, 0.0)
                for d in descendants
            ) / total_c
        else:
            downstream_val = 0.0

        dep_count = float(G.in_degree(v) + G.out_degree(v))

        raw_matrix[v] = [
            round(pv, 4),
            round(pv * pop_v, 4),
            round(pv * infra_v, 4),
            round(pv * emerg_v, 4),
            round(downstream_val, 4),
            dep_count,
        ]

    # Find max per column for 0-1 max-scaling
    feature_names = ["Direct", "Pop", "Infra", "Emerg", "Downstream", "DepCount"]
    max_values = [
        max(raw_matrix[v][i] for v in candidates)
        for i in range(6)
    ]
    max_factors = {
        feature_names[i]: round(max_values[i], 4) for i in range(6)
    }

    # Compute weighted criticality score
    scored_candidates: List[Dict[str, Any]] = []
    scores_dict: Dict[str, float] = {}

    for v in candidates:
        raw_vals = raw_matrix[v]
        scaled_vals = [
            raw_vals[i] / max_values[i] if max_values[i] > 0 else 0.0
            for i in range(6)
        ]

        score = (
            v_weights["Direct"] * scaled_vals[0] +
            v_weights["Pop"] * scaled_vals[1] +
            v_weights["Infra"] * scaled_vals[2] +
            v_weights["Emerg"] * scaled_vals[3] +
            v_weights["Downstream"] * scaled_vals[4] +
            v_weights["DepCount"] * scaled_vals[5]
        )
        score_rounded = round(score, 4)
        scores_dict[v] = score_rounded

        scored_candidates.append({
            "node_id": v,
            "label": G.nodes[v].get("label", v),
            "category": G.nodes[v].get("category", "infrastructure"),
            "criticality_score": score_rounded,
            "raw_features": {
                feature_names[i]: raw_vals[i] for i in range(6)
            },
            "scaled_features": {
                feature_names[i]: round(scaled_vals[i], 4) for i in range(6)
            },
            "downstream_impact": raw_vals[4],
            "direct_risk": raw_vals[0],
            "dependency_count": int(raw_vals[5]),
        })

    # Sort descending by criticality score, tie-break by downstream impact, then direct risk, then ID
    scored_candidates.sort(
        key=lambda item: (
            item["criticality_score"],
            item["downstream_impact"],
            item["direct_risk"],
            -len(item["node_id"]),
            item["node_id"],
        ),
        reverse=True,
    )

    for rank, item in enumerate(scored_candidates, 1):
        item["rank"] = rank

    critical_node = scored_candidates[0]["node_id"] if scored_candidates else None

    return {
        "critical_node": critical_node,
        "critical_node_details": scored_candidates[0] if scored_candidates else None,
        "ranked_nodes": scored_candidates,
        "scores": scores_dict,
        "weights_applied": v_weights,
        "max_factors": max_factors,
    }
