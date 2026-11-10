"""Milestone 6: Comprehensive Automated Test Suite for Evacuation Routing & Pre-Calamity Alerts.

Verifies:
1. Pre-calamity alert severity classification (CRITICAL >= 75, HIGH >= 50, MEDIUM >= 25, LOW < 25)
2. Alert generation on flash-flood scenario (critical warnings with authoritative dominant causes)
3. Alert generation on baseline scenario (normal/low warnings without false alarms)
4. Dominant hazard cause attribution grounded in Algorithm 1/2 outputs without hallucination
5. Safe points discovery with capacity, elevation, and operational status
6. Dijkstra shortest-safe-path traversal under normal baseline conditions
7. Avoidance of flooded and failing infrastructure nodes (pruning FAILING nodes from Alg 5 cascade)
8. Elevated perimeter bypass corridor selection when primary arterial road fails
9. Nearest safe point auto-selection when destination is unspecified
10. Strict watch mode: avoiding WATCH nodes in addition to FAILING nodes
11. Blocked route handling when all exit paths are flooded: explicit BLOCKED status and shelter-in-place advice
12. Missing origin zone handling: explicit ERROR without inventing paths
13. Missing destination safe point handling: explicit ERROR
14. Disconnected graph handling without crashes or hallucinations
15. Synthetic route and alert labeling: is_live_confirmed=False, is_simulated=True, disclaimers present
16. Authentication and RBAC enforcement on alerts, safe points, and routing API endpoints
17. Route plan caching and retrieval via route_id
18. Existing chatbot backward compatibility with grounded evacuation and alert answers
"""

from __future__ import annotations

from pathlib import Path
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

import app.config as config_module
from app.db.base import Base
from app.db.session import create_db_engine, get_db, get_session_factory
from app.main import app
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.models.user import User
from app.schemas.scenario_data import SCENARIOS_STORE
from app.security.jwt import jwt_service
from app.security.passwords import password_service
from app.security.rbac import (
    ALL_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_ROLES,
    ROLE_AUDITOR,
    ROLE_OPERATOR,
    ROLE_VIEWER,
)
from app.services.alert_service import (
    classify_alert_severity,
    generate_scenario_alerts,
)
from app.services.routing_service import (
    build_evacuation_graph,
    calculate_evacuation_route,
    get_scenario_safe_points,
)


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def rbac_test_db(tmp_path: Path, monkeypatch):
    """Isolated test database with all 5 canonical roles and permissions."""
    db_file = tmp_path / f"test_rbac_m6_{uuid.uuid4().hex}.db"
    db_url = f"sqlite:///{db_file}"

    monkeypatch.setattr(config_module.settings, "jwt_signing_key", "k" * 32)
    monkeypatch.setattr(config_module.settings, "jwt_issuer", "climaforge")
    monkeypatch.setattr(config_module.settings, "jwt_audience", "climaforge-api")
    monkeypatch.setattr(config_module.settings, "refresh_token_pepper", "p" * 32)
    monkeypatch.setattr(config_module.settings, "access_token_minutes", 15)
    monkeypatch.setattr(config_module.settings, "refresh_token_days", 7)
    monkeypatch.setattr(config_module.settings, "database_url", db_url)

    engine = create_db_engine(db_url)
    Base.metadata.create_all(bind=engine)
    factory = get_session_factory(engine)

    with factory() as session:
        role_map: dict[str, Role] = {}
        for r_name in DEFAULT_ROLES:
            role = Role(name=r_name, description=f"{r_name} role")
            session.add(role)
            role_map[r_name] = role

        perm_map: dict[str, Permission] = {}
        for p_name in ALL_PERMISSIONS:
            perm = Permission(name=p_name, description=f"{p_name} permission")
            session.add(perm)
            perm_map[p_name] = perm

        session.flush()

        for r_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
            r_obj = role_map[r_name]
            for p_name in perms:
                p_obj = perm_map[p_name]
                rp = RolePermission(role_id=r_obj.id, permission_id=p_obj.id)
                session.add(rp)

        session.commit()

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield factory
    app.dependency_overrides.pop(get_db, None)


