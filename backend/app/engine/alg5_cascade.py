"""CLIMAFORGE Algorithm 5: Cascade Detection & Noisy-OR Probability Propagation.

Follows the flood through the dependency graph and estimates the failure risk
for each urban infrastructure system using a bounded noisy-OR formulation.

Directly implements Section 6.3 (Algorithm 5) and Section 9 (Worked Example)
of the CLIMAFORGE Algorithm Design & Implementation Report v2.
"""

from typing import Any, Dict, List, Optional, Tuple
import networkx as nx

from app.engine.constants import CASCADE_THRESHOLD_TAU


def break_cycles_deterministic(G: nx.DiGraph) -> Tuple[nx.DiGraph, List[Dict[str, Any]]]:
    """Detects cycles and deterministically removes the weakest edge per cycle.

    Per Report Section 6.3 Alg 5 step 2:
    - Finds cycles in directed graph.
    - For each cycle, identifies the edge (u, v) with the minimum dependency strength s.
    - Breaks ties deterministically using alphabetical ordering of (u, v).
    - Logs each cycle resolution for auditability and verification.
    - Guarantees termination and pure deterministic DAG output for topological sort.
    """
    H = G.copy()
    cycle_logs: List[Dict[str, Any]] = []

    # Iteratively detect and eliminate cycles until H is an acyclic DAG
    iteration_guard = 0
    max_iterations = len(G.edges()) + 1

    while not nx.is_directed_acyclic_graph(H) and iteration_guard < max_iterations:
        iteration_guard += 1
        simple_cycles = list(nx.simple_cycles(H))
        if not simple_cycles:
            break

        # Canonical sort of cycles: shortest cycle first, then node sequence
        simple_cycles.sort(key=lambda cyc: (len(cyc), cyc))
        chosen_cycle = simple_cycles[0]

        # Extract directed edges in this cycle along with their dependency strength
        cycle_edges = []
        for i in range(len(chosen_cycle)):
            u = chosen_cycle[i]
            v = chosen_cycle[(i + 1) % len(chosen_cycle)]
            s = float(H[u][v].get("s", 1.0))
            cycle_edges.append((s, str(u), str(v)))

        # Sort ascending by strength (weakest edge first), tie-break alphabetically
        cycle_edges.sort(key=lambda item: (item[0], item[1], item[2]))
        weakest_s, u_rem, v_rem = cycle_edges[0]

        # Remove the weakest edge
        H.remove_edge(u_rem, v_rem)
        cycle_logs.append({
            "cycle": [str(n) for n in chosen_cycle],
            "removed_edge": [u_rem, v_rem],
            "strength": weakest_s,
            "reason": (
                f"Deterministically removed weakest dependency edge '{u_rem}' -> '{v_rem}' "
                f"(strength={weakest_s:.3f}) to ensure acyclic cascade propagation."
            ),
        })

    return H, cycle_logs


