import React, { useState } from 'react';
import {
  AlertTriangle,
  Flame,
  Play,
  Activity,
  CheckCircle2,
  XCircle,
  Info,
  Loader2,
  ShieldCheck,
  Check,
  ArrowRight,
  MapPin,
  Map,
  Zap,
} from 'lucide-react';
import type {
  ScenarioDetail,
  ScenarioSummaryItem,
  AuditEvent,
  ScenarioAnalysisResponse,
  ScenarioZoneItem,
  FloodPredictionResponse,
} from '../types/api';
import type { HealthCheckResult } from '../services/api';
import type { NavigationTab } from './Sidebar';

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
  onNavigateTab?: (tab: NavigationTab) => void;
  mlPrediction: FloodPredictionResponse | null;
  mlPredictionError: string | null;
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
  onNavigateTab,
  mlPrediction,
  mlPredictionError,
}) => {
  // Map Layer State
  const [activeMapLayer, setActiveMapLayer] = useState<'flood' | 'grid' | 'safe'>('flood');
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

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

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return '#dc2626';
      case 'HIGH':
        return '#ea580c';
      case 'MEDIUM':
      case 'MODERATE':
      case 'ELEVATED':
        return '#d97706';
      case 'LOW':
      case 'NOMINAL':
      default:
        return '#16a34a';
    }
  };

  const isAnalysisActive = !!analysisResult && analysisResult.scenario_id === selectedScenarioId;
  const isMonitoringOnly = isAnalysisActive && analysisResult.is_monitoring_only;
  const isDataInsufficient = isAnalysisActive && analysisResult.pipeline_status === 'DATA_INSUFFICIENT';

  // 1. KPI Calculation — Overall Risk
  const displayPeakRisk = isAnalysisActive
    ? analysisResult.highest_risk_score.toFixed(1)
    : scenarioDetail
    ? (scenarioDetail.highest_risk_score > 1.0
        ? scenarioDetail.highest_risk_score
        : scenarioDetail.highest_risk_score * 100
      ).toFixed(1)
    : '—';

  const peakZoneName = isAnalysisActive
    ? analysisResult.highest_risk_zone_name
    : scenarioDetail?.highest_risk_zone_name ?? 'Basin';

  const overallRiskTier = isAnalysisActive
    ? isMonitoringOnly
      ? 'Monitoring Only'
      : analysisResult.highest_risk_score >= 80
      ? 'Critical'
      : analysisResult.highest_risk_score >= 50
      ? 'Elevated'
      : 'Nominal'
    : scenarioDetail?.severity ?? 'Pending';

  // 2. KPI Calculation — Population at Risk
  let populationAtRisk: number | null = null;
  let popSubtitle = 'Within catchment basin';

  if (isAnalysisActive) {
    if (isMonitoringOnly) {
      populationAtRisk = 0;
      popSubtitle = '0 hotspot zones (< 50.0 threshold)';
    } else if (analysisResult.exposure_results?.length > 0) {
      populationAtRisk = analysisResult.exposure_results.reduce(
        (sum, e) => sum + (e.raw_counts?.population || 0),
        0
      );
      popSubtitle = 'Across priority hotspot zones';
    }
  } else if (scenarioDetail?.zones) {
    const hotspotPop = scenarioDetail.zones
      .filter((z) => z.is_hotspot || z.severity === 'CRITICAL' || z.severity === 'HIGH')
      .reduce((sum, z) => sum + (z.population || 0), 0);
    const totalPop = scenarioDetail.zones.reduce((sum, z) => sum + (z.population || 0), 0);
    if (hotspotPop > 0) {
      populationAtRisk = hotspotPop;
      popSubtitle = `Of ${totalPop.toLocaleString()} total residents`;
    } else if (totalPop > 0) {
      populationAtRisk = totalPop;
      popSubtitle = 'Catchment residency';
    }
  }

  // 3. KPI Calculation — Critical Infrastructure
  const criticalInfraCount = scenarioDetail?.critical_infrastructure_count ?? (
    scenarioDetail?.zones
      ? scenarioDetail.zones.reduce((sum, z) => sum + (z.critical_infrastructure_count || 0), 0)
      : null
  );

  const cascadeFailedCount = isAnalysisActive && analysisResult.cascade_analysis
    ? analysisResult.cascade_analysis.failing_nodes.length
    : 0;

  const cascadeTotalEvaluated = isAnalysisActive && analysisResult.cascade_analysis
    ? Object.keys(analysisResult.cascade_analysis.node_states).length
    : 0;

  const cascadeSurvivingCount = Math.max(0, cascadeTotalEvaluated - cascadeFailedCount);

  const infraSubtitle = isAnalysisActive && analysisResult.cascade_analysis
    ? `${cascadeFailedCount} at risk / ${cascadeSurvivingCount} secure`
    : 'Substations, hospitals, water plants';

  // 4. KPI Calculation — Feasible Interventions
  let feasibleCountText = '—';
  let feasibleBadgeText = 'Pending';
  let feasibleSubtitle = 'Run flood analysis to evaluate';

  if (isAnalysisActive) {
    if (isMonitoringOnly) {
      feasibleCountText = '0 Actionable';
      feasibleBadgeText = 'Monitoring Only';
      feasibleSubtitle = 'Zero hotspots; deployment suspended';
    } else if (analysisResult.intervention_ranking) {
      const feasible = analysisResult.intervention_ranking.feasible.length;
      const infeasible = analysisResult.intervention_ranking.infeasible.length;
      const total = feasible + infeasible;
      feasibleCountText = `${feasible} of ${total}`;
      feasibleBadgeText = feasible > 0 ? 'Operational' : 'Blocked';
      feasibleSubtitle = feasible > 0 ? 'Ranked by multi-criteria score' : 'Depot constraints exhausted';
    }
  } else if (scenarioDetail?.interventions) {
    feasibleCountText = `${scenarioDetail.interventions.length} Candidates`;
    feasibleBadgeText = 'Ready';
    feasibleSubtitle = 'Run analysis to rank feasibility';
  }

  // Active Zone Selection for Map Inspector
  const activeSelectedZoneId = selectedZoneId || scenarioDetail?.zones[0]?.zone_id;
  const currentSelectedZone: ScenarioZoneItem | undefined = scenarioDetail?.zones.find(
    (z) => z.zone_id === activeSelectedZoneId
  );

  // Top 3 Feasible Interventions
  const topFeasibleInterventions = isAnalysisActive && analysisResult.intervention_ranking
    ? analysisResult.intervention_ranking.feasible.slice(0, 3)
    : [];

  // Top Critical Node for Consequence Summary
  const topCriticalNode = isAnalysisActive && analysisResult.critical_nodes?.ranked_nodes?.length
    ? analysisResult.critical_nodes.ranked_nodes[0]
    : null;

  return (
    <div className="tab-pane overview-pane">
      {/* Scenario Control & Execution Bar */}
      <section className="control-bar-card">
        <div className="scenario-selector-group">
          <label htmlFor="scenario-select" className="control-label">
            Active Scenario:
          </label>
          <div className="select-wrapper">
            <select
              id="scenario-select"
              className="scenario-select"
              value={selectedScenarioId}
              onChange={(e) => onSelectScenario(e.target.value)}
              disabled={isLoadingScenario || isAnalyzing}
              aria-label="Active demonstration scenario"
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

        {/* Run Flood Analysis Action */}
        <div className="run-analysis-group">
          <button
            type="button"
            className="btn btn-primary"
            onClick={onRunAnalysis}
            disabled={isAnalyzing || isLoadingScenario || !healthResult?.success}
            title={
              !healthResult?.success
                ? 'Backend core offline — start uvicorn backend server'
                : isAnalyzing
                ? 'Executing Algorithms 0–13...'
                : 'Execute deterministic calculation pipeline'
            }
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={15} className="spin-animation" />
                <span>Computing Risk (Algo 0–13)...</span>
              </>
            ) : isAnalysisActive ? (
              <>
                <Check size={15} />
                <span>Re-run Analysis</span>
              </>
            ) : (
              <>
                <Play size={15} />
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
                Executes deterministic calculation pipeline (Algorithms 0–13).
              </span>
            </div>
          )}
        </div>
      </section>

      <section className="alert-banner-info ml-flood-card" aria-live="polite">
        <Activity size={18} className="text-cyan flex-shrink-0 mt-0.5" />
        {mlPrediction ? (
          <div>
            <strong>ML FLOOD-RISK PREDICTOR</strong>
            <span> &mdash; {mlPrediction.predicted_risk_class}</span>
            <span> &mdash; Confidence {(mlPrediction.confidence * 100).toFixed(1)}%</span>
            <span> &mdash; {mlPrediction.model_version}</span>
          </div>
        ) : mlPredictionError ? (
          <div>
            <strong>ML prediction unavailable:</strong> {mlPredictionError}
          </div>
        ) : (
          <div>
            <strong>ML prediction:</strong> Run flood analysis to generate a separate next-day rainfall-risk classification.
          </div>
        )}
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

      {/* Pipeline Status Alerts */}
      {isMonitoringOnly && (
        <div className="alert-banner-monitoring">
          <ShieldCheck size={18} className="text-cyan flex-shrink-0 mt-0.5" />
          <div>
            <strong>MONITORING_ONLY:</strong> Peak risk score ({analysisResult.highest_risk_score.toFixed(1)}) is below the 50.0 threshold. Zero priority hotspots qualified; consequence graph and intervention dispatch are safely suspended per canonical Algorithm 2/13 specifications.
          </div>
        </div>
      )}

      {isDataInsufficient && (
        <div className="alert-banner-insufficient">
          <AlertTriangle size={18} className="text-red flex-shrink-0 mt-0.5" />
          <div>
            <strong>DATA_INSUFFICIENT:</strong> Hydrological inputs (rainfall depth or drainage capacity) are missing or incomplete. Authoritative risk scores are strictly withheld per Algorithm 0 data-integrity rules.
          </div>
        </div>
      )}

      {/* 4 PRIMARY COMPACT KPI CARDS */}
      <section className="kpi-grid">
        {/* KPI 1: Overall Risk */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">OVERALL RISK</span>
            <span
              className={`kpi-chip ${
                overallRiskTier.toLowerCase().includes('critical') || overallRiskTier.toLowerCase().includes('severe')
                  ? 'chip-critical'
                  : overallRiskTier.toLowerCase().includes('elevated') || overallRiskTier.toLowerCase().includes('moderate')
                  ? 'chip-amber'
                  : 'chip-green'
              }`}
            >
              {overallRiskTier}
            </span>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">{displayPeakRisk}</span>
            {displayPeakRisk !== '—' && <span className="kpi-unit">/ 100</span>}
          </div>
          <p className="kpi-footer truncate">
            Peak sector: <strong className="font-sans">{peakZoneName}</strong>
          </p>
        </div>

        {/* KPI 2: Population at Risk */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">POPULATION AT RISK</span>
            <span className="kpi-chip chip-amber">
              {populationAtRisk !== null && populationAtRisk > 0 ? 'Exposed' : 'Baseline'}
            </span>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {populationAtRisk !== null ? populationAtRisk.toLocaleString() : 'Unavailable'}
            </span>
            {populationAtRisk !== null && <span className="kpi-unit">people</span>}
          </div>
          <p className="kpi-footer truncate">{popSubtitle}</p>
        </div>

        {/* KPI 3: Critical Infrastructure */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">CRITICAL INFRASTRUCTURE</span>
            <span className="kpi-chip chip-teal">
              {criticalInfraCount !== null ? `${criticalInfraCount} mapped` : 'Active'}
            </span>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {criticalInfraCount !== null ? criticalInfraCount : 'Unavailable'}
            </span>
            {criticalInfraCount !== null && <span className="kpi-unit">facilities</span>}
          </div>
          <p className="kpi-footer truncate">{infraSubtitle}</p>
        </div>

        {/* KPI 4: Feasible Interventions */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">FEASIBLE INTERVENTIONS</span>
            <span
              className={`kpi-chip ${
                feasibleBadgeText === 'Operational' || feasibleBadgeText === 'Ready'
                  ? 'chip-green'
                  : feasibleBadgeText === 'Monitoring Only'
                  ? 'chip-teal'
                  : 'chip-amber'
              }`}
            >
              {feasibleBadgeText}
            </span>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">{feasibleCountText}</span>
            {isAnalysisActive && !isMonitoringOnly && (
              <span className="kpi-unit">actionable</span>
            )}
          </div>
          <p className="kpi-footer truncate">{feasibleSubtitle}</p>
        </div>
      </section>

      {/* RESPONSIVE MAIN WORKSPACE: GEOGRAPHIC MAP (LEFT) + TOP INTERVENTIONS & CONSEQUENCE SUMMARY (RIGHT) */}
      <div className="overview-main-grid">
        {/* LEFT COLUMN: Geographic Hazard Map Workspace */}
        <section className="overview-map-card">
          {/* Map Header Toolbar */}
          <div className="overview-card-header">
            <div className="flex items-center gap-2">
              <Map size={16} className="text-brand-forest" />
              <h2 className="overview-card-title">GEOGRAPHIC HAZARD SCHEMATIC</h2>
              <span className="text-slate-300">|</span>
              <span className="text-xs text-slate-500 font-normal">
                {scenarioDetail?.name || 'Catchment Grid'}
              </span>
            </div>

            {/* Layer Controls */}
            <div className="map-layer-pills">
              <button
                type="button"
                className={`layer-pill-btn ${activeMapLayer === 'flood' ? 'active' : ''}`}
                onClick={() => setActiveMapLayer('flood')}
              >
                Flood extent
              </button>
              <button
                type="button"
                className={`layer-pill-btn ${activeMapLayer === 'grid' ? 'active' : ''}`}
                onClick={() => setActiveMapLayer('grid')}
              >
                Terrain
              </button>
              <button
                type="button"
                className={`layer-pill-btn ${activeMapLayer === 'safe' ? 'active' : ''}`}
                onClick={() => setActiveMapLayer('safe')}
              >
                Safe points
              </button>
            </div>
          </div>

          {/* Map Canvas Surface */}
          <div className="overview-map-viewport">
            {/* Top Left Watermark */}
            <div className="map-watermark-pill">
              <span className="watermark-dot" />
              <span>Schematic Map Preview &bull; Synthetic Model</span>
            </div>

            {/* Top Right Selected Asset Inspector */}
            {currentSelectedZone && (
              <div className="map-zone-inspector">
                <div className="inspector-header">
                  <span className="inspector-title">Selected Sector</span>
                  <span
                    className={`kpi-chip ${
                      currentSelectedZone.is_hotspot ? 'chip-critical' : 'chip-green'
                    }`}
                  >
                    {currentSelectedZone.is_hotspot ? 'Hotspot' : 'Nominal'}
                  </span>
                </div>
                <div className="inspector-body">
                  <div className="inspector-zone-name">
                    <span
                      className="inspector-dot"
                      style={{ backgroundColor: getSeverityColor(currentSelectedZone.severity) }}
                    />
                    <span>{currentSelectedZone.name}</span>
                  </div>
                  <div className="inspector-stats-grid">
                    <div>
                      <span className="stat-label">Elevation:</span>{' '}
                      <strong className="stat-val">{currentSelectedZone.elevation_m.toFixed(1)}m</strong>
                    </div>
                    <div>
                      <span className="stat-label">Rainfall:</span>{' '}
                      <strong className="stat-val">{currentSelectedZone.rainfall_mm.toFixed(0)}mm</strong>
                    </div>
                    <div>
                      <span className="stat-label">Drainage:</span>{' '}
                      <strong className="stat-val">{currentSelectedZone.drainage_capacity_cms}m³/s</strong>
                    </div>
                    <div>
                      <span className="stat-label">Assets:</span>{' '}
                      <strong className="stat-val">
                        {currentSelectedZone.critical_infrastructure_count} facilities
                      </strong>
                    </div>
                    <div>
                      <span className="stat-label">Risk score:</span>{' '}
                      <strong
                        className="stat-val font-mono"
                        style={{ color: getSeverityColor(currentSelectedZone.severity) }}
                      >
                        {(currentSelectedZone.risk_score > 1.0
                          ? currentSelectedZone.risk_score
                          : currentSelectedZone.risk_score * 100
                        ).toFixed(1)}
                      </strong>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Schematic SVG Vector Overlay */}
            <svg className="overview-svg-canvas" viewBox="0 0 100 100" preserveAspectRatio="none">
              <defs>
                <linearGradient id="riverFlowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#0284c7" stopOpacity="0.8" />
                </linearGradient>
                <radialGradient id="inundationZoneA" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#dc2626" stopOpacity="0.3" />
                  <stop offset="80%" stopColor="#dc2626" stopOpacity="0.1" />
                  <stop offset="100%" stopColor="#dc2626" stopOpacity="0" />
                </radialGradient>
              </defs>

              {/* River Artery */}
              <path
                d="M 18,0 Q 24,30 30,50 T 40,82 T 32,100"
                fill="none"
                stroke="url(#riverFlowGrad)"
                strokeWidth="6"
                strokeLinecap="round"
              />

              {/* Basin Spillway */}
              <circle
                cx="34"
                cy="80"
                r="13"
                fill="#0284c7"
                fillOpacity="0.18"
                stroke="#38bdf8"
                strokeWidth="0.5"
                strokeDasharray="2,2"
              />

              {/* Inundation polygons if flood layer active */}
              {activeMapLayer === 'flood' && (
                <>
                  <ellipse cx="28" cy="42" rx="14" ry="10" fill="url(#inundationZoneA)" />
                  <circle cx="58" cy="32" r="11" fill="#f59e0b" fillOpacity="0.14" />
                </>
              )}

              {/* Connecting Drainage Vectors */}
              <line x1="28" y1="42" x2="58" y2="32" stroke="#94a3b8" strokeWidth="0.8" strokeDasharray="1,2" />
              <line x1="58" y1="32" x2="76" y2="68" stroke="#94a3b8" strokeWidth="0.8" strokeDasharray="1,2" />
              <line x1="28" y1="42" x2="34" y2="80" stroke="#94a3b8" strokeWidth="0.8" strokeDasharray="1,2" />
            </svg>

            {/* Zone Centroid Markers */}
            {scenarioDetail?.zones.map((zone) => {
              const isSelected = zone.zone_id === activeSelectedZoneId;
              const severityColor = getSeverityColor(zone.severity);

              return (
                <div
                  key={zone.zone_id}
                  className={`overview-marker-container ${isSelected ? 'marker-selected' : ''}`}
                  style={{
                    left: `${zone.schematic_x}%`,
                    top: `${zone.schematic_y}%`,
                  }}
                  onClick={() => setSelectedZoneId(zone.zone_id)}
                  title={`${zone.name} (${zone.zone_id})`}
                >
                  <div
                    className="overview-marker-pin"
                    style={{
                      borderColor: severityColor,
                      boxShadow: isSelected ? `0 0 12px ${severityColor}` : '0 1px 3px rgba(0,0,0,0.1)',
                    }}
                  >
                    {zone.is_hotspot ? (
                      <Flame size={13} className="text-red" />
                    ) : (
                      <MapPin size={13} style={{ color: severityColor }} />
                    )}
                  </div>
                  <div className="overview-marker-tag">
                    <span className="marker-tag-id">{zone.zone_id}</span>
                    <span className="marker-tag-name">{zone.name.split(' ')[0]}</span>
                  </div>
                </div>
              );
            })}

            {/* Safe Points overlay */}
            {(activeMapLayer === 'safe' || activeMapLayer === 'flood') &&
              scenarioDetail?.safe_points?.map((sp) => {
                const spCoords: Record<string, { x: number; y: number }> = {
                  'SP-01': { x: 82, y: 62 },
                  'SP-02': { x: 62, y: 20 },
                  'SP-03': { x: 80, y: 78 },
                };
                const pos = spCoords[sp.safe_point_id] || { x: 50, y: 50 };

                return (
                  <div
                    key={sp.safe_point_id}
                    className="overview-safe-point"
                    style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
                    title={`Safe Point: ${sp.name}`}
                  >
                    <div className="safe-point-icon">
                      <ShieldCheck size={11} className="text-green" />
                    </div>
                    <span className="safe-point-label">{sp.safe_point_id}</span>
                  </div>
                );
              })}

            {/* Map Legend */}
            <div className="overview-map-legend">
              <div className="legend-entry">
                <span className="legend-dot" style={{ backgroundColor: '#dc2626' }} />
                <span>Critical (&ge;50.0 Hotspot)</span>
              </div>
              <div className="legend-entry">
                <span className="legend-dot" style={{ backgroundColor: '#d97706' }} />
                <span>Elevated (30&ndash;50)</span>
              </div>
              <div className="legend-entry">
                <span className="legend-dot" style={{ backgroundColor: '#16a34a' }} />
                <span>Nominal (&lt;30)</span>
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: Top 3 Interventions + Consequence Summary */}
        <div className="overview-right-column">
          {/* 1. Top 3 Ranked Interventions */}
          <section className="overview-side-card">
            <div className="overview-card-header">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-brand-forest" />
                <h2 className="overview-card-title">TOP INTERVENTIONS</h2>
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                {isAnalysisActive ? 'Ranked by Algorithm 10' : 'Candidate Actions'}
              </span>
            </div>

            <div className="side-card-content">
              {isAnalysisActive ? (
                isMonitoringOnly ? (
                  <div className="side-empty-box">
                    <ShieldCheck size={20} className="text-brand-forest mb-1" />
                    <p className="font-semibold text-xs text-slate-base">MONITORING_ONLY</p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      No priority hotspots qualified. Interventions withheld to preserve physical inventory.
                    </p>
                  </div>
                ) : topFeasibleInterventions.length > 0 ? (
                  <div className="intervention-item-list">
                    {topFeasibleInterventions.map((item, idx) => (
                      <div
                        key={item.intervention_id}
                        className={`intervention-mini-card ${idx === 0 ? 'top-ranked' : ''}`}
                      >
                        <div className="mini-card-top">
                          <div className="flex items-center gap-2">
                            <span className="rank-badge">#{idx + 1}</span>
                            <span className="mini-card-title">{item.name}</span>
                          </div>
                          <span className="kpi-chip chip-green">Feasible</span>
                        </div>
                        <div className="mini-card-meta">
                          <span>
                            Target: <strong>{item.target_node}</strong>
                          </span>
                          <span>&bull;</span>
                          <span>
                            Reduces Risk: <strong>{(item.measures.risk_reduction * 100).toFixed(0)}%</strong>
                          </span>
                          <span>&bull;</span>
                          <span>
                            Score: <strong>{item.score.toFixed(3)}</strong>
                          </span>
                        </div>
                        <div className="mini-card-bottom">
                          <div className="resource-req-tags">
                            {Object.entries(item.required_resources).map(([r, q]) => (
                              <span key={r} className="mini-sku-tag">
                                {r}: {String(q)}
                              </span>
                            ))}
                          </div>
                          {onNavigateTab && (
                            <button
                              type="button"
                              className="btn-action-link"
                              onClick={() => onNavigateTab('interventions')}
                            >
                              Review &rarr;
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="side-empty-box">
                    <AlertTriangle size={20} className="text-amber mb-1" />
                    <p className="font-semibold text-xs text-slate-base">No Feasible Interventions</p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Depot resources or feasibility constraints blocked candidate actions.
                    </p>
                  </div>
                )
              ) : (
                <div className="side-empty-box">
                  <Play size={20} className="text-brand-forest mb-1" />
                  <p className="font-semibold text-xs text-slate-base">Analysis Required</p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Run flood analysis to calculate resource feasibility and multi-criteria rankings.
                  </p>
                </div>
              )}
            </div>

            {/* Link to Full Interventions Tab */}
            {onNavigateTab && (
              <div className="side-card-footer">
                <span className="text-[11px] text-slate-500">
                  {scenarioDetail?.interventions?.length ?? 0} total candidates
                </span>
                <button
                  type="button"
                  className="footer-nav-link"
                  onClick={() => onNavigateTab('interventions')}
                >
                  <span>View all interventions</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            )}
          </section>

          {/* 2. Concise Consequence Summary */}
          <section className="overview-side-card">
            <div className="overview-card-header">
              <div className="flex items-center gap-2">
                <Zap size={16} className="text-brand-forest" />
                <h2 className="overview-card-title">CONSEQUENCE SUMMARY</h2>
              </div>
              <span className="text-[11px] text-slate-500 font-medium">Cascade Infrastructure</span>
            </div>

            <div className="side-card-content">
              {isAnalysisActive ? (
                isMonitoringOnly ? (
                  <div className="side-empty-box">
                    <CheckCircle2 size={20} className="text-green mb-1" />
                    <p className="font-semibold text-xs text-slate-base">Cascade Bypassed</p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Zero priority hotspots qualified; cascade propagation safely suppressed.
                    </p>
                  </div>
                ) : analysisResult.cascade_analysis ? (
                  <div className="consequence-chain-flow">
                    {/* Step 1: Root Inundation */}
                    <div className="chain-step">
                      <div className="chain-step-num num-critical">1</div>
                      <div className="chain-step-body">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-xs text-slate-base">
                            Sector {analysisResult.highest_risk_zone_name} Spillway
                          </span>
                          <span className="kpi-chip chip-critical">Root Hazard</span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Peak flood risk {analysisResult.highest_risk_score.toFixed(1)} qualifies as priority hotspot.
                        </p>
                      </div>
                    </div>

                    <div className="chain-arrow">&darr;</div>

                    {/* Step 2: Infrastructure Bottleneck */}
                    <div className="chain-step">
                      <div className="chain-step-num num-amber">2</div>
                      <div className="chain-step-body">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-xs text-slate-base">
                            {topCriticalNode ? topCriticalNode.label : 'Primary Utility Hub'}
                          </span>
                          <span className="kpi-chip chip-amber">Key Bottleneck</span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {cascadeFailedCount} facilities in cascade failure radius;{' '}
                          {cascadeSurvivingCount} nodes operational.
                        </p>
                      </div>
                    </div>

                    {/* Metric summary strip */}
                    <div className="cascade-metric-strip">
                      <div className="metric-col">
                        <span className="metric-strip-lbl">Failed Nodes</span>
                        <span className="metric-strip-val text-red">
                          {cascadeFailedCount}
                        </span>
                      </div>
                      <div className="metric-col">
                        <span className="metric-strip-lbl">Surviving Nodes</span>
                        <span className="metric-strip-val text-green">
                          {cascadeSurvivingCount}
                        </span>
                      </div>
                      <div className="metric-col">
                        <span className="metric-strip-lbl">Cascade Risk</span>
                        <span className="metric-strip-val font-mono">
                          {analysisResult.cascade_analysis.cascade_risk.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="side-empty-box">
                    <Info size={18} className="text-slate-400 mb-1" />
                    <p className="text-[11px] text-slate-500">Consequence analysis data pending.</p>
                  </div>
                )
              ) : (
                <div className="side-empty-box">
                  <Activity size={20} className="text-brand-forest mb-1" />
                  <p className="font-semibold text-xs text-slate-base">Cascade Ready</p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Contains {scenarioDetail?.nodes?.length ?? 0} mapped facilities. Run analysis to trace failure propagation.
                  </p>
                </div>
              )}
            </div>

            {/* Link to Full Consequence Graph Tab */}
            {onNavigateTab && (
              <div className="side-card-footer">
                <span className="text-[11px] text-slate-500">
                  {scenarioDetail?.nodes?.length ?? 0} infrastructure nodes
                </span>
                <button
                  type="button"
                  className="footer-nav-link"
                  onClick={() => onNavigateTab('consequence-graph')}
                >
                  <span>Explore consequence graph</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            )}
          </section>
        </div>
      </div>

      {/* CATCHMENT ZONE TELEMETRY & RISK TABLE */}
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

      {/* TWO COLUMN SECTION: SYSTEM HEALTH & AUTHENTIC RECENT ACTIVITY */}
      <section className="overview-split-grid">
        {/* Core Subsystems Health */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <h3 className="card-heading-sm">
              <Activity size={17} className="text-brand-forest" /> Core Subsystems Health
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
              <XCircle size={18} className="text-red" />
              <div>
                <p className="offline-heading">Backend Core Unavailable</p>
                <p className="offline-subtext">
                  Start uvicorn on port 8000: <code>uvicorn --app-dir backend app.main:app</code>
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Authentic Recent Session Activity */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <h3 className="card-heading-sm">
              <Activity size={17} className="text-brand-forest" /> Recent Session Activity
            </h3>
            <span className="timestamp-tag">Verified Audit Events</span>
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
