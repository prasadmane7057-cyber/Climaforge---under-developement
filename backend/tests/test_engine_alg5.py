"""Unit tests for CLIMAFORGE Algorithm 5: Cascade Detection & Noisy-OR Probability Propagation.

Verifies:
- Deterministic cycle detection and weakest-edge removal.
- Deterministic cycle tie-breaking and audit logging.
- Noisy-OR formula propagation on acyclic and cyclic graphs.
- Boundary risk cases (0.0 flood risk, 100.0 flood risk).
- Cascade threshold tau=0.30: failing nodes, watch nodes, safe nodes.
- Cascade chain construction along strongest incoming edge.
- Zone A worked example benchmark (CascadeRisk ~ 0.446, 5 failing nodes).
- Shared simulate() core and intervention attenuation on vulnerability f.
"""

import networkx as nx
import pytest

from app.engine.alg4_graph import build_illustrative_chain_graph, build_zone_a_graph
from app.engine.alg5_cascade import (
    break_cycles_deterministic,
    cascade,
    simulate,
)


class TestAlgorithm5CascadePropagation:
    """Tests for probability propagation, cycle breaking, and simulation."""

    def test_cycle_breaking_drops_weakest_edge(self):
        # Create a graph with a directed triangle cycle: A -> B (0.9), B -> C (0.7), C -> A (0.4)
        G = nx.DiGraph()
        G.add_node("A", seed=False, f=0.8, c=0.5)
        G.add_node("B", seed=False, f=0.7, c=0.5)
        G.add_node("C", seed=False, f=0.6, c=0.5)
        G.add_edge("A", "B", s=0.9)
        G.add_edge("B", "C", s=0.7)
        G.add_edge("C", "A", s=0.4)  # Weakest edge in cycle

        dag, logs = break_cycles_deterministic(G)
        assert nx.is_directed_acyclic_graph(dag)
        assert len(logs) == 1
        assert logs[0]["removed_edge"] == ["C", "A"]
        assert logs[0]["strength"] == 0.4
        assert not dag.has_edge("C", "A")
        assert dag.has_edge("A", "B")
        assert dag.has_edge("B", "C")

    def test_cycle_breaking_deterministic_tie_breaking(self):
        # Create a cycle with equal edge strengths: X -> Y (0.5), Y -> X (0.5)
        G = nx.DiGraph()
        G.add_edge("X", "Y", s=0.5)
        G.add_edge("Y", "X", s=0.5)

        dag, logs = break_cycles_deterministic(G)
        assert nx.is_directed_acyclic_graph(dag)
        assert len(logs) == 1
        # Alphabetical tie-breaking: ('X', 'Y') comes before ('Y', 'X')
        assert logs[0]["removed_edge"] == ["X", "Y"]
        assert not dag.has_edge("X", "Y")
        assert dag.has_edge("Y", "X")

    def test_noisy_or_single_incoming_edge(self):
        # Hazard -> Asset: p_Asset = f_Asset * (p_Hazard * s)
        G = nx.DiGraph()
        G.add_node("Flood", seed=True, f=1.0, c=0.0)
        G.add_node("Substation", seed=False, f=0.80, c=0.6)
        G.add_edge("Flood", "Substation", s=0.75)

        res = cascade(G, flood_risk=60.0)
        # flood_risk / 100 = 0.60
        # p_Substation = 0.80 * (0.60 * 0.75) = 0.80 * 0.45 = 0.36
        assert res["node_risks"]["Flood"] == 0.60
        assert res["node_risks"]["Substation"] == pytest.approx(0.36, abs=0.005)
        assert "Substation" in res["failing_nodes"]

    def test_noisy_or_multiple_incoming_edges(self):
        # Node with 2 upstream parents
        G = nx.DiGraph()
        G.add_node("Flood", seed=True, f=1.0, c=0.0)
        G.add_node("Parent1", seed=False, f=1.0, c=0.5)
        G.add_node("Parent2", seed=False, f=1.0, c=0.5)
        G.add_node("Target", seed=False, f=1.0, c=0.5)

        G.add_edge("Flood", "Parent1", s=1.0)
        G.add_edge("Flood", "Parent2", s=1.0)
        G.add_edge("Parent1", "Target", s=0.5)
        G.add_edge("Parent2", "Target", s=0.5)

        # flood_risk = 100 -> p_P1 = 1.0, p_P2 = 1.0
        # keep = (1 - 1.0*0.5) * (1 - 1.0*0.5) = 0.5 * 0.5 = 0.25
        # p_Target = 1.0 * (1 - 0.25) = 0.75
        res = cascade(G, flood_risk=100.0)
        assert res["node_risks"]["Target"] == pytest.approx(0.75, abs=0.005)

    def test_boundary_zero_and_hundred_flood_risk(self):
        G = build_zone_a_graph()

        # Zero flood risk
        res_zero = cascade(G, flood_risk=0.0)
        assert res_zero["seed_risk"] == 0.0
        assert res_zero["cascade_risk"] == 0.0
        assert len(res_zero["failing_nodes"]) == 0

        # Maximum flood risk
        res_max = cascade(G, flood_risk=100.0)
        assert res_max["seed_risk"] == 1.0
        assert res_max["cascade_risk"] > 0.40
        assert len(res_max["failing_nodes"]) >= 5

    def test_canonical_zone_a_benchmark(self):
        # Section 9 Worked Example: flood_risk = 76.0, tau = 0.30
        G = build_zone_a_graph()
        res = cascade(G, flood_risk=76.0, tau=0.30)

        assert res["seed_risk"] == 0.76
        # Report v2 specifies CascadeRisk ~ 0.446 (0.43 - 0.46)
        assert 0.40 <= res["cascade_risk"] <= 0.48
        # Five failing nodes: Drainage, Road, Main Junction A, Emergency Access, Population
        assert res["cascade_length"] == 5
        assert "Drainage" in res["failing_nodes"]
        assert "Road" in res["failing_nodes"]
        assert "Main Junction A" in res["failing_nodes"]
        assert "Emergency Access" in res["failing_nodes"]
        assert "Population" in res["failing_nodes"]
        # Hospital is watch node (< 0.30)
        assert "Hospital" not in res["failing_nodes"]
        assert res["node_states"]["Hospital"]["state"] == "WATCH"

        # Cascade chain follows propagation path
        assert len(res["cascade_chain"]) >= 3
        assert res["cascade_chain"][0] == "Drainage"

    def test_shared_simulate_core(self):
        G = build_zone_a_graph()
        orig_drainage_f = G.nodes["Drainage"]["f"]

        intervention = {
            "intervention_id": "I1",
            "target_node": "Drainage",
            "mitigation_m": 0.60,
        }

        baseline = simulate(G, flood_risk=76.0)
        mitigated = simulate(G, flood_risk=76.0, intervention=intervention)

        # Ensure G itself was not mutated
        assert G.nodes["Drainage"]["f"] == orig_drainage_f

        # Attenuation verification
        assert mitigated["cascade_risk"] < baseline["cascade_risk"]
        assert mitigated["cascade_length"] < baseline["cascade_length"]
        assert mitigated["node_risks"]["Drainage"] < baseline["node_risks"]["Drainage"]