def cascade(
    G: nx.DiGraph,
    flood_risk: float,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Dict[str, Any]:
    """Propagates failure probabilities through the consequence graph using Noisy-OR.

    Formulas per Section 6.3:
    - p[seed] = clamp(flood_risk / 100.0, 0.0, 1.0)
    - For non-seed v in topological order:
      p_v = f_v * [ 1 - prod_{u in pred(v)} (1 - p_u * s_{uv}) ]
    - Failing nodes: {v != seed | p_v >= tau}
    - Cascade length: count of failing non-seed nodes
    - CascadeRisk: sum(p_v * c_v) / sum(c_v) over all non-seed nodes
    """
    # 1. Break cycles deterministically to guarantee DAG
    dag, cycle_logs = break_cycles_deterministic(G)

    # 2. Identify seed node
    seed_nodes = [n for n, d in dag.nodes(data=True) if d.get("seed", False)]
    seed = seed_nodes[0] if seed_nodes else "Flood"

    # Seed risk normalized to [0, 1]
    p: Dict[str, float] = {
        seed: max(0.0, min(1.0, float(flood_risk) / 100.0))
    }

    # 3. Topological traversal
    topo_order = list(nx.topological_sort(dag))
    non_seed_nodes = [v for v in topo_order if v != seed]

    for v in non_seed_nodes:
        preds = list(dag.predecessors(v))
        if preds:
            keep = 1.0
            for u in preds:
                pu = p.get(u, 0.0)
                s_uv = float(dag[u][v].get("s", 1.0))
                keep *= (1.0 - pu * s_uv)
            f_v = float(dag.nodes[v].get("f", 0.5))
            p[v] = round(max(0.0, min(1.0, f_v * (1.0 - keep))), 4)
        else:
            p[v] = 0.0

    # 4. Failing nodes and categorization
    failing_nodes = [v for v in non_seed_nodes if p[v] >= tau]

    node_states: Dict[str, Dict[str, Any]] = {}
    for v in non_seed_nodes:
        risk_val = p[v]
        if risk_val >= tau:
            state = "FAILING"
        elif risk_val >= 0.15:
            state = "WATCH"
        else:
            state = "SAFE"

        # Strongest incoming edge for traceability
        preds = list(dag.predecessors(v))
        strongest_pred = None
        strongest_s = 0.0
        if preds:
            preds_with_s = [(u, float(dag[u][v].get("s", 1.0)) * p.get(u, 0.0)) for u in preds]
            preds_with_s.sort(key=lambda item: item[1], reverse=True)
            strongest_pred = preds_with_s[0][0]
            strongest_s = float(dag[strongest_pred][v].get("s", 1.0))

        node_states[v] = {
            "node_id": v,
            "label": dag.nodes[v].get("label", v),
            "category": dag.nodes[v].get("category", "infrastructure"),
            "risk_p": risk_val,
            "vulnerability_f": dag.nodes[v].get("f", 0.5),
            "consequence_c": dag.nodes[v].get("c", 0.5),
            "state": state,
            "strongest_incoming_predecessor": strongest_pred,
            "strongest_dependency_strength": strongest_s,
        }

    # 5. Build cascade chain along strongest incoming edge among failing nodes
    cascade_chain: List[str] = []
    if failing_nodes:
        # Trace path through failing nodes starting with top failing node in topological order
        start_node = failing_nodes[0]
        curr: Optional[str] = start_node
        visited = set()
        while curr and curr not in visited:
            cascade_chain.append(curr)
            visited.add(curr)
            failing_succs = [
                s for s in dag.successors(curr)
                if s in failing_nodes and s not in visited
            ]
            if failing_succs:
                # Pick successor with highest dependency strength from curr
                failing_succs.sort(key=lambda s: float(dag[curr][s].get("s", 0.0)), reverse=True)
                curr = failing_succs[0]
            else:
                curr = None

    # 6. CascadeRisk = consequence-weighted average of p_v over all non-seed nodes
    c_weights = {
        v: float(dag.nodes[v].get("c", (
            float(dag.nodes[v].get("pop", 0.0)) +
            float(dag.nodes[v].get("infra", 0.0)) +
            float(dag.nodes[v].get("emerg", 0.0))
        ) / 3.0))
        for v in non_seed_nodes
    }
    sum_c = sum(c_weights.values())
    if sum_c > 0:
        cascade_risk = sum(p[v] * c_weights[v] for v in non_seed_nodes) / sum_c
    else:
        cascade_risk = sum(p[v] for v in non_seed_nodes) / len(non_seed_nodes) if non_seed_nodes else 0.0

    cascade_risk = round(max(0.0, min(1.0, cascade_risk)), 4)

    return {
        "seed_node": seed,
        "seed_risk": p[seed],
        "node_risks": p,
        "node_states": node_states,
        "failing_nodes": failing_nodes,
        "cascade_chain": cascade_chain,
        "cascade_length": len(failing_nodes),
        "cascade_risk": cascade_risk,
        "tau_applied": tau,
        "cycle_logs": cycle_logs,
        "topological_order": topo_order,
    }


def simulate(
    G: nx.DiGraph,
    flood_risk: float,
    intervention: Optional[Dict[str, Any]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Dict[str, Any]:
    """Shared authoritative simulation core used across Algorithms 7, 10, 11, and 12.

    Per Report Section 5.2 & Section 6.3:
    - Copies graph G.
    - If intervention provided, applies mitigation attenuation on target node vulnerability:
      f_target <- f_target * (1 - m)
    - Executes deterministic cascade propagation on the modified graph.
    """
    G2 = G.copy()
    applied_intervention = None

    if intervention:
        target_node = intervention.get("target_node") or intervention.get("target")
        mitigation_m = float(intervention.get("mitigation_m") or intervention.get("m") or 0.0)
        mitigation_m = max(0.0, min(1.0, mitigation_m))

        if target_node and target_node in G2.nodes:
            f_orig = float(G2.nodes[target_node].get("f", 0.5))
            f_mitigated = f_orig * (1.0 - mitigation_m)
            G2.nodes[target_node]["f"] = round(f_mitigated, 4)
            applied_intervention = {
                "intervention_id": intervention.get("intervention_id", "INTV-CUSTOM"),
                "target_node": target_node,
                "original_f": f_orig,
                "mitigated_f": round(f_mitigated, 4),
                "mitigation_m": mitigation_m,
            }

    sim_res = cascade(G2, flood_risk=flood_risk, tau=tau)
    sim_res["applied_intervention"] = applied_intervention
    return sim_res
