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
