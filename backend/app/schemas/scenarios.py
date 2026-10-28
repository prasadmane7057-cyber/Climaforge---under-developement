"""Scenario and Audit Log schemas for CLIMAFORGE Milestone 1.

All models enforce strict type validation and explicit labeling
for synthetic / illustrative demo datasets.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.contracts import GraphNode, Intervention


class ScenarioZoneItem(BaseModel):
    """Zone telemetry and synthetic risk attributes in a scenario context."""

    zone_id: str = Field(..., description="Unique zone identifier")
    name: str = Field(..., description="Human-readable zone name")
    rainfall_mm: float = Field(..., ge=0.0, description="Precipitation depth in mm")
    elevation_m: float = Field(..., description="Mean ground elevation in meters")
    soil_saturation_index: float = Field(
        ..., ge=0.0, le=1.0, description="Soil saturation ratio [0.0 - 1.0]"
    )
    drainage_capacity_cms: float = Field(
        ..., ge=0.0, description="Drainage capacity in cubic meters/sec"
    )
    critical_infrastructure_count: int = Field(
        0, ge=0, description="Number of critical infrastructure assets"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Synthetic illustrative risk index [0.0 - 1.0]",
    )
    severity: str = Field(
        ..., description="Risk tier: 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'"
    )
    is_hotspot: bool = Field(
        ..., description="True if zone exceeds threshold for downstream intervention"
    )
    data_provenance: str = Field(
        default="SYNTHETIC_SCENARIO_PROTOTYPE",
        description="Origin marker for audit and provenance",
    )
    centroid_lat: Optional[float] = Field(
        None, ge=-90.0, le=90.0, description="Illustrative centroid latitude"
    )
    centroid_lon: Optional[float] = Field(
        None, ge=-180.0, le=180.0, description="Illustrative centroid longitude"
    )
    schematic_x: int = Field(
        ..., ge=0, le=100, description="Normalized X coordinate on schematic map (0-100%)"
    )
    schematic_y: int = Field(
        ..., ge=0, le=100, description="Normalized Y coordinate on schematic map (0-100%)"
    )


class ScenarioSummaryItem(BaseModel):
    """Concise scenario descriptor for the scenario selector."""

    scenario_id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Scenario display name")
    description: str = Field(..., description="Brief scenario narrative")
    severity: str = Field(..., description="'NOMINAL', 'ELEVATED', 'CRITICAL'")
    zone_count: int = Field(..., ge=1, description="Number of evaluated zones")
    hotspot_count: int = Field(..., ge=0, description="Number of identified hotspot zones")
    highest_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Peak zone risk score in scenario"
    )
    highest_risk_zone_name: str = Field(
        ..., description="Name of zone with peak risk score"
    )
    critical_infrastructure_count: int = Field(
        ..., ge=0, description="Total critical assets in scenario"
    )
    data_label: str = Field(
        default="SYNTHETIC / ILLUSTRATIVE DATA ONLY",
        description="Mandatory prototype disclaimer label",
    )


class ScenarioDetail(ScenarioSummaryItem):
    """Comprehensive scenario dataset including zones, nodes, and interventions."""

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Scenario definition timestamp",
    )
    analysis_engine_status: str = Field(
        default="PENDING_MILESTONE_2",
        description="Status flag indicating Algorithms 0–5 are scheduled for Milestone 2",
    )
    zones: List[ScenarioZoneItem] = Field(
        default_factory=list, description="Array of zones evaluated in scenario"
    )
    nodes: List[GraphNode] = Field(
        default_factory=list, description="Infrastructure assets in scenario"
    )
    interventions: List[Intervention] = Field(
        default_factory=list, description="Candidate mitigation actions"
    )
    safe_points: List[Dict[str, Any]] = Field(
        default_factory=list, description="Safe shelters and evacuation points"
    )


class AuditEvent(BaseModel):
    """An authentically recorded UI or backend operational event."""

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC event occurrence timestamp",
    )
    event_type: str = Field(
        ...,
        description="Category: 'SYSTEM_BOOT', 'HEALTH_CHECK', 'SCENARIO_LOADED', 'USER_NAVIGATION', 'ACTION_ATTEMPT'",
    )
    source: str = Field(..., description="'BACKEND' or 'FRONTEND'")
    description: str = Field(..., description="Human-readable event summary")
    details: Dict[str, str] = Field(
        default_factory=dict, description="Key-value event metadata"
    )


class CreateAuditEventRequest(BaseModel):
    """Payload to append a verified client event into the audit log."""

    event_type: str
    description: str
    details: Dict[str, str] = Field(default_factory=dict)