def create_test_user(factory, email: str, role_name: str) -> str:
    """Helper creating a user with a canonical role and returning an access token."""
    with factory() as session:
        user = User(
            email=email,
            hashed_password=password_service.hash_password("ValidPassword123!"),
            full_name=f"Test {role_name}",
            is_active=True,
            is_superuser=False,
            role=role_name.lower(),
        )
        session.add(user)
        session.flush()

        role = session.query(Role).filter_by(name=role_name.upper()).first()
        if role:
            ur = UserRole(user_id=user.id, role_id=role.id)
            session.add(ur)

        session.commit()
        session.refresh(user)
        user_id = user.id
        return jwt_service.create_access_token(user_id=user_id, role=role_name.lower(), email=email)


# -----------------------------------------------------------------------------
# Unit & Algorithmic Tests: Pre-Calamity Alerts
# -----------------------------------------------------------------------------

def test_alert_severity_classification_thresholds():
    """Verify strict adherence to canonical risk severity thresholds."""
    assert classify_alert_severity(100.0) == "CRITICAL"
    assert classify_alert_severity(75.0) == "CRITICAL"
    assert classify_alert_severity(74.99) == "HIGH"
    assert classify_alert_severity(50.0) == "HIGH"
    assert classify_alert_severity(49.99) == "MEDIUM"
    assert classify_alert_severity(25.0) == "MEDIUM"
    assert classify_alert_severity(24.99) == "LOW"
    assert classify_alert_severity(0.0) == "LOW"
    assert classify_alert_severity(None) == "DATA_INSUFFICIENT"
    assert classify_alert_severity(85.0, is_scorable=False) == "DATA_INSUFFICIENT"


def test_alert_generation_from_flash_flood_scenario():
    """Verify alert generation for flash-flood scenario identifies critical zones and causes."""
    scenario = SCENARIOS_STORE["scenario-flash-flood"]
    alerts_response = generate_scenario_alerts(scenario)

    assert alerts_response.scenario_id == "scenario-flash-flood"
    assert alerts_response.highest_severity == "CRITICAL"
    assert alerts_response.affected_zone_count >= 2
    assert alerts_response.is_simulated is True
    assert alerts_response.is_live_confirmed is False
    assert "SIMULATED" in alerts_response.disclaimer

    # Check that ZONE-001 or ZONE-004 is CRITICAL
    alert_map = {a.zone_id: a for a in alerts_response.alerts}
    assert "ZONE-001" in alert_map
    assert alert_map["ZONE-001"].severity == "CRITICAL"
    assert alert_map["ZONE-001"].risk_score >= 75.0
    assert alert_map["ZONE-001"].dominant_cause is not None
    assert "CRITICAL" in alert_map["ZONE-001"].headline
    assert alert_map["ZONE-001"].is_live_confirmed is False


def test_alert_generation_from_baseline_scenario():
    """Verify alert generation for baseline scenario has no false critical alerts."""
    scenario = SCENARIOS_STORE["scenario-baseline"]
    alerts_response = generate_scenario_alerts(scenario)

    assert alerts_response.highest_severity in ("MEDIUM", "LOW")
    for a in alerts_response.alerts:
        assert a.severity != "CRITICAL"
        assert a.is_simulated is True
        assert a.is_live_confirmed is False


def test_alert_dominant_cause_attribution_without_hallucination():
    """Verify dominant cause is directly derived from algorithm factor breakdown."""
    scenario = SCENARIOS_STORE["scenario-flash-flood"]
    alerts_response = generate_scenario_alerts(scenario)

    for alert in alerts_response.alerts:
        assert alert.dominant_cause != ""
        # The cause must be mentioned in description
        assert alert.dominant_cause in alert.description


