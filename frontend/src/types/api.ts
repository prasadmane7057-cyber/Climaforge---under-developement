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
export type RiskSeverity = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

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
