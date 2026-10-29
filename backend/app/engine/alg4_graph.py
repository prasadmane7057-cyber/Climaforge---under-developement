"""CLIMAFORGE Algorithm 4: Consequence Dependency Graph Construction.

Draws the "what depends on what" network topology so failure can propagate
from one urban infrastructure system to the next.

Directly implements Section 6.3 (Algorithm 4) and Section 9 (Worked Example)
of the CLIMAFORGE Algorithm Design & Implementation Report v2.
"""

from typing import Any, Dict, List, Optional, Tuple
import networkx as nx


def build_consequence_graph(
    hotspot_zone: Optional[Dict[str, Any]] = None,
    exposure: Optional[Dict[str, Any]] = None,
    custom_nodes: Optional[List[Dict[str, Any]]] = None,
    custom_edges: Optional[List[Dict[str, Any]]] = None,
) -> nx.DiGraph:
    """Builds a directed consequence graph G for a hotspot zone.

    If custom nodes and edges are provided, they are incorporated.
    Otherwise, constructs the canonical urban infrastructure dependency topology
    parameterized with the hotspot's exposure profile.
    """
    G = nx.DiGraph()

    if custom_nodes is not None and custom_edges is not None:
        for node in custom_nodes:
            nid = node["id"]
            pop = float(node.get("pop", 0.0))
            infra = float(node.get("infra", 0.0))
            emerg = float(node.get("emerg", 0.0))
            c = float(node.get("c", (pop + infra + emerg) / 3.0))
            G.add_node(
                nid,
                seed=bool(node.get("seed", False)),
                f=float(node.get("f", 0.5)),
                pop=pop,
                infra=infra,
                emerg=emerg,
                c=c,
                label=node.get("label", nid),
                category=node.get("category", "infrastructure"),
            )
        for edge in custom_edges:
            u, v = edge["source"], edge["target"]
            s = float(edge.get("s", edge.get("strength", 1.0)))
            G.add_edge(
                u,
                v,
                s=s,
                dependency_type=edge.get("dependency_type", "physical_cascade"),
            )
        return G

    # Derive baseline exposure proportions if available from Alg 3
    pop_score = 0.50
    infra_score = 0.50
    road_score = 0.50
    emerg_score = 0.50

    if exposure is not None:
        pop_score = float(exposure.get("population_score") or 0.50)
        infra_score = float(exposure.get("infrastructure_score") or 0.50)
        road_score = float(exposure.get("road_score") or 0.50)
        emerg_score = float(exposure.get("emergency_score") or 0.50)

    # 1. Seed node (Hazard initiator)
    G.add_node(
        "Flood",
        seed=True,
        f=1.0,
        pop=0.0,
        infra=0.0,
        emerg=0.0,
        c=0.0,
        label="Flood Inundation Hazard",
        category="hazard",
    )

    # 2. System nodes with calibrated baseline vulnerability f and exposure shares
    system_nodes = [
        {
            "id": "Drainage",
            "seed": False,
            "f": 0.90,
            "pop": 0.10,
            "infra": min(1.0, infra_score * 1.3),
            "emerg": 0.40,
            "label": "Stormwater Drainage Network & Culverts",
            "category": "drainage",
        },
        {
            "id": "Road",
            "seed": False,
            "f": 0.70,
            "pop": min(1.0, pop_score * 0.6),
            "infra": min(1.0, infra_score * 0.8),
            "emerg": min(1.0, emerg_score * 1.0),
            "label": "Arterial Road Network",
            "category": "transport",
        },
        {
            "id": "Main Junction A",
            "seed": False,
            "f": 0.65,
            "pop": min(1.0, pop_score * 0.7),
            "infra": min(1.0, infra_score * 0.7),
            "emerg": min(1.0, emerg_score * 1.3),
            "label": "Primary Traffic Junction & Staging Hub",
            "category": "traffic_chokepoint",
        },
        {
            "id": "Emergency Access",
            "seed": False,
            "f": 0.70,
            "pop": min(1.0, pop_score * 0.5),
            "infra": min(1.0, infra_score * 1.0),
            "emerg": min(1.0, emerg_score * 1.5),
            "label": "Designated Emergency Access Corridors",
            "category": "emergency_route",
        },
        {
            "id": "Hospital",
            "seed": False,
            "f": 0.40,
            "pop": min(1.0, pop_score * 0.8),
            "infra": min(1.0, infra_score * 1.6),
            "emerg": min(1.0, emerg_score * 1.2),
            "label": "District Emergency Trauma Hospital",
            "category": "medical_facility",
        },
        {
            "id": "Population",
            "seed": False,
            "f": 0.80,
            "pop": min(1.0, pop_score * 1.4),
            "infra": 0.10,
            "emerg": 0.20,
            "label": "Residential Population Centers",
            "category": "community",
        },
    ]

    for n in system_nodes:
        pop = round(float(n["pop"]), 3)
        infra = round(float(n["infra"]), 3)
        emerg = round(float(n["emerg"]), 3)
        c_v = round((pop + infra + emerg) / 3.0, 3)
        G.add_node(
            n["id"],
            seed=n["seed"],
            f=n["f"],
            pop=pop,
            infra=infra,
            emerg=emerg,
            c=c_v,
            label=n["label"],
            category=n["category"],
        )

    # 3. Directed dependency edges with strengths s (0.0 to 1.0)
    # Reflects: Flood -> Drainage -> Road -> Main Junction A -> Emergency Access -> Hospital
    # plus connections to Population
    edges = [
        ("Flood", "Drainage", 1.00, "hydraulic_inundation"),
        ("Flood", "Road", 0.40, "surface_sheetflow"),
        ("Drainage", "Road", 0.70, "culvert_overflow"),
        ("Road", "Main Junction A", 0.85, "traffic_bottleneck"),
        ("Main Junction A", "Emergency Access", 0.85, "route_impairment"),
        ("Emergency Access", "Hospital", 0.65, "transit_cutoff"),
        ("Drainage", "Population", 0.40, "localized_backflow"),
        ("Road", "Population", 0.50, "evacuation_isolation"),
        ("Emergency Access", "Population", 0.30, "first_responder_delay"),
    ]

    for u, v, s, dep_type in edges:
        G.add_edge(u, v, s=s, dependency_type=dep_type)

    return G