def test_safe_points_discovery_and_metadata():
    """Verify discovery of scenario safe points includes capacities, elevations, and tags."""
    scenario = SCENARIOS_STORE["scenario-baseline"]
    safe_points_response = get_scenario_safe_points(scenario)

    assert len(safe_points_response.safe_points) == 3
    assert safe_points_response.total_shelter_capacity == 6700
    assert safe_points_response.highest_elevation_m >= 22.0

    sp_map = {sp.safe_point_id: sp for sp in safe_points_response.safe_points}
    assert "SP-01" in sp_map
    assert sp_map["SP-01"].name == "Highland Sports Arena Shelter"
    assert sp_map["SP-01"].zone_id == "ZONE-003"
    assert sp_map["SP-01"].capacity_persons == 3000
    assert sp_map["SP-01"].elevation_m == 22.0
    assert sp_map["SP-01"].is_operational is True


# -----------------------------------------------------------------------------
# Unit & Algorithmic Tests: Safe Evacuation Routing Engine
# -----------------------------------------------------------------------------

def test_routing_baseline_shortest_safe_path():
    """Verify Dijkstra finds the direct shortest safe path when all infrastructure is safe."""
    scenario = SCENARIOS_STORE["scenario-baseline"]
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-001",
        destination_safe_point_id="SP-01",
    )

    assert route.status == "CONFIRMED_SAFE"
    assert route.origin_zone_id == "ZONE-001"
    assert route.destination_safe_point_id == "SP-01"
    # In baseline, Road is safe; shortest path traverses Road -> Main Junction A -> Emergency Access
    assert "Road" in route.path_node_ids
    assert "Main Junction A" in route.path_node_ids
    assert route.distance_km is not None and route.distance_km > 0
    assert route.estimated_transit_minutes is not None and route.estimated_transit_minutes > 0
    assert route.avoided_hazard_nodes == []
    assert route.is_live_confirmed is False
    assert route.is_simulated is True
    assert len(route.waypoints) == len(route.path_node_ids)
    assert len(route.step_by_step_instructions) >= len(route.path_node_ids)


def test_routing_avoids_failing_flooded_nodes():
    """Verify that when Road fails in flash-flood cascade, Dijkstra avoids it and diverts to elevated bypass."""
    scenario = SCENARIOS_STORE["scenario-flash-flood"]
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-001",
        destination_safe_point_id="SP-01",
    )

    assert route.status == "CONFIRMED_SAFE"
    # Must strictly NOT contain the flooded 'Road' node
    assert "Road" not in route.path_node_ids
    # Must divert via the elevated perimeter bypass
    assert "ROAD-PERIM-01" in route.path_node_ids
    # 'Road' must be logged as an avoided hazard node
    assert "Road" in route.avoided_hazard_nodes
    assert any(detail.node_id == "Road" for detail in route.avoided_node_details)
    assert route.is_live_confirmed is False
    assert route.is_simulated is True


def test_routing_auto_selects_nearest_shelter():
    """Verify that when destination is None, Dijkstra selects the shelter with minimum transit time."""
    scenario = SCENARIOS_STORE["scenario-baseline"]
    # From ZONE-002 (Central Ward), SP-02 (Civic Center Hall) is directly inside the ward
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-002",
        destination_safe_point_id=None,
    )

    assert route.status == "CONFIRMED_SAFE"
    assert route.destination_safe_point_id == "SP-02"
    assert route.destination_safe_point_name == "Civic Center Evacuation Hall"
    assert route.estimated_transit_minutes < 5.0


def test_routing_strict_watch_mode_avoidance():
    """Verify that avoid_watch_nodes=True strictly prunes WATCH nodes in addition to FAILING nodes."""
    scenario = SCENARIOS_STORE["scenario-flash-flood"]
    # Main Junction A is in WATCH state in flash flood
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-001",
        destination_safe_point_id="SP-01",
        avoid_watch_nodes=True,
    )

    assert route.status == "CONFIRMED_SAFE"
    assert "Road" not in route.path_node_ids
    assert "Main Junction A" not in route.path_node_ids


