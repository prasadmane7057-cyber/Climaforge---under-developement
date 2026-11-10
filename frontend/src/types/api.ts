/**
 * API types and domain contract definitions for CLIMAFORGE.
 */

export interface SubsystemStatusMap {
  [key: string]: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'down';
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  subsystems: SubsystemStatusMap;
  disclaimer: string;
}

export type UrgencyLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type IncidentStatus = 'NOT_SENT' | 'QUEUED' | 'ACKNOWLEDGED' | 'RESOLVED';
export type AdvisoryStatus = 'ADVISORY_ACCEPTED' | 'FALLBACK' | 'DISABLED';
export type RiskSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'MODERATE' | 'DATA_INSUFFICIENT';

export interface FactorBreakdownItem {
  factor_name: string;
  factor_value: number;
  effective_weight: number;
  weighted_contribution: number;
}

export interface ZoneAnalysisResult {
  zone_id: string;
  name: string;
  score: number | null;
  raw_score?: number | null;
  normalized_score: number | null;
  severity: RiskSeverity;
  dominant_cause: string | null;
  breakdown: Record<string, FactorBreakdownItem>;
  flags: string[];
  status: string;
  is_scorable: boolean;
  is_hotspot: boolean;
}

export interface ExposureAnalysisResult {
  zone_id: string;
  name: string;
  impact_score: number | null;
  status: string;
  flags: string[];
  population_score: number | null;
  infrastructure_score: number | null;
  road_score: number | null;
  emergency_score: number | null;
  raw_counts: {
    population?: number | null;
    critical_infra?: number | null;
    road_length_km?: number | null;
    emergency_routes?: number | null;
  };
  effective_weights?: Record<string, number>;
}

export interface ConsequenceNodeData {
  id: string;
  label: string;
  seed: boolean;
  f: number;
  pop: number;
  infra: number;
  emerg: number;
  c: number;
  category: string;
}

export interface ConsequenceEdgeData {
  source: string;
  target: string;
  s: number;
  dependency_type: string;
}

export interface ConsequenceGraphData {
  node_count: number;
  edge_count: number;
  nodes: ConsequenceNodeData[];
  edges: ConsequenceEdgeData[];
}

export interface CycleResolutionLog {
  cycle: string[];
  removed_edge: string[];
  strength: number;
  reason: string;
}

export interface NodeStateItem {
  node_id: string;
  label: string;
  category: string;
  risk_p: number;
  vulnerability_f: number;
  consequence_c: number;
  state: 'FAILING' | 'WATCH' | 'SAFE';
  strongest_incoming_predecessor?: string | null;
  strongest_dependency_strength?: number;
}

export interface CascadeAnalysisResult {
  seed_node: string;
  seed_risk: number;
  node_risks: Record<string, number>;
  node_states: Record<string, NodeStateItem>;
  failing_nodes: string[];
  cascade_chain: string[];
  cascade_length: number;
  cascade_risk: number;
  tau_applied: number;
  cycle_logs: CycleResolutionLog[];
  topological_order: string[];
}

export interface CriticalNodeItem {
  rank: number;
  node_id: string;
  label: string;
  category: string;
  criticality_score: number;
  raw_features: Record<string, number>;
  scaled_features: Record<string, number>;
  downstream_impact: number;
  direct_risk: number;
  dependency_count: number;
}

export interface CriticalNodesResult {
  critical_node: string | null;
  critical_node_details?: CriticalNodeItem | null;
  ranked_nodes: CriticalNodeItem[];
  scores: Record<string, number>;
  weights_applied: Record<string, number>;
  max_factors: Record<string, number>;
}

export interface BreakPointItem {
  rank: number;
  intervention_id: string;
  action: string;
  target_node: string;
  mitigation_m: number;
  required_resources: Record<string, number>;
  cost_usd: number;
  lead_time_minutes: number;
  baseline_cascade_risk: number;
  mitigated_cascade_risk: number;
  impact_reduction_abs: number;
  impact_reduction_rel: number;
  impact_reduction_pct: number;
  baseline_cascade_length: number;
  mitigated_cascade_length: number;
  cascade_length_delta: number;
  mitigated_cascade_chain: string[];
  surviving_nodes: string[];
  target_node_risk_before: number;
  target_node_risk_after: number;
  target_node_exists: boolean;
}

