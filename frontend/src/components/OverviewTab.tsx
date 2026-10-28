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
} from 'lucide-react';
import type {
  ScenarioDetail,
  ScenarioSummaryItem,
  AuditEvent,
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
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  scenarios,
  selectedScenarioId,
  scenarioDetail,
  isLoadingScenario,
  onSelectScenario,
  healthResult,
  recentAuditLogs,
}) => {
  const getSeverityBadgeClass = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'badge-critical';
      case 'HIGH':
        return 'badge-high';
      case 'MODERATE':
      case 'ELEVATED':
        return 'badge-moderate';
      case 'LOW':
      case 'NOMINAL':
      default:
        return 'badge-low';
    }
  };

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
              disabled={isLoadingScenario}
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

        {/* Run Analysis Button (Intentionally Disabled with Explanation) */}
        <div className="run-analysis-group">
          <button
            type="button"
            className="btn btn-disabled"
            disabled
            title="Analysis engine will be connected in Milestone 2"
          >
            <Play size={16} />
            <span>Run Flood Analysis</span>
          </button>
          <div className="action-disabled-explanation">
            <Info size={14} className="text-cyan flex-shrink-0" />
            <span>
              <strong>Milestone 1 Scope:</strong> Deterministic Flood Risk Engine (Algorithms 0–5) is scheduled for Milestone 2. Calculation execution is currently disabled.
            </span>
          </div>
        </div>
      </section>

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
          <div className="kpi-value">{scenarioDetail?.zone_count ?? '—'}</div>
          <div className="kpi-footer">
            <span>Hydraulic catchment sectors</span>
          </div>
        </div>

        {/* KPI 2: Peak Risk Index */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">PEAK RISK INDEX</span>
            <AlertTriangle size={18} className="text-amber" />
          </div>
          <div className="kpi-value text-amber">
            {scenarioDetail ? scenarioDetail.highest_risk_score.toFixed(2) : '—'}
          </div>
          <div className="kpi-footer">
            <span className="truncate">
              Zone: {scenarioDetail?.highest_risk_zone_name ?? '—'}
            </span>
          </div>
        </div>

        {/* KPI 3: Priority Hotspots */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">PRIORITY HOTSPOTS</span>
            <Flame size={18} className="text-red" />
          </div>
          <div className="kpi-value text-red">
            {scenarioDetail?.hotspot_count ?? '—'}
          </div>
          <div className="kpi-footer">
            <span>Requiring immediate intervention</span>
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

      {/* Zone Telemetry and Risk Table */}
      <section className="dashboard-card">
        <div className="card-header-row">
          <div>
            <h2 className="card-heading">Catchment Zone Telemetry & Risk Table</h2>
            <p className="card-subheading">
              Hydrological telemetry and deterministic risk classification per zone
            </p>
          </div>
          <div className="card-badge-provenance">
            <span>PROVENANCE: SYNTHETIC_SCENARIO_PROTOTYPE</span>
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
                <th>Risk Score</th>
                <th>Severity Tier</th>
                <th>Hotspot Status</th>
                <th>Data Provenance</th>
              </tr>
            </thead>
            <tbody>
              {scenarioDetail?.zones.map((zone) => (
                <tr key={zone.zone_id} className={zone.is_hotspot ? 'row-hotspot' : ''}>
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
                    <code className="score-code">{zone.risk_score.toFixed(2)}</code>
                  </td>
                  <td>
                    <span className={`severity-pill ${getSeverityBadgeClass(zone.severity)}`}>
                      {zone.severity}
                    </span>
                  </td>
                  <td>
                    {zone.is_hotspot ? (
                      <span className="badge-hotspot">
                        <Flame size={12} /> HOTSPOT
                      </span>
                    ) : (
                      <span className="badge-nominal">MONITORING</span>
                    )}
                  </td>
                  <td>
                    <span className="provenance-tag">{zone.data_provenance}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

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