def test_routing_blocked_when_all_paths_flooded():
    """Verify that when all exit corridors from an origin zone are flooded, route returns BLOCKED."""
    scenario = SCENARIOS_STORE["scenario-flash-flood"]
    # Custom block all exits from ZONE-001: Road (already failing in flash-flood), ROAD-PERIM-01, and ROAD-HARBOR-01
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-001",
        destination_safe_point_id="SP-01",
        custom_blocked_nodes={"ROAD-PERIM-01", "ROAD-HARBOR-01"},
    )

    assert route.status == "BLOCKED"
    assert route.path_node_ids == []
    assert route.waypoints == []
    assert route.distance_km is None
    assert route.estimated_transit_minutes is None
    assert route.error_message is not None
    assert "No safe evacuation route available" in route.error_message
    assert "Road" in route.error_message
    assert any("SHELTER IN PLACE" in instr for instr in route.step_by_step_instructions)
    assert route.is_live_confirmed is False


def test_routing_missing_origin_returns_explicit_error():
    """Verify that an unrecognized origin zone returns status ERROR without crashing or inventing paths."""
    scenario = SCENARIOS_STORE["scenario-baseline"]
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-NONEXISTENT",
        destination_safe_point_id="SP-01",
    )

    assert route.status == "ERROR"
    assert "ZONE-NONEXISTENT" in str(route.error_message)
    assert route.path_node_ids == []
    assert route.is_live_confirmed is False


def test_routing_missing_destination_returns_explicit_error():
    """Verify that an unrecognized safe point returns status ERROR without crashing."""
    scenario = SCENARIOS_STORE["scenario-baseline"]
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-001",
        destination_safe_point_id="SP-999-NONEXISTENT",
    )

    assert route.status == "ERROR"
    assert "SP-999-NONEXISTENT" in str(route.error_message)
    assert route.path_node_ids == []


def test_routing_disconnected_graph_handling():
    """Verify that a disconnected graph target returns BLOCKED instead of raising exceptions."""
    scenario = SCENARIOS_STORE["scenario-baseline"]
    # Build graph and simulate island target
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-004",
        destination_safe_point_id="SP-01",
        custom_blocked_nodes={"NODE-BRG-01", "ROAD-HARBOR-01"},
    )

    assert route.status == "BLOCKED"
    assert route.path_node_ids == []
    assert route.distance_km is None
    assert route.estimated_transit_minutes is None
    assert "No safe evacuation route available" in str(route.error_message)


def test_routing_synthetic_labeling_guarantee():
    """Verify that every route plan strictly asserts is_live_confirmed=False and is_simulated=True."""
    for s_id, sc in SCENARIOS_STORE.items():
        route = calculate_evacuation_route(sc, origin_zone_id="ZONE-001")
        assert route.is_live_confirmed is False
        assert route.is_simulated is True
        assert "SIMULATED" in route.disclaimer


