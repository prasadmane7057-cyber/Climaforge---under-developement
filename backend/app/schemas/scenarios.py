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
        le=100.0,
        description="Risk index [0.0 - 100.0]",
    )
    severity: str = Field(
        ..., description="Risk tier: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'"
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
    population: Optional[int] = Field(None, ge=0, description="Resident population in zone")
    water_level_m: Optional[float] = Field(None, ge=0.0, description="River stage / water level in meters")
    road_length_km: Optional[float] = Field(None, ge=0.0, description="Arterial road length in km")
    emergency_routes_count: Optional[int] = Field(None, ge=0, description="Count of designated emergency routes")
    dominant_cause: Optional[str] = Field(None, description="Dominant contributing hydrological factor")


class ScenarioSummaryItem(BaseModel):
    """Concise scenario descriptor for the scenario selector."""

    scenario_id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Scenario display name")
    description: str = Field(..., description="Brief scenario narrative")
    severity: str = Field(..., description="'NOMINAL', 'ELEVATED', 'CRITICAL'")
    zone_count: int = Field(..., ge=1, description="Number of evaluated zones")
    hotspot_count: int = Field(..., ge=0, description="Number of identified hotspot zones")
    highest_risk_score: float = Field(
        ..., ge=0.0, le=100.0, description="Peak zone risk score in scenario"
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


# =====================================================================
# Milestone 2: Deterministic Calculation Engine (Algorithms 0–3) Schemas
# =====================================================================
class ZoneAnalysisResult(BaseModel):
    """Calculated risk metrics for a single zone from Algorithms 0–1."""

    zone_id: str
    name: str
    score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Canonical 0-100 score")
    raw_score: Optional[float] = None
    normalized_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW, or DATA_INSUFFICIENT")
    dominant_cause: Optional[str] = None
    breakdown: Dict[str, Any] = Field(default_factory=dict)
    flags: List[str] = Field(default_factory=list)
    status: str
    is_scorable: bool
    is_hotspot: bool


class ExposureAnalysisResult(BaseModel):
    """Calculated impact and exposure metrics from Algorithm 3."""

    zone_id: str
    name: str
    impact_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Weighted composite ImpactScore [0.0 - 1.0]")
    status: str
    flags: List[str] = Field(default_factory=list)
    population_score: Optional[float] = None
    infrastructure_score: Optional[float] = None
    road_score: Optional[float] = None
    emergency_score: Optional[float] = None
    raw_counts: Dict[str, Any] = Field(default_factory=dict)
    effective_weights: Dict[str, float] = Field(default_factory=dict)


# =====================================================================
# Milestone 3: Consequence Graph & Cascade Analysis (Algorithms 4–7) Schemas
# =====================================================================
class ConsequenceNodeData(BaseModel):
    """Node attributes in the consequence dependency graph (Algorithm 4)."""

    id: str
    label: str
    seed: bool = False
    f: float = Field(..., ge=0.0, le=1.0, description="Failure probability / vulnerability")
    pop: float = Field(0.0, ge=0.0, le=1.0)
    infra: float = Field(0.0, ge=0.0, le=1.0)
    emerg: float = Field(0.0, ge=0.0, le=1.0)
    c: float = Field(0.0, ge=0.0, le=1.0, description="Consequence weight = mean(pop, infra, emerg)")
    category: str = "infrastructure"


class ConsequenceEdgeData(BaseModel):
    """Directed dependency link in the consequence graph (Algorithm 4)."""

    source: str
    target: str
    s: float = Field(..., ge=0.0, le=1.0, description="Dependency strength [0.0 - 1.0]")
    dependency_type: str = "dependency"


class ConsequenceGraphData(BaseModel):
    """Serialized network topology representation (Algorithm 4)."""

    node_count: int
    edge_count: int
    nodes: List[ConsequenceNodeData]
    edges: List[ConsequenceEdgeData]


class CycleResolutionLog(BaseModel):
    """Record of a deterministically broken cycle (Algorithm 5)."""

    cycle: List[str]
    removed_edge: List[str]
    strength: float
    reason: str


class CascadeAnalysisResult(BaseModel):
    """Calculated probability propagation and cascade metrics (Algorithm 5)."""

    seed_node: str
    seed_risk: float
    node_risks: Dict[str, float]
    node_states: Dict[str, Any] = Field(default_factory=dict)
    failing_nodes: List[str] = Field(default_factory=list)
    cascade_chain: List[str] = Field(default_factory=list)
    cascade_length: int = 0
    cascade_risk: float = Field(..., ge=0.0, le=1.0, description="Consequence-weighted CascadeRisk [0.0 - 1.0]")
    tau_applied: float = 0.30
    cycle_logs: List[CycleResolutionLog] = Field(default_factory=list)
    topological_order: List[str] = Field(default_factory=list)


class CriticalNodeItem(BaseModel):
    """Ranked candidate node with feature breakdown (Algorithm 6)."""

    rank: int
    node_id: str
    label: str
    category: str
    criticality_score: float = Field(..., ge=0.0, le=1.0)
    raw_features: Dict[str, float] = Field(default_factory=dict)
    scaled_features: Dict[str, float] = Field(default_factory=dict)
    downstream_impact: float
    direct_risk: float
    dependency_count: int


class CriticalNodesResult(BaseModel):
    """Critical node evaluation output (Algorithm 6)."""

    critical_node: Optional[str] = None
    critical_node_details: Optional[CriticalNodeItem] = None
    ranked_nodes: List[CriticalNodeItem] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)
    weights_applied: Dict[str, float] = Field(default_factory=dict)
    max_factors: Dict[str, float] = Field(default_factory=dict)


class BreakPointItem(BaseModel):
    """Evaluated catalogue-backed intervention action (Algorithm 7)."""

    rank: int
    intervention_id: str
    action: str
    target_node: str
    mitigation_m: float
    required_resources: Dict[str, int] = Field(default_factory=dict)
    cost_usd: float = 0.0
    lead_time_minutes: int = 0
    baseline_cascade_risk: float
    mitigated_cascade_risk: float
    impact_reduction_abs: float
    impact_reduction_rel: float
    impact_reduction_pct: float
    baseline_cascade_length: int
    mitigated_cascade_length: int
    cascade_length_delta: int
    mitigated_cascade_chain: List[str] = Field(default_factory=list)
    surviving_nodes: List[str] = Field(default_factory=list)
    target_node_risk_before: float = 0.0
    target_node_risk_after: float = 0.0
    target_node_exists: bool = True


class BreakPointsResult(BaseModel):
    """Break-point detection and simulation output (Algorithm 7)."""

    baseline: Dict[str, Any] = Field(default_factory=dict)
    best_break_point: Optional[BreakPointItem] = None
    ranked_break_points: List[BreakPointItem] = Field(default_factory=list)
    evaluated_action_count: int = 0


# =====================================================================
# Milestone 4: Resource Allocation, Intervention Ranking, What-If,
# Alternative Comparison, and Decision Card (Algorithms 8, 10–13)
# =====================================================================

class UnmetDemandItem(BaseModel):
    """A single resource shortfall record from Algorithm 8."""

    zone_id: str
    resource_type: str
    needed: int
    granted: int
    status: str  # "UNAVAILABLE" | "PARTIAL"


class ResourceAllocationResult(BaseModel):
    """Depot resource allocation output (Algorithm 8)."""

    priority_scores: Dict[str, float] = Field(default_factory=dict)
    zone_allocation_order: List[str] = Field(default_factory=list)
    zone_budgets: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    unmet_demand: List[UnmetDemandItem] = Field(default_factory=list)
    remaining_inventory: Dict[str, int] = Field(default_factory=dict)
    status: str = "SUCCESS"


class InterventionMeasures(BaseModel):
    """Sub-component score breakdown for a ranked intervention (Algorithm 10)."""

    risk_reduction: float
    cascade_reduction: float
    population_protection: float
    emergency_protection: float
    resource_cost: float
    baseline_cascade_risk: float
    post_cascade_risk: float
    baseline_cascade_length: int
    post_cascade_length: int
    baseline_p_pop: float
    post_p_pop: float
    baseline_p_emerg: float
    post_p_emerg: float


class FeasibleIntervention(BaseModel):
    """A feasible, scored intervention from Algorithm 10."""

    intervention_id: str
    action: str
    name: str
    target_node: str
    required_resources: Dict[str, int] = Field(default_factory=dict)
    score: float
    measures: InterventionMeasures
    nugen_agreement: Optional[bool] = None
    cost_usd: Optional[float] = None
    lead_time_minutes: Optional[int] = None


class InfeasibleIntervention(BaseModel):
    """An infeasible intervention with blocker reasons from Algorithm 10."""

    intervention_id: str
    action: str
    name: str
    required_resources: Dict[str, int] = Field(default_factory=dict)
    blockers: List[str] = Field(default_factory=list)


class InterventionRankingResult(BaseModel):
    """Intervention priority ranking output (Algorithm 10)."""

    feasible: List[FeasibleIntervention] = Field(default_factory=list)
    infeasible: List[InfeasibleIntervention] = Field(default_factory=list)
    top_action: Optional[FeasibleIntervention] = None
    nugen_recommendation: Optional[Dict[str, Any]] = None
    nugen_agreement: Optional[bool] = None
    baseline_simulation: Optional[Dict[str, Any]] = None


class WhatIfMeasures(BaseModel):
    """Five canonical measures extracted from a simulate() result (Algorithm 11)."""

    impact_index: float = Field(..., ge=0.0, le=1.0)
    cascade_length: int = Field(..., ge=0)
    population_risk: float = Field(..., ge=0.0, le=1.0)
    infrastructure_risk: float = Field(..., ge=0.0, le=1.0)
    emergency_delay: float = Field(..., ge=0.0, le=1.0)


class WhatIfAnalysisResult(BaseModel):
    """Before/after simulation results and reductions (Algorithm 11)."""

    before: WhatIfMeasures
    after: WhatIfMeasures
    reductions: Dict[str, Any] = Field(default_factory=dict)
    intervention_applied: Optional[Dict[str, Any]] = None


class ComparisonRow(BaseModel):
    """A single row in the alternative comparison table (Algorithm 12)."""

    intervention_id: str
    action_name: str
    score: float = 0.0
    resource_cost: float = 0.0
    impact_index: float
    cascade_length: int
    population_risk: float
    infrastructure_risk: float
    emergency_delay: float
    population_saved: float = 0.0
    infrastructure_protected: float = 0.0


class AlternativeComparisonResult(BaseModel):
    """Side-by-side comparison table (Algorithm 12)."""

    no_action_baseline: ComparisonRow
    rows: List[ComparisonRow] = Field(default_factory=list)
    top_k: int = 3
    alternatives_count: int = 0


class RejectedCandidate(BaseModel):
    """A candidate that failed final re-verification (Algorithm 13)."""

    intervention_id: str
    blockers: List[str] = Field(default_factory=list)


class DecisionCardResult(BaseModel):
    """Command Decision Card output (Algorithm 13)."""

    status: str  # "FEASIBLE" | "NO_FEASIBLE_INTERVENTION"
    priority: str
    zone_id: str
    target_node: Optional[str] = None
    action: Optional[str] = None
    intervention_id: Optional[str] = None
    required_resources: Dict[str, int] = Field(default_factory=dict)
    reason: str
    expected_impact: Optional[Dict[str, Any]] = None
    modelled_relative_change: Optional[float] = None
    quality_flags: List[str] = Field(default_factory=list)
    ai_status: str = "MOCK"
    nugen_recommendation: Optional[str] = None
    nugen_agreement: Optional[bool] = None
    human_review_warning: str
    run_id: str
    blockers: List[str] = Field(default_factory=list)
    rejected_candidates: List[RejectedCandidate] = Field(default_factory=list)


class ScenarioAnalysisResponse(BaseModel):
    """Complete response payload for a deterministic scenario risk run."""

    scenario_id: str
    scenario_name: str
    execution_timestamp: str
    spec_version: str
    data_label: str
    pipeline_status: str = Field(..., description="'SUCCESS', 'MONITORING_ONLY', 'PARTIAL_DATA', 'DATA_INSUFFICIENT'")
    is_monitoring_only: bool
    hotspot_threshold_applied: float
    zone_count: int
    scorable_zone_count: int
    insufficient_zone_count: int
    hotspot_count: int
    highest_risk_score: float
    highest_risk_zone_name: str
    executed_algorithms: List[str]
    zones: List[ZoneAnalysisResult]
    hotspots: List[ZoneAnalysisResult]
    exposure_results: List[ExposureAnalysisResult]
    exposure_status: Optional[str] = None
    cascade_status: Optional[str] = Field(None, description="'SUCCESS' or 'SKIPPED_MONITORING_ONLY'")
    consequence_graph: Optional[ConsequenceGraphData] = None
    cascade_analysis: Optional[CascadeAnalysisResult] = None
    critical_nodes: Optional[CriticalNodesResult] = None
    break_points: Optional[BreakPointsResult] = None
    # Milestone 4
    resource_allocation: Optional[ResourceAllocationResult] = None
    intervention_ranking: Optional[InterventionRankingResult] = None
    what_if_analysis: Optional[WhatIfAnalysisResult] = None
    alternative_comparison: Optional[AlternativeComparisonResult] = None
    decision_card: Optional[DecisionCardResult] = None
    data_quality_flags: List[str] = Field(default_factory=list)


