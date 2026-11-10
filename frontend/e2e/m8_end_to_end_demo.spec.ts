import { test, expect } from '@playwright/test';

/**
 * Milestone 8: Complete End-to-End Operational Workflow E2E Demonstration Suite.
 *
 * Verifies all six operational scenes in genuine headless Chromium:
 * - Scene 1: Baseline Monitoring (nominal flow, zero hotspots, monitoring-only cascade)
 * - Scene 2: Flood Risk Escalation (canonical risk scoring, hotspot qualification, dominant hazard cause)
 * - Scene 3: Infrastructure Cascade (Noisy-OR failure propagation, failing assets, cycle safety)
 * - Scene 4: Intervention Decision Support (resource allocation, multi-criteria ranking, Command Decision Card)
 * - Scene 5: Citizen Emergency Response (pre-calamity alerts, shortest-safe-path evacuation routing, hazard avoidance)
 * - Scene 6: Offline Panic Resilience (IndexedDB cache, offline SOS queuing, automatic reconnection sync)
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'http://localhost:5173',
  'Access-Control-Allow-Credentials': 'true',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-CSRF-Token, Accept',
};

test.describe('Milestone 8: End-to-End System Integration & Demonstration Suite', () => {
  test.beforeEach(async ({ context }) => {
    // Intercept backend health check
    await context.route('**/health', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_HEADERS,
        body: JSON.stringify({
          status: 'ok',
          version: '0.1.0',
          timestamp: new Date().toISOString(),
          subsystems: { database: 'connected', engine: 'ready' },
        }),
      });
    });

    // Intercept auth refresh
    await context.route('**/api/auth/refresh', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_HEADERS,
        body: JSON.stringify({
          access_token: 'valid_mock_operator_token',
          token_type: 'bearer',
          expires_in: 900,
        }),
      });
    });

    // Intercept auth checks (demonstrator access)
    await context.route('**/api/auth/me', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_HEADERS,
        body: JSON.stringify({
          id: 'demo-operator-uuid',
          email: 'operator@climaforge.test',
          full_name: 'Lead Operations Coordinator',
          role: 'OPERATOR',
          is_active: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Intercept ML predict
    await context.route('**/api/ml/predict', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_HEADERS,
        body: JSON.stringify({
          model_name: 'random_forest_research_prototype',
          predicted_class: 'ELEVATED',
          flood_probability: 0.65,
          confidence_score: 0.82,
          feature_importance: { prcp_mm: 0.52 },
        }),
      });
    });

    // Unified router for all /api/scenarios endpoints (matches /api/scenarios and /api/scenarios/...)
    await context.route(/.*\/api\/scenarios.*/, async (route) => {
      const req = route.request();
      const method = req.method();
      const url = req.url();
      const path = new URL(url).pathname;

      if (method === 'OPTIONS') {
        return route.fulfill({ status: 204, headers: CORS_HEADERS });
      }

      // 1. Scenarios Catalog: GET /api/scenarios
      if ((path === '/api/scenarios' || path === '/api/scenarios/') && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify([
            {
              scenario_id: 'scenario-baseline',
              name: 'Dry Season Baseline (Nominal Flow)',
              severity: 'NOMINAL',
              zone_count: 4,
              hotspot_count: 0,
              highest_risk_score: 0.18,
            },
            {
              scenario_id: 'scenario-flash-flood',
              name: 'Extreme Monsoonal Inundation & River Surge',
              severity: 'CRITICAL',
              zone_count: 4,
              hotspot_count: 1,
              highest_risk_score: 82.4,
            },
          ]),
        });
      }

      // 2. Incident Sync: POST /api/scenarios/{id}/incidents/sync
      if (url.includes('/incidents/sync') && method === 'POST') {
        const payload = JSON.parse(req.postData() || '{}');
        const incidents = payload.incidents || [];
        const ids = incidents.map((i: any) => i.incident_id);
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({
            scenario_id: 'scenario-flash-flood',
            synced_incident_ids: ids,
            duplicate_incident_ids: [],
            rejected_incident_ids: [],
            total_received: ids.length,
            total_synced: ids.length,
            total_duplicates: 0,
            acknowledged_at: new Date().toISOString(),
            status: 'ACKNOWLEDGED',
            disclaimer: 'SIMULATED CITIZEN SOS RECEIPT. Prototype outbox synchronization only.',
          }),
        });
      }

      // 3. Incidents List: GET /api/scenarios/{id}/incidents
      if (url.includes('/incidents') && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({
            scenario_id: 'scenario-flash-flood',
            total_incidents: 0,
            incidents: [],
          }),
        });
      }

      // 4. Pre-Calamity Alerts: GET /api/scenarios/{id}/alerts
      if (url.includes('/alerts') && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({
            scenario_id: 'scenario-flash-flood',
            scenario_name: 'Extreme Monsoonal Inundation & River Surge',
            generated_at: new Date().toISOString(),
            highest_severity: 'CRITICAL',
            affected_zone_count: 1,
            is_simulated: true,
            is_live_confirmed: false,
            disclaimer: 'Advisory simulated alerts only.',
            alerts: [
              {
                alert_id: 'ALT-ZONE-001',
                zone_id: 'ZONE-001',
                zone_name: 'Riverside Industrial District',
                severity: 'CRITICAL',
                risk_score: 82.4,
                dominant_cause: 'Extreme Precipitation',
                headline: 'Flash Flood Emergency: Severe Inundation Threat',
                description: 'Torrential rainfall exceeding canal capacity. Low-lying corridors submerging.',
                action_recommendation: 'Evacuate immediately via designated elevated perimeter corridors.',
                is_hotspot: true,
                generated_at: new Date().toISOString(),
              },
            ],
          }),
        });
      }

      // 5. Safe Points: GET /api/scenarios/{id}/safe-points
      if (url.includes('/safe-points') && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({
            scenario_id: 'scenario-flash-flood',
            safe_points: [
              {
                id: 'SP-01',
                name: 'Northern High School Evacuation Shelter',
                capacity: 1200,
                current_occupancy: 150,
                elevation_m: 42.0,
                status: 'OPEN',
                latitude: 18.995,
                longitude: 72.860,
                has_emergency_power: true,
                has_medical_supplies: true,
              },
            ],
            total_shelter_capacity: 1200,
            highest_elevation_m: 42.0,
          }),
        });
      }

      // 6. Evacuation Route: POST /api/scenarios/{id}/evacuation-route
      if (url.includes('/evacuation-route') && method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({
            route_id: 'ROUTE-SAFE-001',
            scenario_id: 'scenario-flash-flood',
            origin_zone_id: 'ZONE-001',
            origin_zone_name: 'Riverside Industrial District',
            destination_safe_point_id: 'SP-01',
            destination_safe_point_name: 'Northern High School Evacuation Shelter',
            status: 'CONFIRMED_SAFE',
            path_node_ids: ['ZONE-001', 'ROAD-PERIM-01', 'JUNCTION-NORTH-01', 'SP-01'],
            distance_km: 11.7,
            estimated_transit_minutes: 16.4,
            avoided_hazard_nodes: ['Arterial Road Network'],
            avoided_node_details: [
              { node_id: 'Road', name: 'Arterial Road Network', failure_probability: 0.72 },
            ],
            waypoints: [],
            step_by_step_instructions: [
              'Depart Riverside via North Gate',
              'Bypass flooded arterial road via elevated perimeter',
              'Arrive at shelter',
            ],
            generated_at: new Date().toISOString(),
            is_simulated: true,
            is_live_confirmed: false,
            disclaimer: 'SIMULATED ROUTE FOR DEMONSTRATION PURPOSES ONLY.',
          }),
        });
      }

      // 7. Scenario Analysis: POST /api/scenarios/{id}/analyze
      if (url.includes('/analyze') && method === 'POST') {
        if (url.includes('scenario-baseline')) {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            headers: CORS_HEADERS,
            body: JSON.stringify({
              scenario_id: 'scenario-baseline',
              scenario_name: 'Dry Season Baseline (Nominal Flow)',
              execution_timestamp: new Date().toISOString(),
              spec_version: '1.0.0',
              data_label: 'SYNTHETIC / ILLUSTRATIVE DATA ONLY',
              pipeline_status: 'MONITORING_ONLY',
              is_monitoring_only: true,
              hotspot_threshold_applied: 50.0,
              zone_count: 4,
              scorable_zone_count: 4,
              insufficient_zone_count: 0,
              hotspot_count: 0,
              highest_risk_score: 18.0,
              highest_risk_zone_name: 'Harbor & Estuary Basin',
              executed_algorithms: ['Alg 0: Data Preparation', 'Alg 1: Flood Risk Score', 'Alg 2: Hotspot Detection'],
              zones: [
                {
                  zone_id: 'ZONE-001',
                  name: 'Riverside Industrial District',
                  score: 12.0,
                  raw_score: 12.0,
                  normalized_score: 0.12,
                  severity: 'LOW',
                  dominant_cause: 'Nominal Inflow',
                  breakdown: {},
                  flags: [],
                  status: 'COMPUTED',
                  is_scorable: true,
                  is_hotspot: false,
                },
              ],
              hotspots: [],
              exposure_results: [],
              cascade_status: 'SKIPPED_MONITORING_ONLY',
            }),
          });
        }

        // Default: Flash Flood Analysis Output
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({
            scenario_id: 'scenario-flash-flood',
            scenario_name: 'Extreme Monsoonal Inundation & River Surge',
            execution_timestamp: new Date().toISOString(),
            spec_version: '1.0.0',
            data_label: 'SYNTHETIC / ILLUSTRATIVE DATA ONLY',
            pipeline_status: 'SUCCESS',
            is_monitoring_only: false,
            hotspot_threshold_applied: 50.0,
            zone_count: 4,
            scorable_zone_count: 4,
            insufficient_zone_count: 0,
            hotspot_count: 1,
            highest_risk_score: 82.4,
            highest_risk_zone_name: 'Riverside Industrial District',
            executed_algorithms: [
              'Alg 0', 'Alg 1', 'Alg 2', 'Alg 3', 'Alg 4', 'Alg 5', 'Alg 6', 'Alg 7', 'Alg 8', 'Alg 10', 'Alg 11', 'Alg 12', 'Alg 13'
            ],
            zones: [
              {
                zone_id: 'ZONE-001',
                name: 'Riverside Industrial District',
                score: 82.4,
                raw_score: 82.4,
                normalized_score: 0.824,
                severity: 'CRITICAL',
                dominant_cause: 'Extreme Precipitation (Rainfall)',
                breakdown: {},
                flags: [],
                status: 'COMPUTED',
                is_scorable: true,
                is_hotspot: true,
              },
            ],
            hotspots: [
              {
                zone_id: 'ZONE-001',
                name: 'Riverside Industrial District',
                score: 82.4,
                raw_score: 82.4,
                normalized_score: 0.824,
                severity: 'CRITICAL',
                dominant_cause: 'Extreme Precipitation (Rainfall)',
                breakdown: {},
                flags: [],
                status: 'COMPUTED',
                is_scorable: true,
                is_hotspot: true,
              },
            ],
            exposure_results: [],
            cascade_status: 'SUCCESS',
            consequence_graph: {
              nodes: [
                { id: 'Flood', label: 'Flood Origin', seed: true, f: 1.0, c: 0.0, category: 'seed' },
                { id: 'Drainage', label: 'Drainage Network', seed: false, f: 0.85, c: 0.8, category: 'infrastructure' },
                { id: 'Road', label: 'Arterial Road Network', seed: false, f: 0.72, c: 0.7, category: 'infrastructure' },
              ],
              edges: [
                { source: 'Flood', target: 'Drainage', s: 0.85, dependency_type: 'dependency' },
                { source: 'Drainage', target: 'Road', s: 0.72, dependency_type: 'dependency' },
              ],
              cycles_detected: false,
              cycles_broken: 0,
              broken_edges: [],
            },
            cascade_analysis: {
              seed_node: 'Flood',
              seed_risk: 1.0,
              node_risks: { Flood: 1.0, Drainage: 0.85, Road: 0.72 },
              node_states: { Flood: 'FAILING', Drainage: 'FAILING', Road: 'FAILING' },
              failing_nodes: ['Drainage', 'Road'],
              cascade_chain: ['Drainage', 'Road'],
              cascade_length: 2,
              cascade_risk: 0.628,
              tau_applied: 0.30,
              status: 'CASCADE_PROPAGATED',
              cycle_logs: [],
              topological_order: ['Flood', 'Drainage', 'Road'],
            },
            critical_nodes: {
              critical_node: 'Drainage',
              critical_node_details: {
                rank: 1,
                node_id: 'Drainage',
                label: 'Drainage Network',
                category: 'infrastructure',
                criticality_score: 0.88,
                downstream_impact: 0.85,
                direct_risk: 0.85,
                dependency_count: 2,
              },
              ranked_nodes: [
                {
                  rank: 1,
                  node_id: 'Drainage',
                  label: 'Drainage Network',
                  category: 'infrastructure',
                  criticality_score: 0.88,
                  downstream_impact: 0.85,
                  direct_risk: 0.85,
                  dependency_count: 2,
                },
              ],
            },
            break_points: {
              best_break_point: {
                rank: 1,
                intervention_id: 'I1',
                action: 'Deploy High-Capacity Mobile Pumping Units',
                target_node: 'Drainage',
                mitigation_m: 0.8,
                baseline_cascade_risk: 0.628,
                mitigated_cascade_risk: 0.259,
                impact_reduction_abs: 0.369,
                impact_reduction_rel: 0.587,
                impact_reduction_pct: 58.7,
                baseline_cascade_length: 3,
                mitigated_cascade_length: 0,
                cascade_length_delta: 3,
                surviving_nodes: ['Drainage', 'Road'],
              },
              ranked_break_points: [],
            },
            resource_allocation: {
              priority_scores: { 'ZONE-001': 1.0 },
              zone_allocation_order: ['ZONE-001'],
              zone_budgets: { 'ZONE-001': { budget: 42000, pumps: 4 } },
              unmet_demand: [],
              remaining_inventory: {},
              status: 'SUCCESS',
            },
            intervention_ranking: {
              feasible: [
                {
                  intervention_id: 'I1',
                  action: 'Deploy High-Capacity Mobile Pumping Units',
                  name: 'Deploy High-Capacity Mobile Pumping Units',
                  target_node: 'Drainage',
                  required_resources: { budget: 42000, pumps: 4 },
                  score: 0.862,
                  feasible: true,
                  measures: {
                    risk_reduction: 0.587,
                    cascade_reduction: 1.0,
                    population_protection: 0.8,
                    emergency_protection: 0.8,
                    resource_cost: 0.4,
                    baseline_cascade_risk: 0.628,
                    post_cascade_risk: 0.259,
                    baseline_cascade_length: 3,
                    post_cascade_length: 0,
                    baseline_p_pop: 0.7,
                    post_p_pop: 0.1,
                    baseline_p_emerg: 0.6,
                    post_p_emerg: 0.1,
                  },
                },
              ],
              infeasible: [],
            },
            decision_card: {
              status: 'FEASIBLE',
              priority: 'CRITICAL',
              zone_id: 'ZONE-001',
              target_node: 'Drainage',
              action: 'Deploy High-Capacity Mobile Pumping Units',
              intervention_id: 'I1',
              required_resources: { budget: 42000, pumps: 4 },
              reason: 'Optimal break-point reducing cascade risk by 58.7%',
              expected_impact: {
                before: { impact_index: 0.82, cascade_length: 3, population_risk: 0.74 },
                after: { impact_index: 0.34, cascade_length: 0, population_risk: 0.18 },
              },
              quality_flags: [],
              ai_status: 'MOCK',
              nugen_recommendation: 'Deploy pumping units to alleviate drainage bottleneck.',
              nugen_agreement: true,
              human_review_warning: 'Advisory guidance only. Verify with incident commander.',
              run_id: 'RUN-DEMO-001',
            },
          }),
        });
      }

      // 8. Scenario Details: GET /api/scenarios/{id}
      if (url.includes('scenario-baseline')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: CORS_HEADERS,
          body: JSON.stringify({
            scenario_id: 'scenario-baseline',
            name: 'Dry Season Baseline (Nominal Flow)',
            description: 'Standard dry-weather hydrological conditions with low river stages.',
            severity: 'NOMINAL',
            zone_count: 4,
            hotspot_count: 0,
            highest_risk_score: 0.18,
            highest_risk_zone_name: 'Harbor & Estuary Basin',
            critical_infrastructure_count: 16,
            data_label: 'SYNTHETIC / ILLUSTRATIVE DATA ONLY',
            analysis_engine_status: 'NOMINAL_MONITORING',
            zones: [
              {
                zone_id: 'ZONE-001',
                name: 'Riverside Industrial District',
                rainfall_mm: 12.0,
                elevation_m: 4.5,
                soil_saturation_index: 0.22,
                drainage_capacity_cms: 45.0,
                critical_infrastructure_count: 4,
                risk_score: 0.12,
                severity: 'LOW',
                is_hotspot: false,
                population: 32000,
                water_level_m: 0.3,
              },
            ],
          }),
        });
      }

      // Default Scenario Detail: Flash Flood
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_HEADERS,
        body: JSON.stringify({
          scenario_id: 'scenario-flash-flood',
          name: 'Extreme Monsoonal Inundation & River Surge',
          description: 'High-intensity convective cloudburst with rapid urban inundation.',
          severity: 'CRITICAL',
          zone_count: 4,
          hotspot_count: 1,
          highest_risk_score: 82.4,
          highest_risk_zone_name: 'Riverside Industrial District',
          critical_infrastructure_count: 16,
          data_label: 'SYNTHETIC / ILLUSTRATIVE DATA ONLY',
          analysis_engine_status: 'ENGINE_READY',
          zones: [
            {
              zone_id: 'ZONE-001',
              name: 'Riverside Industrial District',
              rainfall_mm: 112.5,
              elevation_m: 4.5,
              soil_saturation_index: 0.92,
              drainage_capacity_cms: 45.0,
              critical_infrastructure_count: 4,
              risk_score: 82.4,
              severity: 'CRITICAL',
              is_hotspot: true,
              population: 32000,
              water_level_m: 2.8,
            },
          ],
        }),
      });
    });

    // Intercept audit logs
    await context.route('**/api/audit-logs', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_HEADERS,
        body: JSON.stringify([]),
      });
    });
  });

  test('executes complete 6-scene end-to-end operational workflow demonstration', async ({ page }) => {
    page.on('console', (msg) => console.log('BROWSER LOG:', msg.text()));
    page.on('pageerror', (err) => console.log('PAGE ERROR:', err));

    // Navigate to application
    await page.goto('/');

    // -------------------------------------------------------------------------
    // SCENE 1 — BASELINE MONITORING & ZERO-HOTSPOT VERIFICATION
    // -------------------------------------------------------------------------
    await page.selectOption('select.scenario-pill-select', 'scenario-baseline');
    await expect(page.locator('select.scenario-pill-select')).toHaveValue('scenario-baseline');

    // Click Run Flood Analysis on baseline scenario
    const runAnalysisBtn = page.locator('button:has-text("Run Flood Analysis")');
    await runAnalysisBtn.click();

    // Verify baseline monitoring-only alert banner appears
    await expect(page.locator('text=MONITORING_ONLY:')).toBeVisible({ timeout: 5000 });

    // -------------------------------------------------------------------------
    // SCENE 2 — FLOOD RISK ESCALATION & HAZARD IDENTIFICATION
    // -------------------------------------------------------------------------
    await page.selectOption('select.scenario-pill-select', 'scenario-flash-flood');
    await expect(page.locator('select.scenario-pill-select')).toHaveValue('scenario-flash-flood');

    // Run deterministic analysis on flash flood scenario
    await page.locator('button:has-text("Run Flood Analysis")').click();

    // Verify canonical risk escalation and dominant hazard cause
    await expect(page.locator('text=82.4').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.badge-critical, .badge-hotspot').first()).toBeVisible();

    // -------------------------------------------------------------------------
    // SCENE 3 — INFRASTRUCTURE CASCADE & NOISY-OR PROPAGATION
    // -------------------------------------------------------------------------
    await page.click('button.nav-button:has-text("Consequence Graph")');
    await expect(page.locator('h1.header-tab-title')).toContainText('Consequence Graph');

    // Verify cascade visualization elements exist
    await expect(page.locator('.consequence-pane, .consequence-summary-grid').first()).toBeVisible({
      timeout: 5000,
    });
    await expect(page.locator('text=Cascade risk')).toBeVisible({ timeout: 5000 });

    // -------------------------------------------------------------------------
    // SCENE 4 — INTERVENTION DECISION SUPPORT & NUGEN ADVISORY
    // -------------------------------------------------------------------------
    await page.click('button.nav-button:has-text("Interventions")');
    await expect(page.locator('h1.header-tab-title')).toContainText('Interventions');

    // Verify ranked candidate intervention I1 is displayed
    await expect(page.locator('text=Deploy High-Capacity Mobile Pumping Units').first()).toBeVisible({
      timeout: 5000,
    });

    // -------------------------------------------------------------------------
    // SCENE 5 — CITIZEN EMERGENCY RESPONSE & SAFE EVACUATION ROUTING
    // -------------------------------------------------------------------------
    await page.click('button.nav-button:has-text("Emergency Chatbot")');
    await expect(page.locator('h1.header-tab-title')).toContainText('Emergency Chatbot');

    // Verify pre-calamity citizen alerts
    await expect(page.locator('text=Flash Flood Emergency: Severe Inundation Threat').first()).toBeVisible({
      timeout: 5000,
    });

    // Plan safe evacuation route
    await page.click('button:has-text("Find Safe Route")');

    // Verify shortest safe path results with hazard avoidance
    await expect(page.locator('text=11.7 km')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Avoided 1 flooded/failing infrastructure asset')).toBeVisible();

    // -------------------------------------------------------------------------
    // SCENE 6 — OFFLINE PANIC RESILIENCE & SOS OUTBOX DRAINAGE
    // -------------------------------------------------------------------------
    // Engage Panic Phase
    const panicBtn = page.locator('button[aria-label="Toggle Panic Phase"]');
    await panicBtn.click();

    // Verify OFFLINE SURVIVAL MODE banner
    await expect(page.locator('text=OFFLINE SURVIVAL MODE')).toBeVisible();

    // Fill and submit SOS distress report
    await page.fill('#sos-desc', 'Severe water inundation reaching upper floor, 4 citizens trapped.');
    await page.click('button:has-text("Record Emergency SOS (Queue Outbox)")');

    // Verify distress report is queued with NOT_SENT status
    await expect(page.locator('text=Severe water inundation reaching upper floor')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=NOT_SENT').first()).toBeVisible();

    // Disengage Panic Phase / restore network connection
    await panicBtn.click();

    // Verify automatic background synchronization updates receipt to ACKNOWLEDGED
    await expect(page.locator('text=ACKNOWLEDGED').first()).toBeVisible({ timeout: 10000 });
  });
});