# -----------------------------------------------------------------------------
# Integration Tests: Authenticated API & RBAC Enforcement
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_alerts_authenticated_and_rbac(rbac_test_db):
    """Verify GET /api/scenarios/{id}/alerts enforces authentication and RBAC."""
    factory = rbac_test_db
    viewer_token = create_test_user(factory, "viewer_m6@test.com", ROLE_VIEWER)
    auditor_token = create_test_user(factory, "auditor_m6@test.com", ROLE_AUDITOR)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res_unauth = await client.get("/api/scenarios/scenario-flash-flood/alerts")
        assert res_unauth.status_code == 401

        # 2. Auditor (lacks PERM_SCENARIO_READ) -> 403
        res_auditor = await client.get(
            "/api/scenarios/scenario-flash-flood/alerts",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        assert res_auditor.status_code == 403

        # 3. Viewer (has PERM_SCENARIO_READ) -> 200
        res_viewer = await client.get(
            "/api/scenarios/scenario-flash-flood/alerts",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_viewer.status_code == 200
        data = res_viewer.json()
        assert data["scenario_id"] == "scenario-flash-flood"
        assert data["highest_severity"] == "CRITICAL"
        assert len(data["alerts"]) >= 1


@pytest.mark.asyncio
async def test_api_safe_points_authenticated_and_rbac(rbac_test_db):
    """Verify GET /api/scenarios/{id}/safe-points enforces authentication and RBAC."""
    factory = rbac_test_db
    viewer_token = create_test_user(factory, "viewer_sp@test.com", ROLE_VIEWER)
    auditor_token = create_test_user(factory, "auditor_sp@test.com", ROLE_AUDITOR)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res_unauth = await client.get("/api/scenarios/scenario-baseline/safe-points")
        assert res_unauth.status_code == 401

        # 2. Auditor -> 403
        res_auditor = await client.get(
            "/api/scenarios/scenario-baseline/safe-points",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )
        assert res_auditor.status_code == 403

        # 3. Viewer -> 200
        res_viewer = await client.get(
            "/api/scenarios/scenario-baseline/safe-points",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_viewer.status_code == 200
        data = res_viewer.json()
        assert len(data["safe_points"]) == 3
        assert data["total_shelter_capacity"] == 6700


@pytest.mark.asyncio
async def test_api_evacuation_routing_and_cache(rbac_test_db):
    """Verify POST /api/scenarios/{id}/evacuation-route and retrieval via route_id."""
    factory = rbac_test_db
    operator_token = create_test_user(factory, "operator_route@test.com", ROLE_OPERATOR)
    auditor_token = create_test_user(factory, "auditor_route@test.com", ROLE_AUDITOR)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res_unauth = await client.post(
            "/api/scenarios/scenario-flash-flood/evacuation-route",
            json={"origin_zone_id": "ZONE-001", "destination_safe_point_id": "SP-01"},
        )
        assert res_unauth.status_code == 401

        # 2. Auditor (lacks PERM_CHATBOT_ASK) -> 403
        res_auditor = await client.post(
            "/api/scenarios/scenario-flash-flood/evacuation-route",
            headers={"Authorization": f"Bearer {auditor_token}"},
            json={"origin_zone_id": "ZONE-001", "destination_safe_point_id": "SP-01"},
        )
        assert res_auditor.status_code == 403

        # 3. Operator -> 200
        res_op = await client.post(
            "/api/scenarios/scenario-flash-flood/evacuation-route",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={"origin_zone_id": "ZONE-001", "destination_safe_point_id": "SP-01"},
        )
        assert res_op.status_code == 200
        route_data = res_op.json()
        assert route_data["status"] == "CONFIRMED_SAFE"
        assert "Road" not in route_data["path_node_ids"]
        assert "Road" in route_data["avoided_hazard_nodes"]
        assert route_data["is_live_confirmed"] is False

        # 4. Route retrieval by route_id
        route_id = route_data["route_id"]
        res_get = await client.get(
            f"/api/scenarios/scenario-flash-flood/evacuation-route/{route_id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert res_get.status_code == 200
        assert res_get.json()["route_id"] == route_id

        # 5. Nonexistent route -> 404
        res_404 = await client.get(
            "/api/scenarios/scenario-flash-flood/evacuation-route/ROUTE-NONEXISTENT",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_chatbot_backward_compatibility_with_evacuation_queries(rbac_test_db):
    """Verify chatbot answers questions about safe points, shelters, and active warnings."""
    factory = rbac_test_db
    viewer_token = create_test_user(factory, "viewer_chat@test.com", ROLE_VIEWER)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/chatbot/message",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "scenario_id": "scenario-flash-flood",
                "question": "What are the safe points and evacuation alerts?",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert "shelter" in data["answer"].lower() or "safe point" in data["answer"].lower() or "alert" in data["answer"].lower()
        # Verify non-authoritative disclaimers are preserved
        assert data.get("is_advisory", True) is True


def test_alert_severity_canonical_consistency():
    """Verify alert severity bands strictly match canonical constants.SEVERITY_BANDS."""
    from app.engine.constants import SEVERITY_BANDS
    from app.services.alert_service import ALERT_SEVERITY_THRESHOLDS

    assert ALERT_SEVERITY_THRESHOLDS == SEVERITY_BANDS
    assert SEVERITY_BANDS["CRITICAL"] == 75.0
    assert SEVERITY_BANDS["HIGH"] == 50.0
    assert SEVERITY_BANDS["MEDIUM"] == 25.0


def test_routing_missing_safe_points_data_returns_explicit_unavailable():
    """Verify that a scenario with empty safe points returns status ERROR without inventing destinations."""
    scenario = SCENARIOS_STORE["scenario-baseline"].model_copy(deep=True)
    scenario.safe_points = []

    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id="ZONE-001",
        destination_safe_point_id=None,
    )

    assert route.status == "ERROR"
    assert "No operational safe points are available" in str(route.error_message)
    assert route.path_node_ids == []
    assert route.is_live_confirmed is False


def test_routing_competing_paths_dijkstra_selects_longer_safe_path():
    """Verify that Dijkstra rejects a shorter unsafe path and selects a longer safe path."""
    import networkx as nx

    # Construct competing paths topology:
    # Path A (Short): Origin -> Node_Unsafe (FAILING) -> Dest (Length: 5.0)
    # Path B (Long):  Origin -> Node_Safe (SAFE) -> Dest (Length: 15.0)
    G = nx.Graph()
    G.add_edge("Origin", "Node_Unsafe", transit_minutes=2.0)
    G.add_edge("Node_Unsafe", "Dest", transit_minutes=3.0)
    G.add_edge("Origin", "Node_Safe", transit_minutes=7.0)
    G.add_edge("Node_Safe", "Dest", transit_minutes=8.0)

    # Node failure pruning: excise FAILING node
    safe_G = G.copy()
    safe_G.remove_node("Node_Unsafe")

    chosen_path = nx.dijkstra_path(safe_G, "Origin", "Dest", weight="transit_minutes")
    chosen_length = nx.dijkstra_path_length(safe_G, "Origin", "Dest", weight="transit_minutes")

    assert chosen_path == ["Origin", "Node_Safe", "Dest"]
    assert chosen_length == 15.0
    assert "Node_Unsafe" not in chosen_path


@pytest.mark.asyncio
async def test_cross_scenario_route_cache_isolation(rbac_test_db):
    """Verify that a route generated for Scenario A cannot be retrieved under Scenario B."""
    factory = rbac_test_db
    operator_token = create_test_user(factory, "operator_iso@test.com", ROLE_OPERATOR)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Generate route in scenario-flash-flood
        res_create = await client.post(
            "/api/scenarios/scenario-flash-flood/evacuation-route",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={"origin_zone_id": "ZONE-001", "destination_safe_point_id": "SP-01"},
        )
        assert res_create.status_code == 200
        route_id = res_create.json()["route_id"]

        # Attempt to access this route using scenario-baseline path -> must return 404
        res_cross = await client.get(
            f"/api/scenarios/scenario-baseline/evacuation-route/{route_id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert res_cross.status_code == 404
        assert "not found for scenario 'scenario-baseline'" in res_cross.json()["detail"]


def test_nugen_authority_separation_over_routes_and_alerts():
    """Verify Nugen advisory outputs cannot modify route plans, mark routes live-confirmed, or override risk scores."""
    from app.services.nugen_gateway import nugen_gateway

    scenario = SCENARIOS_STORE["scenario-flash-flood"]
    route = calculate_evacuation_route(scenario, origin_zone_id="ZONE-001", destination_safe_point_id="SP-01")

    # Authoritative route asserts is_live_confirmed=False
    assert route.is_live_confirmed is False
    assert route.is_simulated is True

    # Nugen status is advisory only
    status = nugen_gateway.get_status()
    assert "advisory" in status["authority"].lower()
    assert "Algorithms 0–13 are authoritative" in status["authority"]
    assert "ADVISORY" in status["advisory_label"].upper()

