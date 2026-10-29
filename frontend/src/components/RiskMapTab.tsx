import React, { useState } from 'react';
import {
  MapPin,
  Flame,
  Shield,
  Info,
} from 'lucide-react';
import type { ScenarioDetail, ScenarioZoneItem } from '../types/api';

interface RiskMapTabProps {
  scenarioDetail: ScenarioDetail | null;
}

export const RiskMapTab: React.FC<RiskMapTabProps> = ({ scenarioDetail }) => {
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(
    scenarioDetail?.zones[0]?.zone_id ?? null
  );

  const selectedZone: ScenarioZoneItem | undefined = scenarioDetail?.zones.find(
    (z) => z.zone_id === selectedZoneId
  );

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return '#ef4444';
      case 'HIGH':
        return '#f97316';
      case 'MEDIUM':
      case 'MODERATE':
      case 'ELEVATED':
        return '#f59e0b';
      case 'LOW':
      case 'NOMINAL':
      default:
        return '#10b981';
    }
  };

  return (
    <div className="tab-pane risk-map-pane">
      {/* Notice Banner */}
      <div className="map-disclaimer-banner">
        <Info size={16} className="text-cyan flex-shrink-0" />
        <span>
          <strong>SYNTHETIC GEOGRAPHIC SCHEMATIC:</strong> Zone boundaries, centroid coordinates, and inundation vectors are illustrative prototype representations. Production GIS mapping with Leaflet raster overlays will ingest live municipal shapefiles in upcoming phases.
        </span>
      </div>

      <div className="map-workspace-layout">
        {/* Schematic Canvas Surface */}
        <div className="schematic-canvas-card">
          <div className="canvas-header">
            <div className="canvas-title-group">
              <span className="canvas-title">Hydraulic Catchment Tactical Grid</span>
              <span className="canvas-coords-tag">Region: Estuary & River Basin (72.82°E, 18.95°N)</span>
            </div>
            <div className="map-legend">
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: '#10b981' }} />
                <span>Low Risk (&lt;0.30)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: '#f59e0b' }} />
                <span>Moderate (0.30–0.65)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: '#f97316' }} />
                <span>High (0.65–0.80)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: '#ef4444' }} />
                <span>Critical (&gt;0.80 Hotspot)</span>
              </div>
            </div>
          </div>

          <div className="schematic-surface">
            {/* SVG Background: River Artery & Drainage Pathways */}
            <svg className="schematic-svg-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
              <defs>
                <linearGradient id="riverGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0284c7" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#0369a1" stopOpacity="0.8" />
                </linearGradient>
              </defs>

              {/* River Arterial Course from North to South-West Estuary */}
              <path
                d="M 20,0 Q 26,30 32,50 T 40,85 T 32,100"
                fill="none"
                stroke="url(#riverGrad)"
                strokeWidth="7"
                strokeLinecap="round"
              />

              {/* Estuary Basin Spillage Area */}
              <circle cx="34" cy="85" r="14" fill="#0369a1" fillOpacity="0.25" stroke="#38bdf8" strokeWidth="0.5" strokeDasharray="2,2" />

              {/* Inter-zone drainage connectivity vectors */}
              <line x1="28" y1="42" x2="58" y2="32" stroke="#1e293b" strokeWidth="1" strokeDasharray="1,2" />
              <line x1="58" y1="32" x2="76" y2="68" stroke="#1e293b" strokeWidth="1" strokeDasharray="1,2" />
              <line x1="28" y1="42" x2="34" y2="80" stroke="#1e293b" strokeWidth="1" strokeDasharray="1,2" />
            </svg>

            {/* Render Catchment Zones */}
            {scenarioDetail?.zones.map((zone) => {
              const isSelected = zone.zone_id === selectedZoneId;
              const severityColor = getSeverityColor(zone.severity);

              return (
                <div
                  key={zone.zone_id}
                  className={`zone-marker-box ${isSelected ? 'zone-selected' : ''}`}
                  style={{
                    left: `${zone.schematic_x}%`,
                    top: `${zone.schematic_y}%`,
                  }}
                  onClick={() => setSelectedZoneId(zone.zone_id)}
                >
                  <div
                    className="zone-marker-pin"
                    style={{
                      borderColor: severityColor,
                      boxShadow: isSelected ? `0 0 16px ${severityColor}` : 'none',
                    }}
                  >
                    {zone.is_hotspot ? (
                      <Flame size={14} className="text-red" />
                    ) : (
                      <MapPin size={14} style={{ color: severityColor }} />
                    )}
                  </div>
                  <div className="zone-marker-label">
                    <span className="zone-marker-id">{zone.zone_id}</span>
                    <span className="zone-marker-name">{zone.name.split(' ')[0]}</span>
                    <span
                      className="zone-marker-score"
                      style={{ color: severityColor }}
                    >
                      {zone.risk_score.toFixed(2)}
                    </span>
                  </div>
                </div>
              );
            })}

            {/* Render Safe Points */}
            {scenarioDetail?.safe_points.map((sp) => {
              // Placed in proximity to safe elevation zones
              const coords: Record<string, { x: number; y: number }> = {
                'SP-01': { x: 82, y: 62 },
                'SP-02': { x: 62, y: 22 },
                'SP-03': { x: 80, y: 78 },
              };
              const pos = coords[sp.safe_point_id] || { x: 50, y: 50 };

              return (
                <div
                  key={sp.safe_point_id}
                  className="safe-point-marker"
                  style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
                  title={`${sp.name} (Capacity: ${sp.capacity_persons} persons)`}
                >
                  <Shield size={12} className="safe-icon" />
                  <span className="safe-label">SHELTER</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Zone Inspector Sidebar */}
        <aside className="map-inspector-card">
          <div className="inspector-header">
            <h3 className="inspector-title">Zone Telemetry Inspector</h3>
            <span className="inspector-subtitle">
              Click any zone pin to inspect hydrological parameters
            </span>
          </div>

          {selectedZone ? (
            <div className="inspector-body">
              <div className="inspector-headline">
                <span className="inspector-zone-id">{selectedZone.zone_id}</span>
                <h4 className="inspector-zone-name">{selectedZone.name}</h4>
                <div className="inspector-badge-row">
                  <span
                    className="severity-pill"
                    style={{
                      borderColor: getSeverityColor(selectedZone.severity),
                      color: getSeverityColor(selectedZone.severity),
                    }}
                  >
                    {selectedZone.severity}
                  </span>
                  {selectedZone.is_hotspot && (
                    <span className="badge-hotspot">
                      <Flame size={12} /> HOTSPOT
                    </span>
                  )}
                </div>
              </div>

              <div className="inspector-stats-grid">
                <div className="inspector-stat">
                  <span className="stat-label">Calculated Risk Index</span>
                  <span
                    className="stat-value-lg"
                    style={{ color: getSeverityColor(selectedZone.severity) }}
                  >
                    {selectedZone.risk_score.toFixed(2)}
                  </span>
                </div>

                <div className="inspector-stat">
                  <span className="stat-label">Cumulative Rainfall</span>
                  <span className="stat-value">{selectedZone.rainfall_mm.toFixed(0)} mm</span>
                </div>

                <div className="inspector-stat">
                  <span className="stat-label">Mean Ground Elevation</span>
                  <span className="stat-value">{selectedZone.elevation_m.toFixed(1)} m</span>
                </div>

                <div className="inspector-stat">
                  <span className="stat-label">Soil Saturation Ratio</span>
                  <span className="stat-value">
                    {(selectedZone.soil_saturation_index * 100).toFixed(0)}%
                  </span>
                </div>

                <div className="inspector-stat">
                  <span className="stat-label">Drainage Throughput</span>
                  <span className="stat-value">{selectedZone.drainage_capacity_cms} m³/s</span>
                </div>

                <div className="inspector-stat">
                  <span className="stat-label">Critical Infrastructure</span>
                  <span className="stat-value text-indigo">
                    {selectedZone.critical_infrastructure_count} Assets
                  </span>
                </div>
              </div>

              {selectedZone.centroid_lat && selectedZone.centroid_lon && (
                <div className="inspector-geo-box">
                  <span className="geo-label">GPS Centroid (Illustrative):</span>
                  <code className="geo-code">
                    {selectedZone.centroid_lat.toFixed(4)}°N, {selectedZone.centroid_lon.toFixed(4)}°E
                  </code>
                </div>
              )}
            </div>
          ) : (
            <div className="inspector-empty">Select a zone pin on the schematic canvas.</div>
          )}
        </aside>
      </div>
    </div>
  );
};
