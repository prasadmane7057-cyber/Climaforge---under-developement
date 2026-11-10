"""Scenarios API router for CLIMAFORGE backend."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.auth import require_permission, require_scenario_access
from app.engine.pipeline import execute_risk_engine
from app.routers.audit import SESSION_AUDIT_LOGS
from app.schemas.routing import (
    CitizenAlertItem,
    EvacuationRouteRequest,
    EvacuationRouteResponse,
    ScenarioAlertsResponse,
    ScenarioSafePointsResponse,
)
from app.schemas.scenarios import (
    AuditEvent,
    ScenarioAnalysisResponse,
    ScenarioDetail,
    ScenarioSummaryItem,
)
from app.schemas.scenario_data import get_scenario_by_id, list_scenario_summaries
from app.services.alert_service import generate_scenario_alerts
from app.services.routing_service import (
    calculate_evacuation_route,
    get_scenario_safe_points,
)
from app.security.rbac import (
    PERM_CHATBOT_ASK,
    PERM_SCENARIO_READ,
    PERM_SCENARIO_RUN,
    PERM_SCENARIO_RUN_ADHOC,
)

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

# Thread-safe in-memory cache of generated evacuation routes
ROUTE_CACHE: Dict[str, EvacuationRouteResponse] = {}


class AdHocRunRequest(BaseModel):
    """Payload to execute deterministic risk engine on custom zone telemetry."""

    zones: List[Dict[str, Any]] = Field(..., description="Array of zone telemetry objects")
    scenario_id: Optional[str] = Field("adhoc-run", description="Evaluation tag")
    scenario_name: Optional[str] = Field("Ad-Hoc Catchment Evaluation", description="Display label")
    hotspot_threshold: Optional[float] = Field(50.0, ge=0.0, le=100.0, description="Hotspot qualification threshold")


@router.get(
    "",
    response_model=List[ScenarioSummaryItem],
    summary="List Scenarios",
    description="List all available synthetic demonstration scenarios for the operations dashboard.",
)
async def get_scenarios(
    _: Any = Depends(require_permission(PERM_SCENARIO_READ)),
) -> List[ScenarioSummaryItem]:
    """Retrieve catalog of demo scenarios."""
    return list_scenario_summaries()


@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetail,
    summary="Get Scenario Detail",
    description="Retrieve comprehensive zone telemetry and risk metrics for a specific scenario.",
)
async def get_scenario(
    scenario_id: str,
    scenario: ScenarioDetail = Depends(require_scenario_access(PERM_SCENARIO_READ)),
) -> ScenarioDetail:
    """Retrieve full details of the requested scenario."""
    return scenario


@router.post(
    "/{scenario_id}/analyze",
    response_model=ScenarioAnalysisResponse,
    summary="Run Scenario Flood Analysis",
    description=(
        "Executes deterministic Algorithms 0–3 on the designated scenario. "
        "Calculates canonical 0–100 risk scores, severity bands, hotspot ranking, "
        "and Algorithm 3 flood impact/exposure."
    ),
)
async def analyze_scenario(
    scenario_id: str,
    scenario: ScenarioDetail = Depends(require_scenario_access(PERM_SCENARIO_RUN)),
) -> ScenarioAnalysisResponse:
    """Execute deterministic calculation pipeline (Algorithms 0–3) on selected scenario."""
    # Transform scenario zones into raw engine inputs
    raw_zones: List[Dict[str, Any]] = []
    for z in scenario.zones:
        raw_zones.append({
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
        })

    # Execute deterministic pipeline
    result = execute_risk_engine(
        raw_zones=raw_zones,
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
    )

    # Record authentic backend audit event
    details = {
        "scenario_id": scenario.scenario_id,
        "pipeline_status": result["pipeline_status"],
        "hotspot_count": str(result["hotspot_count"]),
        "peak_risk": str(result["highest_risk_score"]),
        "spec": result["spec_version"],
    }
    if result.get("cascade_analysis"):
        details["cascade_risk"] = str(result["cascade_analysis"]["cascade_risk"])
        details["cascade_length"] = str(result["cascade_analysis"]["cascade_length"])
    if result.get("critical_nodes") and result["critical_nodes"].get("critical_node"):
        details["critical_node"] = str(result["critical_nodes"]["critical_node"])

    SESSION_AUDIT_LOGS.append(
        AuditEvent(
            event_id=f"EVT-ENGINE-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc),
            event_type="ANALYSIS_RUN",
            source="BACKEND",
            description=f"Deterministic engine executed Algorithms 0–7 for '{scenario.name}'",
            details=details,
        )
    )

    return ScenarioAnalysisResponse(**result)


@router.post(
    "/run/adhoc",
    response_model=ScenarioAnalysisResponse,
    summary="Run Ad-Hoc Flood Analysis",
    description="Executes deterministic Algorithms 0–3 directly on a user-provided array of zone telemetry.",
)
async def analyze_adhoc(
    payload: AdHocRunRequest,
    _: Any = Depends(require_permission(PERM_SCENARIO_RUN_ADHOC)),
) -> ScenarioAnalysisResponse:
    """Execute calculation pipeline on custom zone payload."""
    if not payload.zones:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Payload must include at least one zone record in 'zones'.",
        )

    threshold = payload.hotspot_threshold if payload.hotspot_threshold is not None else 50.0

    result = execute_risk_engine(
        raw_zones=payload.zones,
        scenario_id=payload.scenario_id,
        scenario_name=payload.scenario_name,
        hotspot_threshold=threshold,
    )

    SESSION_AUDIT_LOGS.append(
        AuditEvent(
            event_id=f"EVT-ADHOC-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc),
            event_type="ANALYSIS_RUN",
            source="BACKEND",
            description=f"Ad-hoc calculation run evaluated {len(payload.zones)} zones",
            details={
                "status": result["pipeline_status"],
                "hotspots": str(result["hotspot_count"]),
            },
        )
    )

    return ScenarioAnalysisResponse(**result)


@router.get(
    "/{scenario_id}/alerts",
    response_model=ScenarioAlertsResponse,
    summary="Get Pre-Calamity Citizen Alerts",
    description="Retrieves public pre-calamity alerts and hazard warnings for the scenario catchments.",
)
async def get_scenario_alerts(
    scenario_id: str,
    scenario: ScenarioDetail = Depends(require_scenario_access(PERM_SCENARIO_READ)),
) -> ScenarioAlertsResponse:
    return generate_scenario_alerts(scenario=scenario)


@router.get(
    "/{scenario_id}/safe-points",
    response_model=ScenarioSafePointsResponse,
    summary="Discover Scenario Safe Points",
    description="Retrieves available emergency evacuation shelters, capacities, and elevations.",
)
async def get_safe_points(
    scenario_id: str,
    scenario: ScenarioDetail = Depends(require_scenario_access(PERM_SCENARIO_READ)),
) -> ScenarioSafePointsResponse:
    return get_scenario_safe_points(scenario=scenario)


@router.post(
    "/{scenario_id}/evacuation-route",
    response_model=EvacuationRouteResponse,
    summary="Calculate Safe Evacuation Route",
    description=(
        "Calculates an optimal safe evacuation route from an origin zone to confirmed safe points, "
        "strictly pruning flooded and failing infrastructure nodes using NetworkX Dijkstra traversal."
    ),
)
async def plan_evacuation_route(
    scenario_id: str,
    payload: EvacuationRouteRequest,
    scenario: ScenarioDetail = Depends(require_scenario_access(PERM_CHATBOT_ASK)),
) -> EvacuationRouteResponse:
    route = calculate_evacuation_route(
        scenario=scenario,
        origin_zone_id=payload.origin_zone_id,
        destination_safe_point_id=payload.destination_safe_point_id,
        avoid_watch_nodes=payload.avoid_watch_nodes,
    )
    ROUTE_CACHE[route.route_id] = route
    return route


@router.get(
    "/{scenario_id}/evacuation-route/{route_id}",
    response_model=EvacuationRouteResponse,
    summary="Get Evacuation Route Status",
    description="Retrieve a previously calculated evacuation route plan by its route ID.",
)
async def get_route_status(
    scenario_id: str,
    route_id: str,
    scenario: ScenarioDetail = Depends(require_scenario_access(PERM_SCENARIO_READ)),
) -> EvacuationRouteResponse:
    route = ROUTE_CACHE.get(route_id)
    if route is None or route.scenario_id != scenario_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{route_id}' was not found for scenario '{scenario_id}'.",
        )
    return route