def build_zone_a_graph() -> nx.DiGraph:
    """Builds the canonical Zone A worked example graph from Report v2 (Section 9 & Figure 3).

    Directly models the exact 8 directed dependency edges shown in Figure 3 (Im2383.jpg):
    - Linear infrastructure spine:
      Flood (seed) -> Drainage -> Road -> Main Junction A -> Emergency Access -> Hospital
    - Community exposure branches:
      Drainage -> Population, Road -> Population, Emergency Access -> Population

    Produces the canonical Section 9 benchmark behavior:
    - Baseline CascadeRisk ~ 0.446 - 0.451
    - 5 failing nodes (tau >= 0.30): Drainage, Road, Main Junction A, Emergency Access, Population
    - Hospital is a watch node (p ~ 0.25 < 0.30)
    - Cascade lengths under interventions: Baseline=5, I1=0, I2=3, I3=4 (exact match to Table 9.4)
    - Critical Node = Drainage (Rank 1, exact match to Section 9.2)
    - Break-point ranking: I1 > I4 > I2 > I3 (exact match to Section 6.3 & 9.2)
    """
    G = nx.DiGraph()

    # Seed
    G.add_node(
        "Flood",
        seed=True,
        f=1.0,
        pop=0.0,
        infra=0.0,
        emerg=0.0,
        c=0.0,
        label="Flood Hazard Initiator",
        category="hazard",
    )

    # System nodes (vulnerabilities f and consequence weights c from Section 6.3 / 9)
    G.add_node("Drainage", seed=False, f=0.90, pop=0.10, infra=0.80, emerg=0.40, c=0.4333, label="Drainage System", category="drainage")
    G.add_node("Road", seed=False, f=0.82, pop=0.40, infra=0.50, emerg=0.70, c=0.5333, label="Arterial Roads", category="transport")
    G.add_node("Main Junction A", seed=False, f=0.80, pop=0.50, infra=0.40, emerg=0.90, c=0.6000, label="Main Junction A", category="traffic_chokepoint")
    G.add_node("Emergency Access", seed=False, f=0.86, pop=0.30, infra=0.60, emerg=1.00, c=0.6333, label="Emergency Access Routes", category="emergency_route")
    G.add_node("Hospital", seed=False, f=0.65, pop=0.60, infra=1.00, emerg=0.80, c=0.8000, label="District Hospital", category="medical_facility")
    G.add_node("Population", seed=False, f=0.90, pop=1.00, infra=0.10, emerg=0.20, c=0.4333, label="Residential Population", category="community")

    # The 8 directed edges exactly as rendered in Figure 3
    G.add_edge("Flood", "Drainage", s=1.00, dependency_type="hydraulic_overload")
    G.add_edge("Drainage", "Road", s=1.00, dependency_type="overflow_spill")
    G.add_edge("Road", "Main Junction A", s=1.00, dependency_type="traffic_congestion")
    G.add_edge("Main Junction A", "Emergency Access", s=1.00, dependency_type="corridor_blockage")
    G.add_edge("Emergency Access", "Hospital", s=1.00, dependency_type="ambulance_delay")
    G.add_edge("Drainage", "Population", s=0.50, dependency_type="urban_ponding")
    G.add_edge("Road", "Population", s=0.45, dependency_type="evacuation_cutoff")
    G.add_edge("Emergency Access", "Population", s=0.55, dependency_type="rescue_delay")

    return G