export interface BreakPointsResult {
  baseline: {
    cascade_risk: number;
    cascade_length: number;
    cascade_chain: string[];
    failing_nodes: string[];
    node_risks: Record<string, number>;
  };
  best_break_point?: BreakPointItem | null;
  ranked_break_points: BreakPointItem[];
  evaluated_action_count: number;
}

// =====================================================================
// Milestone 4: Resource Allocation, Intervention Ranking, What-If,
// Alternative Comparison, Decision Card (Algorithms 8, 10–13)
// =====================================================================

export interface UnmetDemandItem {
  zone_id: string;
  resource_type: string;
  needed: number;
  granted: number;
  status: string; // "UNAVAILABLE" | "PARTIAL"
}

export interface ResourceAllocationResult {
  priority_scores: Record<string, number>;
  zone_allocation_order: string[];
  zone_budgets: Record<string, Record<string, number>>;
  unmet_demand: UnmetDemandItem[];
  remaining_inventory: Record<string, number>;
  status: string;
}

export interface InterventionMeasures {
  risk_reduction: number;
  cascade_reduction: number;
  population_protection: number;
  emergency_protection: number;
  resource_cost: number;
  baseline_cascade_risk: number;
  post_cascade_risk: number;
  baseline_cascade_length: number;
  post_cascade_length: number;
  baseline_p_pop: number;
  post_p_pop: number;
  baseline_p_emerg: number;
  post_p_emerg: number;
}

export interface FeasibleIntervention {
  intervention_id: string;
  action: string;
  name: string;
  target_node: string;
  required_resources: Record<string, number>;
  score: number;
  measures: InterventionMeasures;
  nugen_agreement: boolean | null;
  cost_usd: number | null;
  lead_time_minutes: number | null;
}

export interface InfeasibleIntervention {
  intervention_id: string;
  action: string;
  name: string;
  required_resources: Record<string, number>;
  blockers: string[];
}

export interface InterventionRankingResult {
  feasible: FeasibleIntervention[];
  infeasible: InfeasibleIntervention[];
  top_action: FeasibleIntervention | null;
  nugen_recommendation: Record<string, unknown> | null;
  nugen_agreement: boolean | null;
  baseline_simulation: Record<string, unknown> | null;
}

export interface WhatIfMeasures {
  impact_index: number;
  cascade_length: number;
  population_risk: number;
  infrastructure_risk: number;
  emergency_delay: number;
}

export interface WhatIfReduction {
  absolute: number;
  relative: number;
}

export interface WhatIfAnalysisResult {
  before: WhatIfMeasures;
  after: WhatIfMeasures;
  reductions: Record<string, WhatIfReduction>;
  intervention_applied: Record<string, unknown> | null;
}

export interface ComparisonRow {
  intervention_id: string;
  action_name: string;
  score: number;
  resource_cost: number;
  impact_index: number;
  cascade_length: number;
  population_risk: number;
  infrastructure_risk: number;
  emergency_delay: number;
  population_saved: number;
  infrastructure_protected: number;
}

export interface AlternativeComparisonResult {
  no_action_baseline: ComparisonRow;
  rows: ComparisonRow[];
  top_k: number;
  alternatives_count: number;
}

export interface RejectedCandidate {
  intervention_id: string;
  blockers: string[];
}

export interface DecisionCardResult {
  status: 'FEASIBLE' | 'NO_FEASIBLE_INTERVENTION';
  priority: string;
  zone_id: string;
  target_node: string | null;
  action: string | null;
  intervention_id: string | null;
  required_resources: Record<string, number>;
  reason: string;
  expected_impact: {
    before: WhatIfMeasures;
    after: WhatIfMeasures;
    reductions: Record<string, WhatIfReduction>;
  } | null;
  modelled_relative_change: number | null;
  quality_flags: string[];
  ai_status: 'MOCK' | 'FALLBACK' | 'LIVE' | 'DISABLED' | string;
  nugen_advisory_status?: AdvisoryStatus | string;
  nugen_recommendation: string | null;
  nugen_agreement: boolean | null;
  human_review_warning: string;
  run_id: string;
  blockers: string[];
  rejected_candidates: RejectedCandidate[];
}

