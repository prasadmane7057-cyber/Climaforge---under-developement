"""CLIMAFORGE Milestone 6 Safe Evacuation Route Engine.

Calculates deterministic, safe evacuation routes from hazard zones to confirmed shelters,
avoiding flooded or failing infrastructure nodes using NetworkX Dijkstra pathfinding.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from app.engine.pipeline import execute_risk_engine
from app.schemas.routing import (
    EvacuationRouteResponse,
    HazardAvoidanceDetail,
    RouteWaypointItem,
    SafePointDetail,
    ScenarioSafePointsResponse,
)
from app.schemas.scenarios import ScenarioDetail


# Canonical urban transport network nodes and metadata
EVACUATION_NETWORK_NODES: Dict[str, Dict[str, Any]] = {
    # Zone origin centroids
    "ZONE-001": {
        "name": "Riverside Industrial District",
        "zone_id": "ZONE-001",
        "node_type": "origin_zone",
        "elevation_m": 4.5,
    },
    "ZONE-002": {
        "name": "Central Ward & Commercial Core",
        "zone_id": "ZONE-002",
        "node_type": "origin_zone",
        "elevation_m": 9.2,
    },
    "ZONE-003": {
        "name": "Valley Residential Heights",
        "zone_id": "ZONE-003",
        "node_type": "origin_zone",
        "elevation_m": 18.0,
    },
    "ZONE-004": {
        "name": "Harbor & Estuary Basin",
        "zone_id": "ZONE-004",
        "node_type": "origin_zone",
        "elevation_m": 2.1,
    },
    # Intermediate infrastructure & transit corridors
    "Road": {
        "name": "Arterial Road Network",
        "zone_id": "ZONE-001",
        "node_type": "road",
        "elevation_m": 5.0,
        "consequence_node_id": "Road",
    },
    "Main Junction A": {
        "name": "Primary Traffic Junction & Staging Hub",
        "zone_id": "ZONE-002",
        "node_type": "junction",
        "elevation_m": 8.5,
        "consequence_node_id": "Main Junction A",
    },
    "Emergency Access": {
        "name": "Designated Emergency Access Corridors",
        "zone_id": "ZONE-002",
        "node_type": "emergency_route",
        "elevation_m": 11.0,
        "consequence_node_id": "Emergency Access",
    },
    "NODE-BRG-01": {
        "name": "East River Arterial Bridge",
        "zone_id": "ZONE-002",
        "node_type": "bridge",
        "elevation_m": 7.5,
        "consequence_node_id": "NODE-BRG-01",
    },
    "ROAD-PERIM-01": {
        "name": "Highland Ridge Perimeter Bypass",
        "zone_id": "ZONE-003",
        "node_type": "bypass",
        "elevation_m": 19.5,
        "consequence_node_id": "ROAD-PERIM-01",
    },
    "ROAD-HARBOR-01": {
        "name": "Harbor Causeway Evacuation Link",
        "zone_id": "ZONE-004",
        "node_type": "road",
        "elevation_m": 3.2,
        "consequence_node_id": "ROAD-HARBOR-01",
    },
    "JUNCTION-NORTH-01": {
        "name": "North Valley Staging Point",
        "zone_id": "ZONE-003",
        "node_type": "junction",
        "elevation_m": 20.0,
        "consequence_node_id": "JUNCTION-NORTH-01",
    },
    # Safe Points (Shelters)
    "SP-01": {
        "name": "Highland Sports Arena Shelter",
        "zone_id": "ZONE-003",
        "node_type": "safe_point",
        "elevation_m": 22.0,
    },
    "SP-02": {
        "name": "Civic Center Evacuation Hall",
        "zone_id": "ZONE-002",
        "node_type": "safe_point",
        "elevation_m": 12.5,
    },
    "SP-03": {
        "name": "Northern Technical Institute High Ground",
        "zone_id": "ZONE-003",
        "node_type": "safe_point",
        "elevation_m": 26.0,
    },
}

# Network edges: (u, v, distance_km, base_speed_kmh, label)
EVACUATION_NETWORK_EDGES: List[Tuple[str, str, float, float, str]] = [
    # ZONE-004 (Harbor) links
    ("ZONE-004", "NODE-BRG-01", 2.5, 40.0, "Cross East River Arterial Bridge north toward Central Core"),
    ("NODE-BRG-01", "ZONE-002", 1.8, 40.0, "Arrive in Central Ward via Bridge Accessway"),
    ("ZONE-004", "ROAD-HARBOR-01", 3.2, 35.0, "Depart Harbor Basin along Causeway northwest"),
    ("ROAD-HARBOR-01", "ZONE-001", 2.0, 35.0, "Connect into Riverside Industrial southern corridor"),

    # ZONE-001 (Riverside) primary central corridor
    ("ZONE-001", "Road", 2.5, 40.0, "Merge onto Central Arterial Road Network"),
    ("Road", "Main Junction A", 2.0, 40.0, "Follow Arterial Road toward Primary Staging Hub"),

    # ZONE-001 elevated bypass corridor (Highland Ridge)
    ("ZONE-001", "ROAD-PERIM-01", 6.5, 45.0, "Divert onto Elevated Highland Ridge Perimeter Bypass"),
    ("ROAD-PERIM-01", "JUNCTION-NORTH-01", 4.0, 45.0, "Ascend Perimeter Bypass to North Valley Staging Point"),

    # Central Core & Junction links
    ("ZONE-002", "Main Junction A", 1.5, 30.0, "Proceed along Central Boulevard to Main Junction A"),
    ("ZONE-002", "SP-02", 0.8, 25.0, "Direct access to Civic Center Evacuation Hall"),
    ("Main Junction A", "Emergency Access", 2.2, 40.0, "Transfer through Designated Emergency Access Corridors"),
    ("Main Junction A", "SP-02", 1.2, 30.0, "Divert south to Civic Center Evacuation Hall"),

    # Emergency Access toward Highland Valley
    ("Emergency Access", "JUNCTION-NORTH-01", 2.0, 40.0, "Ascend Valley Accessway to North Valley Staging Point"),

    # Highland Valley & Safe Point links
    ("JUNCTION-NORTH-01", "SP-01", 1.2, 30.0, "Follow Highland Parkway to Highland Sports Arena Shelter"),
    ("JUNCTION-NORTH-01", "SP-03", 1.8, 30.0, "Proceed along North Tech Way to Northern Technical Institute"),
    ("ZONE-003", "JUNCTION-NORTH-01", 1.0, 30.0, "Local neighborhood connector to North Valley Staging Point"),
    ("ZONE-003", "SP-01", 1.2, 30.0, "Direct local transit to Highland Sports Arena Shelter"),
    ("ZONE-003", "SP-03", 1.5, 30.0, "Direct local transit to Northern Technical Institute"),
]


def build_evacuation_graph() -> nx.Graph:
    """Builds the canonical urban evacuation transit graph."""
    G = nx.Graph()
    for node_id, data in EVACUATION_NETWORK_NODES.items():
        G.add_node(node_id, **data)

    for u, v, dist_km, speed_kmh, label in EVACUATION_NETWORK_EDGES:
        transit_minutes = round((dist_km / speed_kmh) * 60.0, 2)
        G.add_edge(
            u,
            v,
            distance_km=dist_km,
            base_speed_kmh=speed_kmh,
            transit_minutes=transit_minutes,
            label=label,
        )
    return G


def get_scenario_safe_points(scenario: ScenarioDetail) -> ScenarioSafePointsResponse:
    """Retrieves safe points from scenario definition with capacity and elevation details."""
    safe_points_list: List[SafePointDetail] = []
    total_capacity = 0
    max_elevation = 0.0

    for sp in scenario.safe_points:
        sp_id = str(sp.get("safe_point_id", ""))
        name = str(sp.get("name", sp_id))
        zone_id = str(sp.get("zone_id", ""))
        capacity = int(sp.get("capacity_persons", 0))
        elevation = float(sp.get("elevation_m", 0.0))
        label = str(sp.get("label", "SYNTHETIC / ILLUSTRATIVE"))

        total_capacity += capacity
        if elevation > max_elevation:
            max_elevation = elevation

        safe_points_list.append(
            SafePointDetail(
                safe_point_id=sp_id,
                name=name,
                zone_id=zone_id,
                capacity_persons=capacity,
                elevation_m=elevation,
                label=label,
                is_operational=True,
                amenities=["Emergency Shelter", "Potable Water", "First Aid Staging", "Backup Generator"],
            )
        )

    return ScenarioSafePointsResponse(
        scenario_id=scenario.scenario_id,
        safe_points=safe_points_list,
        total_shelter_capacity=total_capacity,
        highest_elevation_m=max_elevation,
    )


def extract_node_hazard_states(
    scenario: ScenarioDetail,
    deterministic_analysis: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Set[str], Set[str]]:
    """Extracts infrastructure node failure states from Algorithm 5 cascade analysis.

    Returns:
    - node_states: mapping of node_id to state information
    - failing_nodes: set of node IDs with state == 'FAILING' (p >= tau)
    - watch_nodes: set of node IDs with state == 'WATCH' (0.15 <= p < tau)
    """
    if deterministic_analysis is None:
        raw_zones = [
            {
                "zone_id": z.zone_id,
                "name": z.name,
                "rainfall_mm": z.rainfall_mm,
                "drainage_capacity_cms": z.drainage_capacity_cms,
                "elevation_m": z.elevation_m,
                "soil_saturation_index": z.soil_saturation_index,
                "water_level_m": z.water_level_m,
                "population": z.population,
                "critical_infrastructure_count": z.critical_infrastructure_count,
                "road_length_km": z.road_length_km,
                "emergency_routes_count": z.emergency_routes_count,
            }
            for z in scenario.zones
        ]
        deterministic_analysis = execute_risk_engine(
            raw_zones=raw_zones,
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
        )

    cascade = deterministic_analysis.get("cascade_analysis") or {}
    node_states = cascade.get("node_states") or {}

    failing_nodes: Set[str] = set()
    watch_nodes: Set[str] = set()

    for node_id, state_info in node_states.items():
        state = state_info.get("state", "SAFE")
        if state == "FAILING":
            failing_nodes.add(node_id)
        elif state == "WATCH":
            watch_nodes.add(node_id)

    return node_states, failing_nodes, watch_nodes


def calculate_evacuation_route(
    scenario: ScenarioDetail,
    origin_zone_id: str,
    destination_safe_point_id: Optional[str] = None,
    avoid_watch_nodes: bool = False,
    deterministic_analysis: Optional[Dict[str, Any]] = None,
    custom_blocked_nodes: Optional[Set[str]] = None,
) -> EvacuationRouteResponse:
    """Calculates a safe evacuation path using NetworkX Dijkstra shortest-path traversal.

    Guarantees:
    - Prunes nodes identified as FAILING in Algorithm 5 cascade analysis.
    - Prunes or penalizes WATCH nodes according to avoid_watch_nodes setting.
    - If path exists, returns step-by-step corridor waypoints with transit minutes and distance.
    - If no path exists (or network is partitioned), returns explicit BLOCKED status without fabricating paths.
    - Returns explicit error when origin or destination is invalid.
    - Explicitly marks is_live_confirmed=False and is_simulated=True.
    """
    now = datetime.now(timezone.utc)
    route_id = f"ROUTE-{scenario.scenario_id}-{origin_zone_id}-{destination_safe_point_id or 'NEAREST'}-{int(now.timestamp())}"

    # 1. Validate origin zone existence
    scenario_zone_ids = {z.zone_id for z in scenario.zones}
    if origin_zone_id not in scenario_zone_ids and origin_zone_id not in EVACUATION_NETWORK_NODES:
        return EvacuationRouteResponse(
            route_id=route_id,
            scenario_id=scenario.scenario_id,
            origin_zone_id=origin_zone_id,
            origin_zone_name=origin_zone_id,
            status="ERROR",
            is_live_confirmed=False,
            is_simulated=True,
            generated_at=now,
            error_message=f"Origin zone '{origin_zone_id}' was not found in the scenario network.",
        )

    origin_zone_name = EVACUATION_NETWORK_NODES.get(origin_zone_id, {}).get("name", origin_zone_id)
    for z in scenario.zones:
        if z.zone_id == origin_zone_id:
            origin_zone_name = z.name
            break

    # 2. Validate destination safe point existence if provided
    available_safe_points = scenario.safe_points or []
    safe_point_ids = {str(sp.get("safe_point_id")) for sp in available_safe_points}

    if destination_safe_point_id is not None:
        if destination_safe_point_id not in safe_point_ids:
            return EvacuationRouteResponse(
                route_id=route_id,
                scenario_id=scenario.scenario_id,
                origin_zone_id=origin_zone_id,
                origin_zone_name=origin_zone_name,
                destination_safe_point_id=destination_safe_point_id,
                status="ERROR",
                is_live_confirmed=False,
                is_simulated=True,
                generated_at=now,
                error_message=f"Destination safe point '{destination_safe_point_id}' does not exist in the scenario.",
            )

    # 3. Ingest hazard states from consequence analysis
    node_states, failing_nodes, watch_nodes = extract_node_hazard_states(
        scenario=scenario,
        deterministic_analysis=deterministic_analysis,
    )
    if custom_blocked_nodes:
        failing_nodes.update(custom_blocked_nodes)

    # 4. Construct routing graph and prune unsafe / flooded nodes
    base_graph = build_evacuation_graph()
    safe_graph = base_graph.copy()

    avoided_hazard_nodes: List[str] = []
    avoided_node_details: List[HazardAvoidanceDetail] = []

    # Map consequence failure states to transport network
    for net_node_id, data in EVACUATION_NETWORK_NODES.items():
        conseq_id = data.get("consequence_node_id") or net_node_id
        is_failing = conseq_id in failing_nodes or net_node_id in failing_nodes
        is_watch = conseq_id in watch_nodes or net_node_id in watch_nodes

        state_info = node_states.get(conseq_id) or node_states.get(net_node_id) or {}
        risk_p = float(state_info.get("risk_p", 0.0))

        if is_failing:
            if safe_graph.has_node(net_node_id):
                safe_graph.remove_node(net_node_id)
                avoided_hazard_nodes.append(net_node_id)
                avoided_node_details.append(
                    HazardAvoidanceDetail(
                        node_id=net_node_id,
                        name=data.get("name", net_node_id),
                        reason=f"Flooded or failing infrastructure (failure risk: {risk_p:.2f} >= threshold)",
                        risk_probability=risk_p,
                        failure_state="FAILING",
                    )
                )
        elif is_watch and avoid_watch_nodes:
            if safe_graph.has_node(net_node_id):
                safe_graph.remove_node(net_node_id)
                avoided_hazard_nodes.append(net_node_id)
                avoided_node_details.append(
                    HazardAvoidanceDetail(
                        node_id=net_node_id,
                        name=data.get("name", net_node_id),
                        reason=f"Ponding sheetflow water hazard (risk: {risk_p:.2f})",
                        risk_probability=risk_p,
                        failure_state="WATCH",
                    )
                )
        elif is_watch:
            # Penalize edges connected to WATCH nodes: speed halved -> transit time doubled
            for u, v in list(safe_graph.edges(net_node_id)):
                safe_graph[u][v]["transit_minutes"] = safe_graph[u][v].get("transit_minutes", 1.0) * 2.0

    # 5. Determine candidate destinations
    if destination_safe_point_id:
        target_destinations = [destination_safe_point_id]
    else:
        # Use safe points configured in the scenario
        target_destinations = [
            str(sp.get("safe_point_id"))
            for sp in available_safe_points
            if str(sp.get("safe_point_id")) in EVACUATION_NETWORK_NODES
        ]
        if not target_destinations:
            return EvacuationRouteResponse(
                route_id=route_id,
                scenario_id=scenario.scenario_id,
                origin_zone_id=origin_zone_id,
                origin_zone_name=origin_zone_name,
                status="ERROR",
                is_live_confirmed=False,
                is_simulated=True,
                generated_at=now,
                error_message=f"No operational safe points are available in scenario '{scenario.scenario_id}'. Destination data is required for route generation.",
            )

    # 6. Dijkstra shortest-safe-path search
    best_path: Optional[List[str]] = None
    best_cost: float = float("inf")
    best_destination: Optional[str] = None

    if safe_graph.has_node(origin_zone_id):
        for dest_id in target_destinations:
            if not safe_graph.has_node(dest_id):
                continue
            try:
                path = nx.dijkstra_path(
                    safe_graph,
                    source=origin_zone_id,
                    target=dest_id,
                    weight="transit_minutes",
                )
                cost = nx.dijkstra_path_length(
                    safe_graph,
                    source=origin_zone_id,
                    target=dest_id,
                    weight="transit_minutes",
                )
                if cost < best_cost:
                    best_cost = cost
                    best_path = path
                    best_destination = dest_id
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

    # 7. Handle path finding failure (blocked or disconnected)
    if not best_path or best_destination is None:
        blockers_str = ", ".join(avoided_hazard_nodes) if avoided_hazard_nodes else "network disruption"
        return EvacuationRouteResponse(
            route_id=route_id,
            scenario_id=scenario.scenario_id,
            origin_zone_id=origin_zone_id,
            origin_zone_name=origin_zone_name,
            destination_safe_point_id=destination_safe_point_id,
            status="BLOCKED",
            path_node_ids=[],
            waypoints=[],
            distance_km=None,
            estimated_transit_minutes=None,
            avoided_hazard_nodes=avoided_hazard_nodes,
            avoided_node_details=avoided_node_details,
            step_by_step_instructions=[
                "SHELTER IN PLACE: All safe evacuation corridors from this zone are currently impassable due to active flood waters.",
                "Move immediately to the highest available floor or reinforced vertical structure.",
                "Avoid entering standing or moving water under all circumstances.",
                "Await official rescue instructions from civil defense authorities.",
            ],
            is_live_confirmed=False,
            is_simulated=True,
            disclaimer=(
                "SIMULATED / ILLUSTRATIVE EVACUATION ROUTE ONLY. "
                "Do not use for real-world life-critical navigation without civil defense field verification."
            ),
            generated_at=now,
            error_message=(
                f"No safe evacuation route available from {origin_zone_name} to designated shelters. "
                f"Candidate transit corridors are blocked by active flood inundation at: {blockers_str}."
            ),
        )

    # 8. Build detailed waypoint sequence and instructions
    waypoints: List[RouteWaypointItem] = []
    instructions: List[str] = []
    cumulative_dist = 0.0
    cumulative_time = 0.0

    dest_info = EVACUATION_NETWORK_NODES.get(best_destination, {})
    dest_name = dest_info.get("name", best_destination)
    dest_zone = dest_info.get("zone_id", "ZONE-003")

    for i, node_id in enumerate(best_path):
        node_meta = EVACUATION_NETWORK_NODES.get(node_id, {})
        node_name = node_meta.get("name", node_id)
        zone_id = node_meta.get("zone_id", origin_zone_id)
        node_type = node_meta.get("node_type", "waypoint")
        conseq_id = node_meta.get("consequence_node_id") or node_id
        safety_status = "WATCH" if conseq_id in watch_nodes else "SAFE"

        if i == 0:
            instruction = f"Depart from {node_name}."
        else:
            prev_node = best_path[i - 1]
            edge_data = base_graph.get_edge_data(prev_node, node_id) or {}
            seg_dist = float(edge_data.get("distance_km", 1.0))
            seg_time = float(edge_data.get("transit_minutes", 2.0))
            cumulative_dist += seg_dist
            cumulative_time += seg_time
            turn_label = edge_data.get("label", f"Proceed to {node_name}")
            instruction = f"Step {i}: {turn_label} ({seg_dist:.1f} km, ~{seg_time:.1f} min)."

        instructions.append(instruction)
        waypoints.append(
            RouteWaypointItem(
                node_id=node_id,
                name=node_name,
                zone_id=zone_id,
                node_type=node_type,
                safety_status=safety_status,
                cumulative_distance_km=round(cumulative_dist, 2),
                cumulative_time_minutes=round(cumulative_time, 2),
                instruction=instruction,
            )
        )

    instructions.append(
        f"Final Destination: Arrive safely at {dest_name} (Elevation: {dest_info.get('elevation_m', 20.0)}m). Check in with shelter intake personnel."
    )

    return EvacuationRouteResponse(
        route_id=route_id,
        scenario_id=scenario.scenario_id,
        origin_zone_id=origin_zone_id,
        origin_zone_name=origin_zone_name,
        destination_safe_point_id=best_destination,
        destination_safe_point_name=dest_name,
        destination_zone_id=dest_zone,
        status="CONFIRMED_SAFE",
        path_node_ids=best_path,
        waypoints=waypoints,
        distance_km=round(cumulative_dist, 2),
        estimated_transit_minutes=round(cumulative_time, 1),
        avoided_hazard_nodes=avoided_hazard_nodes,
        avoided_node_details=avoided_node_details,
        step_by_step_instructions=instructions,
        is_live_confirmed=False,
        is_simulated=True,
        disclaimer=(
            "SIMULATED / ILLUSTRATIVE EVACUATION ROUTE ONLY. "
            "Do not use for real-world life-critical navigation without civil defense field verification."
        ),
        generated_at=now,
        error_message=None,
    )