def build_illustrative_chain_graph() -> nx.DiGraph:
    """Builds the test fixture dependency chain required by Milestone 3 prompt:

    Heavy Rainfall -> Drainage Stress -> Water Accumulation -> Road Disruption -> Emergency Access Delay -> Public-Health Pressure
    """
    G = nx.DiGraph()

    nodes = [
        ("Heavy Rainfall", True, 1.0, 0.0, 0.0, 0.0, 0.0, "Heavy Rainfall Inundation", "hazard"),
        ("Drainage Stress", False, 0.85, 0.10, 0.80, 0.30, 0.40, "Drainage Network Capacity Stress", "drainage"),
        ("Water Accumulation", False, 0.80, 0.20, 0.50, 0.40, 0.367, "Surface Ponding & Water Accumulation", "hydrology"),
        ("Road Disruption", False, 0.75, 0.50, 0.60, 0.80, 0.633, "Road Network Impairment & Disruption", "transport"),
        ("Emergency Access Delay", False, 0.70, 0.40, 0.70, 1.00, 0.70, "Emergency Access Delay & Detours", "emergency_route"),
        ("Public-Health Pressure", False, 0.50, 0.90, 0.90, 0.80, 0.867, "Hospital & Public-Health Pressure", "medical_facility"),
    ]

    for nid, seed, f, pop, infra, emerg, c, label, cat in nodes:
        G.add_node(
            nid,
            seed=seed,
            f=f,
            pop=pop,
            infra=infra,
            emerg=emerg,
            c=c,
            label=label,
            category=cat,
        )

    chain = [
        ("Heavy Rainfall", "Drainage Stress", 1.00),
        ("Drainage Stress", "Water Accumulation", 0.90),
        ("Water Accumulation", "Road Disruption", 0.85),
        ("Road Disruption", "Emergency Access Delay", 0.80),
        ("Emergency Access Delay", "Public-Health Pressure", 0.75),
    ]

    for u, v, s in chain:
        G.add_edge(u, v, s=s, dependency_type="linear_cascade")

    return G


def graph_to_dict(G: nx.DiGraph) -> Dict[str, Any]:
    """Serializes a NetworkX DiGraph into a JSON-compatible dictionary."""
    nodes = []
    for nid, data in G.nodes(data=True):
        nodes.append({
            "id": str(nid),
            "label": data.get("label", str(nid)),
            "seed": bool(data.get("seed", False)),
            "f": float(data.get("f", 0.5)),
            "pop": float(data.get("pop", 0.0)),
            "infra": float(data.get("infra", 0.0)),
            "emerg": float(data.get("emerg", 0.0)),
            "c": float(data.get("c", 0.0)),
            "category": data.get("category", "infrastructure"),
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "source": str(u),
            "target": str(v),
            "s": float(data.get("s", 1.0)),
            "dependency_type": data.get("dependency_type", "dependency"),
        })

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def dict_to_graph(data: Dict[str, Any]) -> nx.DiGraph:
    """Deserializes a dictionary into a NetworkX DiGraph."""
    G = nx.DiGraph()
    for n in data.get("nodes", []):
        G.add_node(
            n["id"],
            seed=bool(n.get("seed", False)),
            f=float(n.get("f", 0.5)),
            pop=float(n.get("pop", 0.0)),
            infra=float(n.get("infra", 0.0)),
            emerg=float(n.get("emerg", 0.0)),
            c=float(n.get("c", 0.0)),
            label=n.get("label", n["id"]),
            category=n.get("category", "infrastructure"),
        )
    for e in data.get("edges", []):
        G.add_edge(
            e["source"],
            e["target"],
            s=float(e.get("s", 1.0)),
            dependency_type=e.get("dependency_type", "dependency"),
        )
    return G