export interface ScenarioAnalysisResponse {
  scenario_id: string;
  scenario_name: string;
  execution_timestamp: string;
  spec_version: string;
  data_label: string;
  pipeline_status: 'SUCCESS' | 'MONITORING_ONLY' | 'PARTIAL_DATA' | 'DATA_INSUFFICIENT' | string;
  is_monitoring_only: boolean;
  hotspot_threshold_applied: number;
  zone_count: number;
  scorable_zone_count: number;
  insufficient_zone_count: number;
  hotspot_count: number;
  highest_risk_score: number;
  highest_risk_zone_name: string;
  executed_algorithms: string[];
  zones: ZoneAnalysisResult[];
  hotspots: ZoneAnalysisResult[];
  exposure_results: ExposureAnalysisResult[];
  exposure_status?: string | null;
  cascade_status?: 'SUCCESS' | 'SKIPPED_MONITORING_ONLY' | string | null;
  consequence_graph?: ConsequenceGraphData | null;
  cascade_analysis?: CascadeAnalysisResult | null;
  critical_nodes?: CriticalNodesResult | null;
  break_points?: BreakPointsResult | null;
  // Milestone 4
  resource_allocation?: ResourceAllocationResult | null;
  intervention_ranking?: InterventionRankingResult | null;
  what_if_analysis?: WhatIfAnalysisResult | null;
  alternative_comparison?: AlternativeComparisonResult | null;
  decision_card?: DecisionCardResult | null;
  data_quality_flags: string[];
}

export interface ZoneInput {
  zone_id: string;
  name: string;
  area_sq_km: number;
  population: number;
  elevation_m: number;
  rainfall_mm: number;
  drainage_capacity_cms: number;
  soil_saturation_index: number;
  critical_infrastructure_count: number;
  river_proximity_m?: number | null;
}

export interface GraphNode {
  node_id: string;
  zone_id: string;
  name: string;
  node_type: string;
  baseline_capacity: number;
  current_operational_ratio: number;
  flood_threshold_m: number;
  criticality_weight: number;
  recovery_latency_hours?: number | null;
}

export interface Intervention {
  intervention_id: string;
  name: string;
  target_zone_id: string;
  target_node_id?: string | null;
  intervention_type: string;
  required_resources: Record<string, number>;
  cost_estimate_usd: number;
  lead_time_minutes: number;
  risk_reduction_factor: number;
}

export interface DecisionCard {
  card_id: string;
  scenario_id: string;
  generated_at: string;
  headline: string;
  primary_action_ids: string[];
  total_estimated_cost_usd: number;
  projected_impact: string;
  nugen_advisory_status: AdvisoryStatus;
  nugen_rationale?: string | null;
  sign_off_status: string;
}

export interface IncidentRecord {
  incident_id: string;
  reported_at: string;
  zone_id: string;
  latitude?: number | null;
  longitude?: number | null;
  incident_type: string;
  urgency: UrgencyLevel;
  status: IncidentStatus;
  description: string;
}

export interface ScenarioZoneItem {
  zone_id: string;
  name: string;
  rainfall_mm: number;
  elevation_m: number;
  soil_saturation_index: number;
  drainage_capacity_cms: number;
  critical_infrastructure_count: number;
  population?: number;
  risk_score: number;
  severity: RiskSeverity;
  is_hotspot: boolean;
  data_provenance: string;
  centroid_lat?: number | null;
  centroid_lon?: number | null;
  schematic_x: number;
  schematic_y: number;
}

export interface ScenarioSummaryItem {
  scenario_id: string;
  name: string;
  description: string;
  severity: 'NOMINAL' | 'ELEVATED' | 'CRITICAL';
  zone_count: number;
  hotspot_count: number;
  highest_risk_score: number;
  highest_risk_zone_name: string;
  critical_infrastructure_count: number;
  data_label: string;
}

export interface SafePointItem {
  safe_point_id: string;
  name: string;
  zone_id: string;
  capacity_persons: number;
  elevation_m: number;
  label: string;
}

export interface ScenarioDetail extends ScenarioSummaryItem {
  generated_at: string;
  analysis_engine_status: string;
  zones: ScenarioZoneItem[];
  nodes: GraphNode[];
  interventions: Intervention[];
  safe_points: SafePointItem[];
}

export interface AuditEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  source: 'BACKEND' | 'FRONTEND';
  description: string;
  details: Record<string, string>;
}

