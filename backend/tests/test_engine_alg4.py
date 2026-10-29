"""Unit tests for CLIMAFORGE Algorithm 4: Consequence Dependency Graph Construction.

Verifies:
- Node attributes: seed, vulnerability f, exposure attributes pop/infra/emerg, consequence weight c.
- Directed edge creation and dependency strength s.
- Serialization to dict and deserialization from dict (roundtrip fidelity).
- Canonical Zone A graph benchmark (Report v2 Section 9).
- Illustrative test fixture chain (Prompt E).
"""

import networkx as nx
import pytest

from app.engine.alg4_graph import (
    build_consequence_graph,
    build_illustrative_chain_graph,
    build_zone_a_graph,
    dict_to_graph,
    graph_to_dict,
)


class TestAlgorithm4ConsequenceGraph:
    """Tests for consequence graph construction, attributes, and serialization."""

    def test_default_graph_construction(self):
        hotspot = {"zone_id": "ZONE-001", "score": 75.0}
        exposure = {
            "population_score": 0.70,
            "infrastructure_score": 0.60,
            "road_score": 0.60,
            "emergency_score": 0.65,
        }
        G = build_consequence_graph(hotspot_zone=hotspot, exposure=exposure)

        assert isinstance(G, nx.DiGraph)
        assert "Flood" in G.nodes
        assert G.nodes["Flood"]["seed"] is True
        assert G.nodes["Flood"]["f"] == 1.0

        # Check non-seed system nodes
        expected_nodes = [
            "Drainage",
            "Road",
            "Main Junction A",
            "Emergency Access",
            "Hospital",
            "Population",
        ]
        for nid in expected_nodes:
            assert nid in G.nodes
            assert G.nodes[nid]["seed"] is False
            assert 0.0 <= G.nodes[nid]["f"] <= 1.0
            assert 0.0 <= G.nodes[nid]["c"] <= 1.0

        # Check edge dependency strengths
        for u, v, data in G.edges(data=True):
            assert "s" in data
            assert 0.0 <= data["s"] <= 1.0
            assert "dependency_type" in data

    def test_custom_nodes_and_edges(self):
        custom_nodes = [
            {"id": "Hazard", "seed": True, "f": 1.0},
            {"id": "Substation", "seed": False, "f": 0.8, "pop": 0.2, "infra": 0.9, "emerg": 0.5},
            {"id": "WaterPlant", "seed": False, "f": 0.7, "pop": 0.8, "infra": 0.7, "emerg": 0.6},
        ]
        custom_edges = [
            {"source": "Hazard", "target": "Substation", "s": 0.95},
            {"source": "Substation", "target": "WaterPlant", "s": 0.85},
        ]
        G = build_consequence_graph(custom_nodes=custom_nodes, custom_edges=custom_edges)

        assert len(G.nodes) == 3
        assert len(G.edges) == 2
        assert G.nodes["Substation"]["f"] == 0.8
        assert G["Substation"]["WaterPlant"]["s"] == 0.85

    def test_serialization_roundtrip(self):
        G1 = build_zone_a_graph()
        data = graph_to_dict(G1)

        assert data["node_count"] == len(G1.nodes)
        assert data["edge_count"] == len(G1.edges)

        G2 = dict_to_graph(data)
        assert len(G2.nodes) == len(G1.nodes)
        assert len(G2.edges) == len(G1.edges)

        for nid in G1.nodes:
            assert nid in G2.nodes
            assert G1.nodes[nid]["f"] == G2.nodes[nid]["f"]
            assert G1.nodes[nid]["c"] == G2.nodes[nid]["c"]

        for u, v in G1.edges:
            assert G2.has_edge(u, v)
            assert G1[u][v]["s"] == G2[u][v]["s"]

    def test_canonical_zone_a_graph_structure(self):
        G = build_zone_a_graph()
        assert len(G.nodes) == 7
        assert len(G.edges) == 8
        assert G.nodes["Flood"]["seed"] is True
        assert G.nodes["Drainage"]["f"] == 0.90
        assert G.nodes["Road"]["f"] == 0.82
        assert G.nodes["Main Junction A"]["f"] == 0.80
        assert G.nodes["Emergency Access"]["f"] == 0.86
        assert G.nodes["Hospital"]["f"] == 0.65
        assert G.nodes["Population"]["f"] == 0.90

        # Consequence weights
        assert G.nodes["Drainage"]["c"] == pytest.approx(0.433, abs=0.01)
        assert G.nodes["Road"]["c"] == pytest.approx(0.533, abs=0.01)
        assert G.nodes["Main Junction A"]["c"] == pytest.approx(0.600, abs=0.01)
        assert G.nodes["Hospital"]["c"] == pytest.approx(0.800, abs=0.01)

    def test_illustrative_chain_fixture(self):
        G = build_illustrative_chain_graph()
        expected_chain = [
            "Heavy Rainfall",
            "Drainage Stress",
            "Water Accumulation",
            "Road Disruption",
            "Emergency Access Delay",
            "Public-Health Pressure",
        ]
        assert len(G.nodes) == 6
        assert len(G.edges) == 5

        for i in range(len(expected_chain) - 1):
            u, v = expected_chain[i], expected_chain[i + 1]
            assert G.has_edge(u, v)
            assert G[u][v]["s"] > 0.0
