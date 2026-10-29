import React from 'react';
import {
  Layers,
  AlertTriangle,
  Flame,
  Building2,
  Play,
  Activity,
  CheckCircle2,
  XCircle,
  Info,
  Loader2,
  ShieldCheck,
  Check,
} from 'lucide-react';
import type {
  ScenarioDetail,
  ScenarioSummaryItem,
  AuditEvent,
  ScenarioAnalysisResponse,
} from '../types/api';
import type { HealthCheckResult } from '../services/api';

interface OverviewTabProps {
  scenarios: ScenarioSummaryItem[];
  selectedScenarioId: string;
  scenarioDetail: ScenarioDetail | null;
  isLoadingScenario: boolean;
  onSelectScenario: (scenarioId: string) => void;
  healthResult: HealthCheckResult | null;
  recentAuditLogs: AuditEvent[];
  analysisResult: ScenarioAnalysisResponse | null;
  isAnalyzing: boolean;
  analysisError: string | null;
  onRunAnalysis: () => Promise<void>;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  scenarios,
  selectedScenarioId,
  scenarioDetail,
  isLoadingScenario,
  onSelectScenario,
  healthResult,
  recentAuditLogs,
  analysisResult,
  isAnalyzing,
  analysisError,
  onRunAnalysis,
}) => {
  const getSeverityBadgeClass = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'badge-critical';
      case 'HIGH':
        return 'badge-high';
      case 'MEDIUM':
      case 'MODERATE':
      case 'ELEVATED':
        return 'badge-moderate';
      case 'LOW':
      case 'NOMINAL':
        return 'badge-low';
      case 'DATA_INSUFFICIENT':
      default:
        return 'badge-insufficient';
    }
  };

  // Determine active KPI values (prefer authoritative backend analysis results if computed)
  const isAnalysisActive = !!analysisResult && analysisResult.scenario_id === selectedScenarioId;

  const displayZoneCount = isAnalysisActive
    ? analysisResult.zone_count
    : scenarioDetail?.zone_count ?? '—';

  const displayPeakRisk = isAnalysisActive
    ? analysisResult.highest_risk_score.toFixed(1)
    : scenarioDetail
    ? (scenarioDetail.highest_risk_score > 1.0 ? scenarioDetail.highest_risk_score : scenarioDetail.highest_risk_score * 100).toFixed(1)
    : '—';

  const displayPeakZone = isAnalysisActive
    ? analysisResult.highest_risk_zone_name
    : scenarioDetail?.highest_risk_zone_name ?? '—';

  const displayHotspots = isAnalysisActive
    ? analysisResult.hotspot_count
    : scenarioDetail?.hotspot_count ?? '—';

  const isMonitoringOnly = isAnalysisActive && analysisResult.is_monitoring_only;
  const isDataInsufficient = isAnalysisActive && analysisResult.pipeline_status === 'DATA_INSUFFICIENT';

  return (
    <div className="tab-pane overview-pane">
      {/* Scenario Selection & Execution Control Bar */}
      <section className="control-bar-card">
        <div className="scenario-selector-group">
          <label htmlFor="scenario-select" className="control-label">
            Active Demonstration Scenario:
          </label>
          <div className="select-wrapper">
            <select
              id="scenario-select"
              className="scenario-select"
              value={selectedScenarioId}
              onChange={(e) => onSelectScenario(e.target.value)}
              disabled={isLoadingScenario || isAnalyzing}
            >
              {scenarios.map((s) => (
                <option key={s.scenario_id} value={s.scenario_id}>
                  {s.name} — [{s.severity}]
                </option>
              ))}
            </select>
          </div>
          {scenarioDetail && (
            <span className={`scenario-severity-tag ${getSeverityBadgeClass(scenarioDetail.severity)}`}>
              {scenarioDetail.severity}
            </span>
          )}
        </div>

        {/* Milestone 2 Run Flood Analysis Action Button */}
        <div className="run-analysis-group">
          <button
            type="button"
            className="btn btn-primary"
            onClick={onRunAnalysis}
            disabled={isAnalyzing || isLoadingScenario || !healthResult?.success}
            title={
              !healthResult?.success
                ? 'Backend core offline — connect uvicorn to run analysis'
                : isAnalyzing
                ? 'Executing Algorithms 0–3...'
                : 'Execute deterministic calculation pipeline (Algorithms 0–3)'
            }
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={16} className="animate-spin text-cyan" />
                <span>Computing Risk (Alg 0–3)...</span>
              </>
            ) : isAnalysisActive ? (
              <>
                <Check size={16} className="text-green" />
                <span>Re-run Analysis</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Run Flood Analysis</span>
              </>
            )}
          </button>

          {isAnalysisActive ? (
            <span className={`analysis-status-badge status-${analysisResult.pipeline_status.toLowerCase()}`}>
              <ShieldCheck size={14} />
              <span>
                {analysisResult.pipeline_status} &bull; {analysisResult.spec_version}
              </span>
            </span>
          ) : (
            <div className="action-disabled-explanation">
              <Info size={14} className="text-cyan flex-shrink-0" />
              <span>
                <strong>Milestone 2 Ready:</strong> Executes deterministic Algorithms 0–3 (Data Prep, Risk 0–100, Hotspots &ge;50, Exposure).
              </span>
            </div>
          )}
        </div>
      </section>

      {/* Analysis Error Alert */}
      {analysisError && (
        <div className="alert-banner-error">
          <div className="flex items-center gap-2">
            <XCircle size={18} className="text-red flex-shrink-0" />
            <span>{analysisError}</span>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-retry"
            onClick={onRunAnalysis}
            disabled={isAnalyzing}
          >
            Retry Analysis
          </button>
        </div>
      )}

      {/* Specific Pipeline Status Alerts */}
      {isMonitoringOnly && (
        <div className="alert-banner-monitoring">
          <ShieldCheck size={20} className="text-cyan flex-shrink-0 mt-0.5" />
          <div>
            <strong>MONITORING_ONLY Status:</strong> Zero priority hotspots detected (peak risk score {analysisResult.highest_risk_score} is below the 50.0 threshold). Per canonical Algorithm 2 specifications, downstream consequence graph and cascade propagation are safely suspended.
          </div>
        </div>
      )}

      {isDataInsufficient && (
        <div className="alert-banner-insufficient">
          <AlertTriangle size={20} className="text-red flex-shrink-0 mt-0.5" />
          <div>
            <strong>DATA_INSUFFICIENT Status:</strong> One or more required hydrological inputs (rainfall depth or drainage capacity) are missing or invalid. Authoritative risk scores are strictly withheld per Algorithm 0 data-integrity rules.
          </div>
        </div>
      )}

      {/* Scenario Description Narrative */}
      {scenarioDetail && (
        <div className="scenario-narrative-bar">
          <span className="narrative-label">SCENARIO NARRATIVE:</span>
          <p className="narrative-text">{scenarioDetail.description}</p>
        </div>
      )}

      {/* KPI Summary Cards */}
      <section className="kpi-grid">
        {/* KPI 1: Evaluated Zones */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">EVALUATED ZONES</span>
            <Layers size={18} className="text-cyan" />
          </div>
          <div className="kpi-value">{displayZoneCount}</div>
          <div className="kpi-footer">
            <span>
              {isAnalysisActive
                ? `${analysisResult.scorable_zone_count} Scorable / ${analysisResult.insufficient_zone_count} Insufficient`
                : 'Hydraulic catchment sectors'}
            </span>
          </div>
        </div>

        {/* KPI 2: Peak Risk Index */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">PEAK RISK INDEX</span>
            <AlertTriangle size={18} className="text-amber" />
          </div>
          <div className="kpi-value text-amber">
            {displayPeakRisk}
            {isAnalysisActive && <span className="text-xs text-slate-400 font-normal ml-1">/ 100</span>}
          </div>
          <div className="kpi-footer">
            <span className="truncate">Zone: {displayPeakZone}</span>
          </div>
        </div>

        {/* KPI 3: Priority Hotspots */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">PRIORITY HOTSPOTS</span>
            <Flame size={18} className="text-red" />
          </div>
          <div className="kpi-value text-red">{displayHotspots}</div>
          <div className="kpi-footer">
            <span>{isAnalysisActive ? 'Score \u2265 50.0 threshold' : 'Requiring immediate intervention'}</span>
          </div>
        </div>

        {/* KPI 4: Critical Assets */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">CRITICAL ASSETS</span>
            <Building2 size={18} className="text-indigo" />
          </div>
          <div className="kpi-value text-indigo">
            {scenarioDetail?.critical_infrastructure_count ?? '—'}
          </div>
          <div className="kpi-footer">
            <span>Substations, hospitals, water plants</span>
          </div>
        </div>
      </section>

      {/* Catchment Zone Telemetry & Risk Table */}
      <section className="dashboard-card">
        <div className="card-header-row">
          <div>
            <h2 className="card-heading">Catchment Zone Telemetry & Risk Table</h2>
            <p className="card-subheading">
              Hydrological telemetry and deterministic risk classification (Algorithms 0–1)
            </p>
          </div>
          <div className="card-badge-provenance">
            <span>
              {isAnalysisActive
                ? 'PROVENANCE: DETERMINISTIC_ENGINE_M2'
                : 'PROVENANCE: SYNTHETIC_SCENARIO_PROTOTYPE'}
            </span>
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Zone ID & Name</th>
                <th>Elevation</th>
                <th>Precipitation</th>
                <th>Soil Saturation</th>
                <th>Drainage</th>
                <th>Critical Assets</th>
                <th>Risk Score (0–100)</th>
                <th>Severity Tier</th>
                <th>Hotspot Status</th>
                <th>Critical Driver</th>
              </tr>
            </thead>
            <tbody>
              {scenarioDetail?.zones.map((zone) => {
                // If analysis has run, lookup calculated zone metrics
                const calculated = isAnalysisActive
                  ? analysisResult.zones.find((cz) => cz.zone_id === zone.zone_id)
                  : null;

                const scoreText = calculated
                  ? calculated.score !== null
                    ? calculated.score.toFixed(1)
                    : 'DATA_INSUFFICIENT'
                  : (zone.risk_score > 1.0 ? zone.risk_score : zone.risk_score * 100).toFixed(1);

                const severityValue = calculated ? calculated.severity : zone.severity;
                const isHotspot = calculated ? calculated.is_hotspot : zone.is_hotspot;
                const dominantCause = calculated?.dominant_cause || 'Precipitation Inflow';

                return (
                  <tr key={zone.zone_id} className={isHotspot ? 'row-hotspot' : ''}>
                    <td className="cell-primary">
                      <span className="zone-id-tag">{zone.zone_id}</span>
                      <span className="zone-name-text">{zone.name}</span>
                    </td>
                    <td>{zone.elevation_m.toFixed(1)} m</td>
                    <td>{zone.rainfall_mm.toFixed(0)} mm</td>
                    <td>
                      <div className="saturation-bar-cell">
                        <span>{(zone.soil_saturation_index * 100).toFixed(0)}%</span>
                        <div className="mini-progress-track">
                          <div
                            className="mini-progress-fill"
                            style={{ width: `${zone.soil_saturation_index * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>{zone.drainage_capacity_cms} m³/s</td>
                    <td className="text-center">{zone.critical_infrastructure_count}</td>
                    <td className="cell-score">
                      <code className="score-code">{scoreText}</code>
                      {calculated?.normalized_score !== null && calculated?.normalized_score !== undefined && (
                        <div className="text-[10px] text-slate-400">
                          [{calculated.normalized_score.toFixed(3)}]
                        </div>
                      )}
                    </td>
                    <td>
                      <span className={`severity-pill ${getSeverityBadgeClass(severityValue)}`}>
                        {severityValue}
                      </span>
                    </td>
                    <td>
                      {isHotspot ? (
                        <span className="badge-hotspot">
                          <Flame size={12} /> HOTSPOT
                        </span>
                      ) : calculated && !calculated.is_scorable ? (
                        <span className="badge-insufficient">INSUFFICIENT</span>
                      ) : (
                        <span className="badge-nominal">MONITORING</span>
                      )}
                    </td>
                    <td>
                      <span className="cause-tag">{dominantCause}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Algorithm 3: Flood Impact & Exposure Calculation Section */}
      {isAnalysisActive && (
        <section className="dashboard-card">
          <div className="card-header-row">
            <div>
              <h2 className="card-heading">Algorithm 3 — Priority Hotspot Impact & Exposure</h2>
              <p className="card-subheading">
                Multi-factor vulnerability assessment (u: Pop=0.35, Infra=0.25, Roads=0.20, Routes=0.20)
              </p>
            </div>
            <div className="card-badge-provenance">
              <span>ALGORITHM 3 EXPOSURE ENGINE</span>
            </div>
          </div>

          {isMonitoringOnly ? (
            <div className="alert-banner-monitoring mt-3">
              <ShieldCheck size={18} className="text-cyan flex-shrink-0" />
              <span>
                <strong>Zero Hotspots Qualified:</strong> Because all zones scored below the 50.0 threshold, Algorithm 3 exposure evaluation is skipped by design under MONITORING_ONLY.
              </span>
            </div>
          ) : analysisResult.exposure_results.length > 0 ? (
            <div className="exposure-grid">
              {analysisResult.exposure_results.map((exp) => (
                <div key={exp.zone_id} className="exposure-card">
                  <div className="exposure-card-header">
                    <div>
                      <span className="text-xs text-cyan font-mono block">{exp.zone_id}</span>
                      <span className="exposure-zone-title">{exp.name}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-slate-400 uppercase block font-semibold">ImpactScore</span>
                      <span className="exposure-impact-badge">
                        {exp.impact_score !== null ? exp.impact_score.toFixed(3) : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="exposure-breakdown-list">
                    <div className="exposure-component-row">
                      <span className="exposure-component-label">Population Exposure (w=0.35):</span>
                      <span className="exposure-component-val">
                        {exp.population_score !== null ? exp.population_score.toFixed(3) : 'N/A'}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          ({exp.raw_counts.population?.toLocaleString() ?? '—'} res)
                        </span>
                      </span>
                    </div>
                    <div className="exposure-component-row">
                      <span className="exposure-component-label">Critical Infrastructure (w=0.25):</span>
                      <span className="exposure-component-val">
                        {exp.infrastructure_score !== null ? exp.infrastructure_score.toFixed(3) : 'N/A'}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          ({exp.raw_counts.critical_infra ?? '—'} facilities)
                        </span>
                      </span>
                    </div>
                    <div className="exposure-component-row">
                      <span className="exposure-component-label">Arterial Road Network (w=0.20):</span>
                      <span className="exposure-component-val">
                        {exp.road_score !== null ? exp.road_score.toFixed(3) : 'N/A'}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          ({exp.raw_counts.road_length_km ?? '—'} km)
                        </span>
                      </span>
                    </div>
                    <div className="exposure-component-row">
                      <span className="exposure-component-label">Emergency Corridors (w=0.20):</span>
                      <span className="exposure-component-val">
                        {exp.emergency_score !== null ? exp.emergency_score.toFixed(3) : 'N/A'}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          ({exp.raw_counts.emergency_routes ?? '—'} routes)
                        </span>
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="activity-empty mt-3">No exposure metrics calculated for this scenario.</div>
          )}
        </section>
      )}

      {/* Two Column Section: System Health & Recent Activity */}
      <section className="overview-split-grid">
        {/* Subsystems Diagnostics Card */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <h3 className="card-heading-sm">
              <Activity size={18} className="text-cyan" /> Core Subsystems Health
            </h3>
            <span className="timestamp-tag">
              {healthResult?.data ? new Date(healthResult.data.timestamp).toLocaleTimeString() : 'Offline'}
            </span>
          </div>

          {healthResult?.success && healthResult.data ? (
            <div className="subsystems-list">
              {Object.entries(healthResult.data.subsystems).map(([name, status]) => (
                <div key={name} className="subsystem-row">
                  <span className="subsystem-title">{name.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="subsystem-status-indicator">
                    <CheckCircle2 size={14} className="text-green" />
                    <span>{status}</span>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="subsystem-offline-box">
              <XCircle size={20} className="text-red" />
              <div>
                <p className="offline-heading">Backend Core Unavailable</p>
                <p className="offline-subtext">
                  Start uvicorn on port 8000: <code>uvicorn --app-dir backend app.main:app</code>
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Authentic Recent Session Activity Card */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <h3 className="card-heading-sm">
              <Activity size={18} className="text-indigo" /> Recent Session Activity
            </h3>
            <span className="timestamp-tag">Verified Events Only</span>
          </div>

          <div className="activity-event-list">
            {recentAuditLogs.slice(0, 4).map((evt) => (
              <div key={evt.event_id} className="activity-item">
                <div className="activity-meta">
                  <span className="activity-type">{evt.event_type}</span>
                  <span className="activity-time">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="activity-desc">{evt.description}</p>
              </div>
            ))}
            {recentAuditLogs.length === 0 && (
              <div className="activity-empty">No session activity recorded yet.</div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
