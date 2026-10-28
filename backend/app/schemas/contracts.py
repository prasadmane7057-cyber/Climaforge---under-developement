"""Domain schemas and provisional Pydantic contracts for CLIMAFORGE.

Milestone 0 provides typed contracts for:
- ZoneInput
- GraphNode
- Intervention
- DecisionCard
- IncidentRecord
Additional domain schemas:
- ZoneRisk, ExposureResult, GraphEdge, CascadeResult,
  ResourceInventory, SimulationResult, HazardReport, RoutePlan

Field confirmation statuses against source documents
(CLIMAFORGE_PRD_System_Architecture.docx & CLIMAFORGE_Algorithm_Report_v2.pdf)
are explicitly annotated in docstrings and Field descriptions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class UrgencyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    NOT_SENT = "NOT_SENT"
    QUEUED = "QUEUED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AdvisoryStatus(str, Enum):
    ADVISORY_ACCEPTED = "ADVISORY_ACCEPTED"
    FALLBACK = "FALLBACK"
    DISABLED = "DISABLED"


# =====================================================================
# 1. ZoneInput
# =====================================================================
class ZoneInput(BaseModel):
    """Input telemetry and geographic attributes for an analyzed zone.

    NOTE FOR CONFIRMATION:
    - rainfall_forecast_hours: Confirm whether Alg 0 uses fixed 3h/6h/12h intervals.
    - water_level_gauge_m: Confirm if sensor telemetry is ingested here or via
      a distinct RiverGauge stream.
    - soil_saturation_index: Confirm if satellite soil moisture index range is [0.0, 1.0].
    """

    zone_id: str = Field(
        ...,
        description="Unique zone identifier (e.g., 'ZONE-001')",
        min_length=1,
    )
    name: str = Field(..., description="Human-readable zone name")
    area_sq_km: float = Field(..., gt=0.0, description="Zone area in square kilometers")
    population: int = Field(..., ge=0, description="Resident population in zone")
    elevation_m: float = Field(
        ..., description="Mean elevation above sea level in meters"
    )
    rainfall_mm: float = Field(
        ..., ge=0.0, description="Current or cumulative precipitation in mm"
    )
    drainage_capacity_cms: float = Field(
        ..., ge=0.0, description="Drainage throughput capacity in cubic meters per second"
    )
    soil_saturation_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Soil moisture saturation index [0.0 to 1.0]. Requires confirmation of raw scale.",
    )
    critical_infrastructure_count: int = Field(
        0, ge=0, description="Number of critical assets located within the zone"
    )
    river_proximity_m: Optional[float] = Field(
        None,
        ge=0.0,
        description="Distance to nearest major watercourse in meters. Field requires confirmation.",
    )


# =====================================================================
# 2. GraphNode
# =====================================================================
class GraphNode(BaseModel):
    """Node representing an infrastructure asset in the consequence dependency graph.

    NOTE FOR CONFIRMATION:
    - node_type: Confirm full taxonomy of infrastructure types from PRD.
    - recovery_latency_hours: Confirm if time-to-restore is tracked at node or edge.
    - flood_threshold_m: Water inundation height at which failure is triggered.
    """

    node_id: str = Field(
        ..., description="Unique node identifier (e.g., 'NODE-SUBSTATION-01')"
    )
    zone_id: str = Field(..., description="Associated ZoneInput.zone_id")
    name: str = Field(..., description="Infrastructure asset name")
    node_type: str = Field(
        ...,
        description="Infrastructure classification (e.g., 'substation', 'hospital', 'water_plant', 'bridge', 'shelter')",
    )
    baseline_capacity: float = Field(
        ..., gt=0.0, description="Nominal operating capacity units"
    )
    current_operational_ratio: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Operating ratio [0.0 = completely failed, 1.0 = fully operational]",
    )
    flood_threshold_m: float = Field(
        ...,
        ge=0.0,
        description="Critical flood inundation depth in meters that initiates asset failure",
    )
    criticality_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relative system priority weight [0.0 to 1.0]",
    )
    recovery_latency_hours: Optional[float] = Field(
        None,
        ge=0.0,
        description="Estimated restoration downtime in hours. Pending confirmation.",
    )


# =====================================================================
# 3. Intervention
# =====================================================================
class Intervention(BaseModel):
    """Action evaluated to break failure cascades and protect assets.

    NOTE FOR CONFIRMATION:
    - intervention_type: Confirm standardized action taxonomy in Alg 10.
    - required_resources: Confirm if quantities match ResourceInventory catalog keys.
    """

    intervention_id: str = Field(
        ..., description="Unique intervention identifier (e.g., 'INTV-BARRIER-01')"
    )
    name: str = Field(..., description="Intervention label")
    target_zone_id: str = Field(..., description="Zone where intervention takes place")
    target_node_id: Optional[str] = Field(
        None, description="Specific infrastructure node protected, if applicable"
    )
    intervention_type: str = Field(
        ...,
        description="Action category (e.g., 'deploy_barriers', 'mobile_pumps', 'traffic_diversion')",
    )
    required_resources: Dict[str, int] = Field(
        default_factory=dict,
        description="Resource demands mapping resource SKU/type to required integer quantity",
    )
    cost_estimate_usd: float = Field(
        ..., ge=0.0, description="Estimated monetary execution cost"
    )
    lead_time_minutes: int = Field(
        ..., ge=0, description="Deployment lead time from dispatch to operational state"
    )
    risk_reduction_factor: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Expected attenuation of failure probability [0.0 to 1.0]",
    )

    @field_validator("required_resources")
    @classmethod
    def validate_resource_demands(cls, v: Dict[str, int]) -> Dict[str, int]:
        for k, qty in v.items():
            if qty < 0:
                raise ValueError(f"Resource quantity for '{k}' must be non-negative")
        return v


# =====================================================================
# 4. DecisionCard
# =====================================================================
class DecisionCard(BaseModel):
    """Authoritative operational summary synthesized for emergency command.

    NOTE FOR CONFIRMATION:
    - sign_off_role: Confirm required sign-off hierarchy (Incident Commander, Chief Logistics Officer).
    - fallback_reason: Field populated whenever Nugen is timed out, disabled, or invalid.
    """

    card_id: str = Field(
        ..., description="Unique decision card reference (e.g., 'DC-20261028-001')"
    )
    scenario_id: str = Field(..., description="Active simulation scenario ID")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of card creation",
    )
    headline: str = Field(
        ..., description="Summary operational action directive headline"
    )
    primary_action_ids: List[str] = Field(
        ..., description="Ordered list of recommended Intervention.intervention_id values"
    )
    total_estimated_cost_usd: float = Field(
        ..., ge=0.0, description="Sum of estimated costs for chosen interventions"
    )
    projected_impact: str = Field(
        ..., description="Deterministic projected risk mitigation and cascade arrest description"
    )
    nugen_advisory_status: AdvisoryStatus = Field(
        default=AdvisoryStatus.DISABLED,
        description="Advisory AI layer execution status",
    )
    nugen_rationale: Optional[str] = Field(
        None,
        description="Nugen advisory text if available. Note: Nugen cannot override calculations.",
    )
    sign_off_status: str = Field(
        default="PENDING_REVIEW",
        description="Status: 'PENDING_REVIEW', 'COMMAND_APPROVED', 'REJECTED'",
    )


# =====================================================================
# 5. IncidentRecord
# =====================================================================
class IncidentRecord(BaseModel):
    """Field incident or citizen SOS telemetry record.

    NOTE FOR CONFIRMATION:
    - citizen_phone_hash: Confirm privacy hashing requirement for PII.
    - offline_sync_id: Confirm client-side UUID generation for IndexedDB synchronization.
    """

    incident_id: str = Field(..., description="Unique incident ID or client outbox UUID")
    reported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC time incident was logged",
    )
    zone_id: str = Field(..., description="Associated geographic zone")
    latitude: Optional[float] = Field(
        None, ge=-90.0, le=90.0, description="GPS latitude coordinates"
    )
    longitude: Optional[float] = Field(
        None, ge=-180.0, le=180.0, description="GPS longitude coordinates"
    )
    incident_type: str = Field(
        ...,
        description="Category: 'RISING_WATER', 'MEDICAL_EMERGENCY', 'STRANDED_PERSONS', 'ROAD_BLOCKED'",
    )
    urgency: UrgencyLevel = Field(
        default=UrgencyLevel.MEDIUM, description="Urgency priority"
    )
    status: IncidentStatus = Field(
        default=IncidentStatus.NOT_SENT,
        description="Sync status. Must remain NOT_SENT until server acknowledgement.",
    )
    description: str = Field(
        ..., min_length=1, description="Citizen or operator observation text"
    )


# =====================================================================
# Additional Domain Schemas from Master Specification
# =====================================================================
class ZoneRisk(BaseModel):
    """Deterministic output for Algorithm 1 / Zone Risk calculation."""

    zone_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    classification: str = Field(
        ..., description="'LOW', 'MODERATE', 'HIGH', 'CRITICAL'"
    )
    is_hotspot: bool = Field(..., description="Flag indicating downstream analysis priority")
    data_quality_flag: str = Field(
        default="COMPLETE",
        description="'COMPLETE', 'PARTIAL_RESCALED', 'DATA_INSUFFICIENT'",
    )


class ExposureResult(BaseModel):
    """Deterministic output for Algorithm 2 / Exposure calculation."""

    zone_id: str
    population_exposed: int = Field(..., ge=0)
    infrastructure_value_at_risk_usd: float = Field(..., ge=0.0)
    critical_assets_exposed: List[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    """Directed dependency link between two GraphNode instances."""

    edge_id: str
    source_node_id: str
    target_node_id: str
    dependency_type: str = Field(
        ..., description="'power_feed', 'water_supply', 'physical_access', 'communications'"
    )
    failure_propagation_probability: float = Field(..., ge=0.0, le=1.0)


class CascadeResult(BaseModel):
    """Output from Algorithm 6-9 cascade simulation."""

    scenario_id: str
    initial_failed_node_ids: List[str]
    cascade_failed_node_ids: List[str]
    critical_node_ids: List[str]
    cascade_depth: int = Field(..., ge=0)


class ResourceInventory(BaseModel):
    """Depot resource stock for feasibility checks in Algorithm 10."""

    resource_id: str
    name: str
    total_quantity: int = Field(..., ge=0)
    allocated_quantity: int = Field(0, ge=0)
    depot_zone_id: str


class SimulationResult(BaseModel):
    """Shared output schema for simulation before/after comparisons."""

    simulation_id: str
    baseline_cascade_impact: float
    mitigated_cascade_impact: float
    impact_reduction_percentage: float = Field(..., ge=0.0, le=100.0)
    surviving_nodes: List[str]


class HazardReport(BaseModel):
    """Citizen or sensor report for Algorithm 0 validation."""

    report_id: str
    zone_id: str
    source: str = Field(..., description="'sensor', 'citizen_sms', 'drone_feed'")
    water_depth_cm: float = Field(..., ge=0.0)
    verified: bool = False


class RoutePlan(BaseModel):
    """Evacuation routing output. Confirmed safe route segments only."""

    route_id: str
    origin_zone_id: str
    destination_safe_point_id: str
    path_node_ids: List[str]
    is_live_confirmed: bool = Field(
        False, description="Cached routes must not be claimed live-confirmed safe without live telemetry."
    )
    estimated_transit_minutes: float = Field(..., gt=0.0)
