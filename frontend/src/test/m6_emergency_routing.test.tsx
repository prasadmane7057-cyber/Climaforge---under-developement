import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EmergencyChatbotTab } from '../components/EmergencyChatbotTab';
import { RiskMapTab } from '../components/RiskMapTab';
import * as api from '../services/api';
import type {
  ScenarioAlertsResponse,
  ScenarioSafePointsResponse,
  EvacuationRouteResponse,
  ScenarioDetail,
} from '../types/api';

describe('Milestone 6: Emergency Alerts & Evacuation Routing UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockAlertsResponse: ScenarioAlertsResponse = {
    scenario_id: 'scenario-flash-flood',
    scenario_name: 'Flash Flood Emergency',
    generated_at: new Date().toISOString(),
    highest_severity: 'CRITICAL',
    affected_zone_count: 2,
    is_simulated: true,
    is_live_confirmed: false,
    disclaimer: 'SIMULATED / ILLUSTRATIVE ALERTS ONLY.',
    alerts: [
      {
        alert_id: 'ALERT-001',
        scenario_id: 'scenario-flash-flood',
        zone_id: 'ZONE-001',
        zone_name: 'Riverside Industrial District',
        severity: 'CRITICAL',
        risk_score: 82.6,
        dominant_cause: 'Rainfall Inundation',
        headline: 'CRITICAL EVACUATION WARNING: Severe Inundation Threat in Riverside',
        description: 'Immediate pre-calamity warning for Riverside.',
        action_recommendation: 'Immediate evacuation required along safe corridors.',
        is_simulated: true,
        is_live_confirmed: false,
        disclaimer: 'SIMULATED / ILLUSTRATIVE ALERT ONLY.',
        generated_at: new Date().toISOString(),
      },
    ],
  };

  const mockSafePointsResponse: ScenarioSafePointsResponse = {
    scenario_id: 'scenario-flash-flood',
    total_shelter_capacity: 6700,
    highest_elevation_m: 26.0,
    safe_points: [
      {
        safe_point_id: 'SP-01',
        name: 'Highland Sports Arena Shelter',
        zone_id: 'ZONE-003',
        capacity_persons: 3000,
        elevation_m: 22.0,
        label: 'SYNTHETIC / ILLUSTRATIVE',
        is_operational: true,
        amenities: ['Emergency Shelter', 'Potable Water'],
      },
    ],
  };

  const mockSafeRouteResponse: EvacuationRouteResponse = {
    route_id: 'ROUTE-001',
    scenario_id: 'scenario-flash-flood',
    origin_zone_id: 'ZONE-001',
    origin_zone_name: 'Riverside Industrial District',
    destination_safe_point_id: 'SP-01',
    destination_safe_point_name: 'Highland Sports Arena Shelter',
    destination_zone_id: 'ZONE-003',
    status: 'CONFIRMED_SAFE',
    path_node_ids: ['ZONE-001', 'ROAD-PERIM-01', 'JUNCTION-NORTH-01', 'SP-01'],
    distance_km: 11.7,
    estimated_transit_minutes: 16.4,
    avoided_hazard_nodes: ['Road'],
    avoided_node_details: [
      {
        node_id: 'Road',
        name: 'Arterial Road Network',
        reason: 'Flooded infrastructure',
        risk_probability: 0.72,
        failure_state: 'FAILING',
      },
    ],
    step_by_step_instructions: [
      'Depart from Riverside Industrial District.',
      'Step 1: Divert onto Elevated Highland Ridge Perimeter Bypass (6.5 km).',
      'Step 2: Ascend to North Valley Staging Point (4.0 km).',
      'Step 3: Arrive safely at Highland Sports Arena Shelter (1.2 km).',
    ],
    waypoints: [],
    is_live_confirmed: false,
    is_simulated: true,
    disclaimer: 'SIMULATED / ILLUSTRATIVE EVACUATION ROUTE ONLY.',
    generated_at: new Date().toISOString(),
  };

  it('renders pre-calamity alerts with severity badge and dominant cause', async () => {
    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue(mockAlertsResponse);
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue(mockSafePointsResponse);

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/CRITICAL EVACUATION WARNING/i)).toBeTruthy();
    });

    expect(screen.getByText(/Rainfall Inundation/i)).toBeTruthy();
    expect(screen.getByText(/SIMULATED ALERTS ONLY/i)).toBeTruthy();
    expect(screen.getByText(/82.6\/100/i)).toBeTruthy();
  });

  it('plans a safe evacuation route and displays hazard avoidance and waypoints', async () => {
    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue(mockAlertsResponse);
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue(mockSafePointsResponse);
    const planSpy = vi.spyOn(api, 'requestEvacuationRoute').mockResolvedValue(mockSafeRouteResponse);

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/Find Safe Route/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/Find Safe Route/i));

    await waitFor(() => {
      expect(planSpy).toHaveBeenCalledWith('scenario-flash-flood', 'ZONE-001', undefined);
      expect(screen.getByText(/CONFIRMED SAFE \(SIMULATED\)/i)).toBeTruthy();
    });

    expect(screen.getByText(/11.7 km/i)).toBeTruthy();
    expect(screen.getByText(/~16.4 mins/i)).toBeTruthy();
    expect(screen.getByText(/Avoided 1 flooded\/failing infrastructure asset/i)).toBeTruthy();
    expect(screen.getByText(/Road/i)).toBeTruthy();
    expect(screen.getByText(/is_live_confirmed: false/i)).toBeTruthy();
  });

  it('displays blocked route error message and shelter-in-place instructions when route is impassable', async () => {
    const blockedRouteResponse: EvacuationRouteResponse = {
      route_id: 'ROUTE-BLOCKED',
      scenario_id: 'scenario-flash-flood',
      origin_zone_id: 'ZONE-001',
      origin_zone_name: 'Riverside Industrial District',
      status: 'BLOCKED',
      path_node_ids: [],
      waypoints: [],
      distance_km: null,
      estimated_transit_minutes: null,
      avoided_hazard_nodes: ['Road', 'ROAD-PERIM-01'],
      avoided_node_details: [],
      error_message: 'Candidate transit corridors are blocked by active flood inundation at: Road, ROAD-PERIM-01.',
      step_by_step_instructions: [
        'SHELTER IN PLACE: All safe evacuation corridors from this zone are currently impassable.',
        'Move immediately to the highest available floor.',
        'Await official rescue instructions.',
      ],
      is_live_confirmed: false,
      is_simulated: true,
      disclaimer: 'SIMULATED / ILLUSTRATIVE EVACUATION ROUTE ONLY.',
      generated_at: new Date().toISOString(),
    };

    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue(mockAlertsResponse);
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue(mockSafePointsResponse);
    vi.spyOn(api, 'requestEvacuationRoute').mockResolvedValue(blockedRouteResponse);

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/Find Safe Route/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/Find Safe Route/i));

    await waitFor(() => {
      expect(screen.getByText(/BLOCKED \/ IMPASSABLE \(NO ROUTE\)/i)).toBeTruthy();
    });

    expect(screen.getByText(/Candidate transit corridors are blocked/i)).toBeTruthy();
    expect(screen.getAllByText(/SHELTER IN PLACE/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Unavailable \(Route Blocked\)/i)).toBeTruthy();
    expect(screen.getByText(/Unavailable \(Shelter in Place\)/i)).toBeTruthy();
  });

  it('renders designated evacuation refuge and corridor in RiskMapTab', () => {
    const mockScenarioDetail: ScenarioDetail = {
      scenario_id: 'scenario-baseline',
      name: 'Baseline Monitoring Scenario',
      description: 'Standard baseline catchment scenario',
      severity: 'NOMINAL',
      zone_count: 1,
      hotspot_count: 0,
      data_label: 'SYNTHETIC / ILLUSTRATIVE',
      analysis_engine_status: 'COMPLETE',
      critical_infrastructure_count: 5,
      highest_risk_score: 24.5,
      highest_risk_zone_name: 'Harbor Basin',
      generated_at: new Date().toISOString(),
      zones: [
        {
          zone_id: 'ZONE-001',
          name: 'Riverside Industrial District',
          severity: 'LOW',
          risk_score: 18.5,
          is_hotspot: false,
          elevation_m: 4.5,
          rainfall_mm: 35.0,
          soil_saturation_index: 0.45,
          drainage_capacity_cms: 40.0,
          critical_infrastructure_count: 2,
          population: 15000,
          data_provenance: 'SYNTHETIC',
          schematic_x: 25,
          schematic_y: 40,
        },
      ],
      nodes: [],
      interventions: [],
      safe_points: [
        {
          safe_point_id: 'SP-01',
          name: 'Highland Sports Arena Shelter',
          zone_id: 'ZONE-001',
          capacity_persons: 3000,
          elevation_m: 22.0,
          label: 'SYNTHETIC / ILLUSTRATIVE',
        },
      ],
    };

    render(
      <RiskMapTab
        scenarioDetail={mockScenarioDetail}
        analysisResult={null}
        isLoadingScenario={false}
        isAnalyzing={false}
      />,
    );

    expect(screen.getByText(/Designated Evacuation Refuge/i)).toBeTruthy();
    expect(screen.getAllByText(/Highland Sports Arena Shelter/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Elevation: 22m/i)).toBeTruthy();
  });
});
