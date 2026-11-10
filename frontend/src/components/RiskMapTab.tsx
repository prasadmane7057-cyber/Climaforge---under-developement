import React, { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Flame,
  Info,
  MapPin,
  Shield,
} from 'lucide-react';
import type {
  ScenarioAnalysisResponse,
  ScenarioDetail,
} from '../types/api';
import {
  getMapTilerStaticMapUrl,
  isMapTilerConfigured,
  MAPTILER_ATTRIBUTION,
  MAPTILER_ATTRIBUTION_URL,
  type MapTilerStyle,
} from '../services/maptiler';

interface RiskMapTabProps {
  scenarioDetail: ScenarioDetail | null;
  analysisResult?: ScenarioAnalysisResponse | null;
  isLoadingScenario?: boolean;
  isAnalyzing?: boolean;
  analysisError?: string | null;
}

const getSeverityColor = (severity: string) => {
  switch (severity.toUpperCase()) {
    case 'CRITICAL':
      return '#dc2626';
    case 'HIGH':
      return '#d97706';
    case 'MEDIUM':
    case 'MODERATE':
    case 'ELEVATED':
      return '#f59e0b';
    default:
      return '#16a34a';
  }
};

export const RiskMapTab: React.FC<RiskMapTabProps> = ({
  scenarioDetail,
  analysisResult,
  isLoadingScenario = false,
  isAnalyzing = false,
  analysisError = null,
}) => {
  const [selectedZoneIdOverride, setSelectedZoneIdOverride] = useState<string | null>(null);

  // MapTiler Basemap State
  const [maptilerStyle, setMaptilerStyle] = useState<MapTilerStyle | 'schematic'>('schematic');
  const [maptilerError, setMaptilerError] = useState<boolean>(false);
  const isKeyConfigured = useMemo(() => isMapTilerConfigured(), []);

  const zones = scenarioDetail?.zones ?? [];
  const selectedZoneId = selectedZoneIdOverride ?? scenarioDetail?.zones[0]?.zone_id ?? null;
  const setSelectedZoneId = (id: string | null) => setSelectedZoneIdOverride(id);

  const selectedZone = zones.find((zone) => zone.zone_id === selectedZoneId);

  const mapCenter = useMemo(() => {
    if (selectedZone?.centroid_lat != null && selectedZone?.centroid_lon != null) {
      return { lat: selectedZone.centroid_lat, lon: selectedZone.centroid_lon };
    }
    const currentZones = scenarioDetail?.zones ?? [];
    const zonesWithCoords = currentZones.filter(
      (z) => z.centroid_lat != null && z.centroid_lon != null,
    );
    if (zonesWithCoords.length > 0) {
      const avgLat =
        zonesWithCoords.reduce((acc, z) => acc + (z.centroid_lat || 0), 0) /
        zonesWithCoords.length;
      const avgLon =
        zonesWithCoords.reduce((acc, z) => acc + (z.centroid_lon || 0), 0) /
        zonesWithCoords.length;
      return { lat: avgLat, lon: avgLon };
    }
    return { lat: 18.5204, lon: 73.8567 };
  }, [selectedZone, scenarioDetail?.zones]);

  const maptilerStaticUrl = useMemo(() => {
    if (maptilerStyle === 'schematic' || !isKeyConfigured) return null;
    return getMapTilerStaticMapUrl(
      mapCenter.lon,
      mapCenter.lat,
      12,
      900,
      500,
      maptilerStyle,
    );
  }, [mapCenter, isKeyConfigured, maptilerStyle]);
  const safePoints = scenarioDetail?.safe_points ?? [];
  const recommendedSafePoint = safePoints.find((sp) => sp.zone_id === selectedZoneId)
    ?? safePoints.slice().sort((a, b) => (Number(b.elevation_m) || 0) - (Number(a.elevation_m) || 0))[0]
    ?? null;
  const targetSafePointZone = recommendedSafePoint
    ? zones.find((z) => z.zone_id === recommendedSafePoint.zone_id)
    : null;

  const hotspotCount = analysisResult?.hotspot_count
    ?? zones.filter((zone) => zone.is_hotspot).length;
  const highestRisk = analysisResult?.highest_risk_score
    ?? Math.max(0, ...zones.map((zone) => zone.risk_score));
  const insufficientCount = analysisResult?.insufficient_zone_count;
  const hasAnalyzedData = !!analysisResult;
  const isMonitoringOnly = !!analysisResult?.is_monitoring_only
    || analysisResult?.pipeline_status === 'MONITORING_ONLY';

  const statusLabel = isAnalyzing
    ? 'Analysis running'
    : analysisError
      ? 'Analysis error'
      : isMonitoringOnly
        ? 'Monitoring only'
        : analysisResult?.pipeline_status === 'DATA_INSUFFICIENT'
          ? 'Data insufficient'
          : hasAnalyzedData
            ? 'Analysis complete'
            : 'Awaiting analysis';

  const statusClass = isAnalyzing
    ? 'status-running'
    : analysisError || analysisResult?.pipeline_status === 'DATA_INSUFFICIENT'
      ? 'status-alert'
      : isMonitoringOnly
        ? 'status-monitoring'
        : hasAnalyzedData
          ? 'status-ready'
          : 'status-awaiting';

  if (!scenarioDetail || isLoadingScenario) {
    return (
      <div className="tab-pane redesigned-section">
        <div className="section-page-header">
          <div>
            <span className="section-eyebrow">Hazard intelligence</span>
            <h2 className="section-title">Risk map</h2>
            <p className="section-description">Spatial distribution of analyzed flood risk across scenario zones.</p>
          </div>
        </div>
        <div className="redesign-state-card">
          <Activity className="state-icon" size={22} />
          <div>
            <strong>{isLoadingScenario ? 'Loading scenario map' : 'Scenario unavailable'}</strong>
            <span>Zone and schematic data will appear when the scenario is available.</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-pane redesigned-section risk-map-pane">
      <div className="section-page-header">
        <div>
          <span className="section-eyebrow">Hazard intelligence</span>
          <h2 className="section-title">Risk map</h2>
          <p className="section-description">Spatial distribution of flood risk across scenario catchments.</p>
        </div>
        <div className={`analysis-status-chip ${statusClass}`}>
          <span className="status-dot" />
          {statusLabel}
        </div>
      </div>

      <div className="scenario-context-strip">
        <div>
          <span className="context-label">Active scenario</span>
          <strong>{scenarioDetail.name}</strong>
        </div>
        <div>
          <span className="context-label">Data quality</span>
          <strong>{analysisResult?.data_label || scenarioDetail.data_label}</strong>
        </div>
        <div>
          <span className="context-label">Analysis status</span>
          <strong>{analysisResult?.pipeline_status || scenarioDetail.analysis_engine_status}</strong>
        </div>
      </div>

      {analysisError && (
        <div className="redesign-state-card error-state">
          <AlertTriangle size={22} />
          <div><strong>Analysis could not be completed</strong><span>{analysisError}</span></div>
        </div>
      )}

      {isAnalyzing && (
        <div className="redesign-state-card loading-state">
          <Activity className="state-icon" size={22} />
          <div><strong>Running flood analysis</strong><span>Zone risk values and hotspot classifications are being updated.</span></div>
        </div>
      )}

      <div className="risk-summary-grid">
        <div className="risk-summary-card">
          <span>Evaluated zones</span>
          <strong>{analysisResult?.scorable_zone_count ?? zones.length}</strong>
          <small>{insufficientCount ? `${insufficientCount} insufficient` : 'Available zone records'}</small>
        </div>
        <div className="risk-summary-card">
          <span>Hotspots</span>
          <strong className="risk-value-red">{hotspotCount}</strong>
          <small>{hasAnalyzedData ? `Threshold ${analysisResult?.hotspot_threshold_applied ?? 50}` : 'Scenario classification'}</small>
        </div>
        <div className="risk-summary-card">
          <span>Highest risk</span>
          <strong>{highestRisk.toFixed(1)}</strong>
          <small>{analysisResult?.highest_risk_zone_name || scenarioDetail.highest_risk_zone_name || 'No zone identified'}</small>
        </div>
        <div className="risk-summary-card">
          <span>Infrastructure assets</span>
          <strong>{scenarioDetail.critical_infrastructure_count}</strong>
          <small>In the active scenario</small>
        </div>
      </div>

      {zones.length === 0 ? (
        <div className="redesign-state-card empty-state">
          <MapPin size={22} />
          <div><strong>No zone data is available</strong><span>The map cannot be rendered without scenario zone records.</span></div>
        </div>
      ) : (
        <div className="map-workspace-layout redesigned-map-layout">
          <div className="schematic-canvas-card redesigned-map-card">
            <div className="canvas-header">
              <div>
                <span className="canvas-kicker">Scenario schematic</span>
                <h3 className="canvas-title">Catchment zone layout</h3>
              </div>
              <div className="maptiler-style-selector" style={{ margin: '0 8px' }}>
                <button
                  type="button"
                  className={`maptiler-style-btn ${maptilerStyle === 'schematic' ? 'active' : ''}`}
                  onClick={() => setMaptilerStyle('schematic')}
                  title="Schematic Vector View"
                >
                  Schematic
                </button>
                <button
                  type="button"
                  className={`maptiler-style-btn ${maptilerStyle === 'dataviz-dark' ? 'active' : ''}`}
                  onClick={() => {
                    setMaptilerStyle('dataviz-dark');
                    setMaptilerError(false);
                  }}
                  title="MapTiler Dark Basemap"
                >
                  Dark
                </button>
                <button
                  type="button"
                  className={`maptiler-style-btn ${maptilerStyle === 'satellite' ? 'active' : ''}`}
                  onClick={() => {
                    setMaptilerStyle('satellite');
                    setMaptilerError(false);
                  }}
                  title="MapTiler Satellite Basemap"
                >
                  Satellite
                </button>
                <button
                  type="button"
                  className={`maptiler-style-btn ${maptilerStyle === 'topo-v2' ? 'active' : ''}`}
                  onClick={() => {
                    setMaptilerStyle('topo-v2');
                    setMaptilerError(false);
                  }}
                  title="MapTiler Topographic Basemap"
                >
                  Topo
                </button>
              </div>
              <span className="synthetic-badge">SYNTHETIC</span>
            </div>

            <div className="schematic-surface redesigned-schematic">
              {maptilerStaticUrl && !maptilerError && (
                <img
                  className="maptiler-basemap-layer"
                  src={maptilerStaticUrl}
                  alt="MapTiler Basemap Layer"
                  onError={() => setMaptilerError(true)}
                />
              )}
              <svg className="schematic-svg-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                <path d="M 12 8 C 18 28, 20 42, 31 58 S 36 82, 48 96" fill="none" stroke="#3b9c91" strokeOpacity="0.38" strokeWidth="4" strokeLinecap="round" />
                <path d="M 31 58 C 48 54, 68 58, 88 72" fill="none" stroke="#94a3b8" strokeOpacity="0.55" strokeWidth="0.8" strokeDasharray="2 2" />
                <path d="M 20 42 C 38 38, 50 32, 72 28" fill="none" stroke="#94a3b8" strokeOpacity="0.45" strokeWidth="0.8" strokeDasharray="2 2" />
                {selectedZone && targetSafePointZone && (
                  <line
                    x1={`${selectedZone.schematic_x}%`}
                    y1={`${selectedZone.schematic_y}%`}
                    x2={`${Math.min(92, targetSafePointZone.schematic_x + 3)}%`}
                    y2={`${Math.min(92, targetSafePointZone.schematic_y + 7)}%`}
                    stroke="#16a34a"
                    strokeWidth="2.5"
                    strokeDasharray="4 2"
                    strokeOpacity="0.85"
                    className="m6-map-corridor-active"
                  />
                )}
              </svg>

              {zones.map((zone) => {
                const isSelected = zone.zone_id === selectedZoneId;
                const color = getSeverityColor(zone.severity);
                return (
                  <button
                    type="button"
                    key={zone.zone_id}
                    className={`zone-marker-box redesigned-zone-marker ${isSelected ? 'zone-selected' : ''}`}
                    style={{ left: `${zone.schematic_x}%`, top: `${zone.schematic_y}%` }}
                    onClick={() => setSelectedZoneId(zone.zone_id)}
                    aria-label={`Select ${zone.name}, risk ${zone.risk_score.toFixed(1)}, ${zone.severity}`}
                  >
                    <span className="zone-marker-pin" style={{ borderColor: color }}>
                      {zone.is_hotspot ? <Flame size={14} /> : <MapPin size={14} style={{ color }} />}
                    </span>
                    <span className="zone-marker-label redesigned-zone-label">
                      <span>{zone.zone_id}</span>
                      <strong>{zone.name}</strong>
                      <em style={{ color }}>{zone.risk_score.toFixed(1)}</em>
                    </span>
                  </button>
                );
              })}

              {scenarioDetail.safe_points.map((safePoint, index) => {
                const zone = zones.find((item) => item.zone_id === safePoint.zone_id) ?? zones[index % zones.length];
                if (!zone) return null;
                return (
                  <div
                    key={safePoint.safe_point_id}
                    className="safe-point-marker redesigned-safe-point"
                    style={{ left: `${Math.min(92, zone.schematic_x + 3)}%`, top: `${Math.min(92, zone.schematic_y + 7)}%` }}
                    title={`${safePoint.name}: ${safePoint.capacity_persons} persons`}
                  >
                    <Shield size={12} />
                    <span>{safePoint.name}</span>
                  </div>
                );
              })}
            </div>

            <div className="risk-map-footer">
              <div className="risk-legend redesigned-risk-legend">
                <span><i style={{ background: '#16a34a' }} />Low</span>
                <span><i style={{ background: '#f59e0b' }} />Medium</span>
                <span><i style={{ background: '#d97706' }} />High</span>
                <span><i style={{ background: '#dc2626' }} />Critical</span>
              </div>
              {isKeyConfigured && maptilerStyle !== 'schematic' && (
                <a
                  href={MAPTILER_ATTRIBUTION_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="maptiler-attribution-link"
                >
                  {MAPTILER_ATTRIBUTION}
                </a>
              )}
              <span className="map-context-note"><Info size={13} />Illustrative coordinates; not a production GIS layer</span>
            </div>
          </div>

          <aside className="map-inspector-card redesigned-inspector">
            <div className="inspector-header">
              <span className="inspector-kicker">Selected zone</span>
              <h3>Zone inspector</h3>
            </div>
            {selectedZone ? (
              <div className="inspector-body">
                <div className="selected-zone-heading">
                  <span>{selectedZone.zone_id}</span>
                  <h4>{selectedZone.name}</h4>
                  <div className="selected-zone-badges">
                    <span className="severity-pill" style={{ borderColor: getSeverityColor(selectedZone.severity), color: getSeverityColor(selectedZone.severity) }}>
                      {selectedZone.severity}
                    </span>
                    {selectedZone.is_hotspot && <span className="badge-hotspot"><Flame size={12} />Hotspot</span>}
                  </div>
                </div>
                <div className="inspector-risk-score">
                  <span>Risk index</span>
                  <strong style={{ color: getSeverityColor(selectedZone.severity) }}>{selectedZone.risk_score.toFixed(1)}</strong>
                </div>
                <dl className="zone-telemetry-list">
                  <div><dt>Rainfall</dt><dd>{selectedZone.rainfall_mm.toFixed(1)} mm</dd></div>
                  <div><dt>Elevation</dt><dd>{selectedZone.elevation_m.toFixed(1)} m</dd></div>
                  <div><dt>Soil saturation</dt><dd>{(selectedZone.soil_saturation_index * 100).toFixed(0)}%</dd></div>
                  <div><dt>Drainage capacity</dt><dd>{selectedZone.drainage_capacity_cms.toFixed(2)} m³/s</dd></div>
                  <div><dt>Infrastructure</dt><dd>{selectedZone.critical_infrastructure_count} assets</dd></div>
                  <div><dt>Population</dt><dd>{selectedZone.population != null ? selectedZone.population.toLocaleString() : 'Not available'}</dd></div>
                </dl>
                {(selectedZone.centroid_lat != null && selectedZone.centroid_lon != null) ? (
                  <div className="inspector-geo-box">
                    <span>Illustrative centroid</span>
                    <code>{selectedZone.centroid_lat.toFixed(4)}, {selectedZone.centroid_lon.toFixed(4)}</code>
                  </div>
                ) : (
                  <div className="inspector-geo-box"><span>Coordinate status</span><strong>Not provided</strong></div>
                )}
                {recommendedSafePoint && (
                  <div style={{ marginTop: '12px', padding: '10px', background: 'var(--surface-muted)', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Shield size={12} /> Designated Evacuation Refuge
                    </span>
                    <h5 style={{ margin: '4px 0', fontSize: '0.8rem', color: 'var(--text-primary)' }}>{recommendedSafePoint.name}</h5>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      Zone: {recommendedSafePoint.zone_id} · Elevation: {recommendedSafePoint.elevation_m}m · Capacity: {Number(recommendedSafePoint.capacity_persons).toLocaleString()} persons
                    </div>
                    <div style={{ fontSize: '0.6rem', color: '#64748b', marginTop: '3px' }}>
                      Active evacuation corridor highlighted on map (Simulated safe shelter)
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="inspector-empty">Select a zone to inspect its available telemetry.</div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
};
