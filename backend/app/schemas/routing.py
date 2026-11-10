"""CLIMAFORGE Milestone 6 Data Contracts: Evacuation Routing and Pre-Calamity Alerts."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class RouteWaypointItem(BaseModel):
    """Specific transit checkpoint along an evacuation corridor."""

    node_id: str
    name: str
    zone_id: str
    node_type: str = Field(..., description="'origin_zone', 'road', 'junction', 'bridge', 'safe_point', 'bypass'")
    safety_status: Literal["SAFE", "WATCH", "FAILING"]
    cumulative_distance_km: float = Field(..., ge=0.0)
    cumulative_time_minutes: float = Field(..., ge=0.0)
    instruction: str


class HazardAvoidanceDetail(BaseModel):
    """Detailed record of flooded or impaired infrastructure avoided during routing."""

    node_id: str
    name: str
    reason: str
    risk_probability: float = Field(..., ge=0.0, le=1.0)
    failure_state: Literal["FAILING", "WATCH", "SAFE"]


class EvacuationRouteRequest(BaseModel):
    """Request payload to calculate a safe evacuation path."""

    origin_zone_id: str = Field(..., min_length=1, max_length=64)
    destination_safe_point_id: Optional[str] = Field(None, max_length=64)
    avoid_watch_nodes: bool = Field(False, description="Strict mode: avoid WATCH nodes in addition to FAILING nodes.")


class EvacuationRouteResponse(BaseModel):
    """Deterministic evacuation route response respecting consequence cascade safety."""

    route_id: str
    scenario_id: str
    origin_zone_id: str
    origin_zone_name: str
    destination_safe_point_id: Optional[str] = None
    destination_safe_point_name: Optional[str] = None
    destination_zone_id: Optional[str] = None
    status: Literal["CONFIRMED_SAFE", "BLOCKED", "NO_PATH_AVAILABLE", "ERROR"]
    path_node_ids: List[str] = Field(default_factory=list)
    waypoints: List[RouteWaypointItem] = Field(default_factory=list)
    distance_km: Optional[float] = None
    estimated_transit_minutes: Optional[float] = None
    avoided_hazard_nodes: List[str] = Field(default_factory=list)
    avoided_node_details: List[HazardAvoidanceDetail] = Field(default_factory=list)
    step_by_step_instructions: List[str] = Field(default_factory=list)
    is_live_confirmed: bool = Field(
        False, description="Cached or simulated routes must not be claimed live-confirmed safe without live telemetry."
    )
    is_simulated: bool = Field(
        True, description="Indicates route is generated from scenario consequence simulation."
    )
    disclaimer: str = Field(
        default="SIMULATED / ILLUSTRATIVE EVACUATION ROUTE ONLY. Do not use for real-world life-critical navigation without civil defense field verification."
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


class CitizenAlertItem(BaseModel):
    """Public pre-calamity warning for an affected catchment zone."""

    alert_id: str
    scenario_id: str
    zone_id: str
    zone_name: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "DATA_INSUFFICIENT"]
    risk_score: float = Field(..., ge=0.0, le=100.0)
    dominant_cause: str
    headline: str
    description: str
    action_recommendation: str
    is_simulated: bool = True
    is_live_confirmed: bool = False
    disclaimer: str = (
        "SIMULATED / ILLUSTRATIVE ALERT ONLY. Authoritative emergency directions require official civil defense verification."
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScenarioAlertsResponse(BaseModel):
    """Bundle of active pre-calamity alerts for a scenario."""

    scenario_id: str
    scenario_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alerts: List[CitizenAlertItem] = Field(default_factory=list)
    highest_severity: str
    affected_zone_count: int
    is_simulated: bool = True
    is_live_confirmed: bool = False
    disclaimer: str = "SIMULATED / ILLUSTRATIVE ALERTS ONLY. For demonstrator and emergency planning purposes."


class SafePointDetail(BaseModel):
    """Designated emergency refuge or evacuation shelter."""

    safe_point_id: str
    name: str
    zone_id: str
    capacity_persons: int
    elevation_m: float
    label: str = "SYNTHETIC / ILLUSTRATIVE"
    is_operational: bool = True
    amenities: List[str] = Field(
        default_factory=lambda: ["Emergency Shelter", "Potable Water", "First Aid Staging"]
    )


class ScenarioSafePointsResponse(BaseModel):
    """Directory of available safe evacuation points for a scenario."""

    scenario_id: str
    safe_points: List[SafePointDetail] = Field(default_factory=list)
    total_shelter_capacity: int
    highest_elevation_m: float