export interface FloodPredictionRequest {
  prcp_mm: number;
  tmax_c: number;
  tmin_c: number;
  snow_mm: number;
  prcp_lag1_mm: number;
  prcp_rolling_3d_mean_mm: number;
  prcp_rolling_7d_mean_mm: number;
  prcp_rolling_14d_mean_mm: number;
}

export interface FloodPredictionResponse {
  predicted_risk_class: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  class_probabilities: Record<string, number>;
  model_version: string;
}

export interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatbotResponse {
  answer: string;
  source: 'LLM' | 'DETERMINISTIC_FALLBACK' | 'MOCK';
  mode: 'grounded_llm' | 'deterministic_fallback' | 'mock_advisory';
  scenario_id: string;
  context_available: boolean;
  is_advisory?: boolean;
  advisory_status?: string | null;
}

export interface NugenGatewayStatus {
  enabled: boolean;
  mock_mode: boolean;
  provider: string;
  active_mode: string;
  timeout_seconds: number;
  advisory_label: string;
  authority: string;
  disclaimer: string;
}

export interface CitizenAlertItem {
  alert_id: string;
  scenario_id: string;
  zone_id: string;
  zone_name: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'DATA_INSUFFICIENT';
  risk_score: number;
  dominant_cause: string;
  headline: string;
  description: string;
  action_recommendation: string;
  is_simulated: boolean;
  is_live_confirmed: boolean;
  disclaimer: string;
  generated_at: string;
}

export interface ScenarioAlertsResponse {
  scenario_id: string;
  scenario_name: string;
  generated_at: string;
  alerts: CitizenAlertItem[];
  highest_severity: string;
  affected_zone_count: number;
  is_simulated: boolean;
  is_live_confirmed: boolean;
  disclaimer: string;
}

export interface RouteWaypointItem {
  node_id: string;
  name: string;
  zone_id: string;
  node_type: string;
  safety_status: 'SAFE' | 'WATCH' | 'FAILING';
  cumulative_distance_km: number;
  cumulative_time_minutes: number;
  instruction: string;
}

export interface HazardAvoidanceDetail {
  node_id: string;
  name: string;
  reason: string;
  risk_probability: number;
  failure_state: 'FAILING' | 'WATCH' | 'SAFE';
}

export interface EvacuationRouteRequest {
  origin_zone_id: string;
  destination_safe_point_id?: string;
  avoid_watch_nodes?: boolean;
}

export interface EvacuationRouteResponse {
  route_id: string;
  scenario_id: string;
  origin_zone_id: string;
  origin_zone_name: string;
  destination_safe_point_id?: string;
  destination_safe_point_name?: string;
  destination_zone_id?: string;
  status: 'CONFIRMED_SAFE' | 'BLOCKED' | 'NO_PATH_AVAILABLE' | 'ERROR';
  path_node_ids: string[];
  waypoints: RouteWaypointItem[];
  distance_km?: number | null;
  estimated_transit_minutes?: number | null;
  avoided_hazard_nodes: string[];
  avoided_node_details: HazardAvoidanceDetail[];
  step_by_step_instructions: string[];
  is_live_confirmed: boolean;
  is_simulated: boolean;
  disclaimer: string;
  generated_at: string;
  error_message?: string | null;
}

export interface SafePointDetail {
  safe_point_id: string;
  name: string;
  zone_id: string;
  capacity_persons: number;
  elevation_m: number;
  label: string;
  is_operational: boolean;
  amenities: string[];
}

export interface ScenarioSafePointsResponse {
  scenario_id: string;
  safe_points: SafePointDetail[];
  total_shelter_capacity: number;
  highest_elevation_m: number;
}

// Milestone 7: Offline Resilience and SOS Outbox Contracts
export interface IncidentSyncRequest {
  incidents: IncidentRecord[];
}

export interface IncidentSyncResponse {
  scenario_id: string;
  synced_incident_ids: string[];
  duplicate_incident_ids: string[];
  rejected_incident_ids: string[];
  total_received: number;
  total_synced: number;
  total_duplicates: number;
  acknowledged_at: string;
  status: 'ACKNOWLEDGED' | 'PARTIAL_SUCCESS' | 'NO_NEW_DATA';
  disclaimer: string;
}

export interface CachedScenarioBundle {
  scenario_id: string;
  scenario_name: string;
  cached_at: string;
  alerts: CitizenAlertItem[];
  safe_points: SafePointDetail[];
}

