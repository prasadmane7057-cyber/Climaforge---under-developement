import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  CloudRain,
  Droplets,
  Wind,
  Thermometer,
  MapPin,
  RefreshCw,
  AlertTriangle,
  Layers,
  Crosshair,
  ExternalLink,
  ShieldCheck,
  Calendar,
  Waves,
} from 'lucide-react';
import type {
  IndrayaniMonitoringResponse,
  RiverHistoricalRecord,
  RiverStationReference,
  WeatherForecastResponse,
} from '../types/environmental';
import {
  fetchIndrayaniHistory,
  fetchIndrayaniMonitoring,
  fetchIndrayaniStations,
  fetchWeatherForecast,
} from '../services/environmentalApi';
import {
  GEOLOCATION_PRESETS,
  requestBrowserPosition,
  type GeolocationPositionResult,
} from '../services/geolocation';
import {
  getMapTilerStaticMapUrl,
  isMapTilerConfigured,
  MAPTILER_ATTRIBUTION,
  MAPTILER_ATTRIBUTION_URL,
  type MapTilerStyle,
} from '../services/maptiler';
import { CartographicMap } from './CartographicMap';
import './EnvironmentalTab.css';

// Geographic bounds for Indrayani River Corridor in Pune District
const BOUNDS = {
  minLat: 18.52,
  maxLat: 18.78,
  minLon: 73.70,
  maxLon: 74.08,
};

function projectX(lon: number): number {
  const norm = (lon - BOUNDS.minLon) / (BOUNDS.maxLon - BOUNDS.minLon);
  return Math.min(94, Math.max(6, norm * 100));
}

function projectY(lat: number): number {
  const norm = (BOUNDS.maxLat - lat) / (BOUNDS.maxLat - BOUNDS.minLat);
  return Math.min(94, Math.max(6, norm * 100));
}

export const EnvironmentalTab: React.FC = () => {
  // Coordinates & Location State
  const defaultPreset = GEOLOCATION_PRESETS[0]; // Moshi MPCB
  const [coords, setCoords] = useState<{
    latitude: number;
    longitude: number;
    accuracyMeters: number | null;
    source: 'GPS_BROWSER' | 'MANUAL_PRESET' | 'MANUAL_COORDINATES';
    presetName?: string;
  }>({
    latitude: defaultPreset.latitude,
    longitude: defaultPreset.longitude,
    accuracyMeters: null,
    source: 'MANUAL_PRESET',
    presetName: defaultPreset.name,
  });

  const [selectedPresetId, setSelectedPresetId] = useState<string>(defaultPreset.id);
  const [latInput, setLatInput] = useState<string>(defaultPreset.latitude.toString());
  const [lonInput, setLonInput] = useState<string>(defaultPreset.longitude.toString());
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  // Data State
  const [weatherData, setWeatherData] = useState<WeatherForecastResponse | null>(null);
  const [indrayaniData, setIndrayaniData] = useState<IndrayaniMonitoringResponse | null>(null);
  const [corridorStations, setCorridorStations] = useState<RiverStationReference[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('MPCB-INDRAYANI-MOSHI-11');
  const [historicalRecords, setHistoricalRecords] = useState<RiverHistoricalRecord[]>([]);

  // View & Filter State
  const [activeLayer, setActiveLayer] = useState<'ALL' | 'LIVE' | 'FORECAST' | 'HISTORICAL'>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // MapTiler Basemap State
  const [maptilerStyle, setMaptilerStyle] = useState<MapTilerStyle | 'schematic'>('dataviz-dark');
  const [maptilerError, setMaptilerError] = useState<boolean>(false);
  const isKeyConfigured = useMemo(() => isMapTilerConfigured(), []);

  const maptilerStaticUrl = useMemo(() => {
    if (maptilerStyle === 'schematic' || !isKeyConfigured) return null;
    return getMapTilerStaticMapUrl(
      coords.longitude,
      coords.latitude,
      11,
      900,
      500,
      maptilerStyle,
    );
  }, [coords.longitude, coords.latitude, isKeyConfigured, maptilerStyle]);

  // Load corridor stations once on mount
  useEffect(() => {
    let isMounted = true;
    fetchIndrayaniStations()
      .then((stations) => {
        if (isMounted) setCorridorStations(stations);
      })
      .catch((err) => {
        console.error('Failed to load corridor stations:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch Environmental Data for Coordinates
  const loadEnvironmentalData = useCallback(
    async (lat: number, lon: number, force = false) => {
      if (force) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setGeneralError(null);

      try {
        const [forecastRes, indrayaniRes] = await Promise.all([
          fetchWeatherForecast(lat, lon, undefined, force),
          fetchIndrayaniMonitoring(selectedStationId, force),
        ]);

        setWeatherData(forecastRes);
        setIndrayaniData(indrayaniRes);
      } catch (err) {
        setGeneralError(
          err instanceof Error ? err.message : 'Failed to retrieve environmental data.',
        );
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [selectedStationId],
  );

  // Fetch Station History when selected station changes
  useEffect(() => {
    let isMounted = true;
    fetchIndrayaniHistory(selectedStationId)
      .then((records) => {
        if (isMounted) setHistoricalRecords(records);
      })
      .catch((err) => {
        console.error('Failed to load station history:', err);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedStationId]);

  // Initial load or coordinate update
  useEffect(() => {
    loadEnvironmentalData(coords.latitude, coords.longitude, false);
  }, [coords.latitude, coords.longitude, loadEnvironmentalData]);

  // Browser GPS Trigger
  const handleRequestGPS = async () => {
    setIsLocating(true);
    setLocationError(null);
    try {
      const position: GeolocationPositionResult = await requestBrowserPosition();
      setCoords({
        latitude: position.latitude,
        longitude: position.longitude,
        accuracyMeters: position.accuracyMeters,
        source: 'GPS_BROWSER',
      });
      setLatInput(position.latitude.toFixed(5));
      setLonInput(position.longitude.toFixed(5));
      setSelectedPresetId('custom');
    } catch (err) {
      setLocationError(err instanceof Error ? err.message : 'Failed to acquire GPS position.');
    } finally {
      setIsLocating(false);
    }
  };

  // Preset Selection Change
  const handleSelectPreset = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const presetId = e.target.value;
    setSelectedPresetId(presetId);
    if (presetId === 'custom') return;

    const preset = GEOLOCATION_PRESETS.find((p) => p.id === presetId);
    if (preset) {
      setCoords({
        latitude: preset.latitude,
        longitude: preset.longitude,
        accuracyMeters: null,
        source: 'MANUAL_PRESET',
        presetName: preset.name,
      });
      setLatInput(preset.latitude.toString());
      setLonInput(preset.longitude.toString());
      setLocationError(null);
    }
  };

  // Manual Coordinates Apply
  const handleApplyCoordinates = (e: React.FormEvent) => {
    e.preventDefault();
    const lat = parseFloat(latInput);
    const lon = parseFloat(lonInput);

    if (isNaN(lat) || isNaN(lon)) {
      setLocationError('Latitude and longitude must be valid numerical values.');
      return;
    }
    if (lat < -90 || lat > 90) {
      setLocationError('Latitude must be between -90 and 90 degrees.');
      return;
    }
    if (lon < -180 || lon > 180) {
      setLocationError('Longitude must be between -180 and 180 degrees.');
      return;
    }

    setLocationError(null);
    setSelectedPresetId('custom');
    setCoords({
      latitude: lat,
      longitude: lon,
      accuracyMeters: null,
      source: 'MANUAL_COORDINATES',
    });
  };

  // Selected station object
  const activeStation = useMemo(() => {
    return (
      corridorStations.find((s) => s.station_id === selectedStationId) ||
      indrayaniData?.primary_reference_station ||
      null
    );
  }, [corridorStations, indrayaniData, selectedStationId]);

  // Projected River Path coordinates for SVG
  const riverPoints = useMemo(() => {
    // Corridor order: Dehu -> Moshi -> Alandi -> Tulapur
    const dehuX = projectX(73.768);
    const dehuY = projectY(18.718);
    const moshiX = projectX(73.87855);
    const moshiY = projectY(18.68365);
    const alandiX = projectX(73.896);
    const alandiY = projectY(18.677);
    const tulapurX = projectX(74.015);
    const tulapurY = projectY(18.577);

    return `M ${dehuX.toFixed(1)} ${dehuY.toFixed(1)} C ${((dehuX + moshiX) / 2).toFixed(1)} ${((dehuY + moshiY) / 2 - 3).toFixed(1)}, ${moshiX.toFixed(1)} ${moshiY.toFixed(1)}, ${moshiX.toFixed(1)} ${moshiY.toFixed(1)} S ${alandiX.toFixed(1)} ${alandiY.toFixed(1)}, ${alandiX.toFixed(1)} ${alandiY.toFixed(1)} S ${tulapurX.toFixed(1)} ${tulapurY.toFixed(1)}, ${tulapurX.toFixed(1)} ${tulapurY.toFixed(1)}`;
  }, []);

  const currentObs = weatherData?.current;
  const imd = indrayaniData?.imd_warnings;

  return (
    <div className="tab-pane environmental-container">
      {/* 1. Header Bar */}
      <div className="env-header-bar">
        <div className="env-title-group">
          <span className="env-eyebrow">
            <Waves size={15} /> Real-Time Environmental Intelligence
          </span>
          <h2 className="env-title">Indrayani River Basin & Weather Surveillance</h2>
          <p className="env-subtitle">
            Pune District, Maharashtra, India &bull; Hyperlocal weather forecasting, IMD alerts &amp; verified MPCB environmental monitoring reference.
          </p>
        </div>

        <div className="env-actions-group">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleRequestGPS}
            disabled={isLocating}
          >
            <Crosshair size={14} className={isLocating ? 'spin-icon' : ''} />
            <span>{isLocating ? 'Locating...' : 'Use My GPS'}</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => loadEnvironmentalData(coords.latitude, coords.longitude, true)}
            disabled={isRefreshing || isLoading}
          >
            <RefreshCw size={14} className={isRefreshing ? 'spin-icon' : ''} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Intel'}</span>
          </button>
        </div>
      </div>

      {/* 2. Location Controls Toolbar */}
      <div className="env-location-toolbar">
        <div className="location-controls-left">
          <label htmlFor="env-preset-select" className="meta-label">
            Location Preset:
          </label>
          <select
            id="env-preset-select"
            className="location-preset-select"
            value={selectedPresetId}
            onChange={handleSelectPreset}
          >
            {GEOLOCATION_PRESETS.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.name} {preset.isRiverCorridor ? '• [River Corridor]' : ''}
              </option>
            ))}
            <option value="custom">Custom Coordinates / GPS</option>
          </select>
        </div>

        <form className="location-controls-right" onSubmit={handleApplyCoordinates}>
          <div className="coord-inputs-group">
            <span className="meta-label">Lat:</span>
            <input
              type="text"
              className="coord-input"
              value={latInput}
              onChange={(e) => setLatInput(e.target.value)}
              placeholder="18.6836"
              aria-label="Latitude"
            />
            <span className="meta-label">Lon:</span>
            <input
              type="text"
              className="coord-input"
              value={lonInput}
              onChange={(e) => setLonInput(e.target.value)}
              placeholder="73.8785"
              aria-label="Longitude"
            />
            <button type="submit" className="btn btn-secondary btn-sm">
              Apply
            </button>
          </div>

          <div
            className={`location-badge ${
              coords.source === 'GPS_BROWSER' ? 'gps' : 'preset'
            }`}
          >
            <MapPin size={12} />
            <span>
              {coords.latitude.toFixed(4)}°, {coords.longitude.toFixed(4)}°
              {coords.accuracyMeters != null
                ? ` (±${Math.round(coords.accuracyMeters)}m)`
                : ''}
            </span>
          </div>
        </form>
      </div>

      {locationError && (
        <div className="redesign-state-card error-state">
          <AlertTriangle size={18} />
          <div>
            <strong>Location Notice</strong>
            <span>{locationError}</span>
          </div>
        </div>
      )}

      {generalError && (
        <div className="redesign-state-card error-state">
          <AlertTriangle size={18} />
          <div>
            <strong>Data Acquisition Error</strong>
            <span>{generalError}</span>
          </div>
        </div>
      )}

      {/* 3. Official Scientific & Hydrological Honesty Disclaimer */}
      <div className="env-disclaimer-card">
        <ShieldCheck size={26} className="disclaimer-icon" />
        <div className="disclaimer-body">
          <div className="disclaimer-title">
            Verified Geographical Environmental Reference &bull; MPCB Station 11 (Moshi)
          </div>
          <div className="disclaimer-text">
            <strong>Critical Scientific &amp; Safety Notice:</strong> The Moshi reference point (Lat: 18.68365, Lon: 73.87855, Taluka Haveli, Pune) is an official Maharashtra Pollution Control Board (MPCB) surface-water quality monitoring reference. Automated live flood-level telemetry (CWC / India-WRIS) is currently unmonitored at this site. <em>Indrayani River telemetry currently unavailable.</em> Never extrapolate unverified flood stage heights or certified safe crossings without emergency authority confirmation.
          </div>
          <div className="disclaimer-badges">
            <span className="badge-notice">SURFACE WATER QUALITY REFERENCE</span>
            <span className="badge-telemetry-unavailable">FLOOD TELEMETRY NOT VERIFIED</span>
            <span className="badge-notice">MPCB STATION 11</span>
          </div>
        </div>
      </div>

      {/* 4. Real-Time Ambient Weather KPI Grid */}
      <div className="env-kpi-grid">
        <div className="env-kpi-card">
          <div className="kpi-header">
            <span>Ambient Temperature</span>
            <Thermometer size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {currentObs?.temperature_c != null ? `${currentObs.temperature_c.toFixed(1)}` : '—'}
            </span>
            <span className="kpi-unit">°C</span>
          </div>
          <span className="kpi-subtext">
            {currentObs?.weather_description || 'Open-Meteo Hyperlocal'}
          </span>
        </div>

        <div className="env-kpi-card">
          <div className="kpi-header">
            <span>Precipitation (Current)</span>
            <CloudRain size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {currentObs?.precipitation_mm != null ? `${currentObs.precipitation_mm.toFixed(1)}` : '0.0'}
            </span>
            <span className="kpi-unit">mm</span>
          </div>
          <span className="kpi-subtext">Rain rate: {currentObs?.rain_mm != null ? `${currentObs.rain_mm.toFixed(1)} mm/h` : '0.0 mm/h'}</span>
        </div>

        <div className="env-kpi-card">
          <div className="kpi-header">
            <span>24h Expected Rainfall</span>
            <Droplets size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {indrayaniData?.rainfall_forecast_24h_mm != null
                ? `${indrayaniData.rainfall_forecast_24h_mm.toFixed(1)}`
                : '—'}
            </span>
            <span className="kpi-unit">mm</span>
          </div>
          <span className="kpi-subtext">
            Max Probability: {indrayaniData?.rainfall_probability_max_pct ?? 0}%
          </span>
        </div>

        <div className="env-kpi-card">
          <div className="kpi-header">
            <span>Relative Humidity</span>
            <Droplets size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {currentObs?.relative_humidity_pct != null
                ? `${Math.round(currentObs.relative_humidity_pct)}`
                : '—'}
            </span>
            <span className="kpi-unit">%</span>
          </div>
          <span className="kpi-subtext">Atmospheric moisture</span>
        </div>

        <div className="env-kpi-card">
          <div className="kpi-header">
            <span>Wind Conditions</span>
            <Wind size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-value">
              {currentObs?.wind_speed_kmh != null
                ? `${currentObs.wind_speed_kmh.toFixed(1)}`
                : '—'}
            </span>
            <span className="kpi-unit">km/h</span>
          </div>
          <span className="kpi-subtext">
            Bearing: {currentObs?.wind_direction_deg != null ? `${Math.round(currentObs.wind_direction_deg)}°` : '—'}
          </span>
        </div>
      </div>

      {/* 5. Two-Column Layout: Interactive Map + Side Intelligence Panel */}
      <div className="env-split-layout">
        {/* Left Column: Interactive Indrayani Corridor SVG Map */}
        <div className="env-map-card">
          <div className="map-card-header">
            <div className="map-card-title">
              <Layers size={17} />
              <span>Indrayani River Corridor &bull; Pune Basin Map</span>
            </div>

            <div className="maptiler-style-selector">
              <span className="maptiler-style-label">Basemap:</span>
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
                title="MapTiler Satellite Imagery"
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
                title="MapTiler Topographic Terrain"
              >
                Topo
              </button>
              <button
                type="button"
                className={`maptiler-style-btn ${maptilerStyle === 'schematic' ? 'active' : ''}`}
                onClick={() => setMaptilerStyle('schematic')}
                title="Schematic Vector Grid"
              >
                Grid
              </button>
              {isKeyConfigured && maptilerStyle !== 'schematic' && !maptilerError && (
                <span className="maptiler-badge-live">MapTiler Active</span>
              )}
              {isKeyConfigured && maptilerError && (
                <span className="maptiler-badge-fallback">Fallback (Grid)</span>
              )}
              {!isKeyConfigured && (
                <span className="maptiler-badge-fallback">No Key (Grid)</span>
              )}
            </div>

            <div className="layer-toggle-group">
              <button
                type="button"
                className={`layer-btn ${activeLayer === 'ALL' ? 'active' : ''}`}
                onClick={() => setActiveLayer('ALL')}
              >
                All Layers
              </button>
              <button
                type="button"
                className={`layer-btn ${activeLayer === 'LIVE' ? 'active' : ''}`}
                onClick={() => setActiveLayer('LIVE')}
              >
                Live Stations
              </button>
              <button
                type="button"
                className={`layer-btn ${activeLayer === 'FORECAST' ? 'active' : ''}`}
                onClick={() => setActiveLayer('FORECAST')}
              >
                Rain Forecast
              </button>
              <button
                type="button"
                className={`layer-btn ${activeLayer === 'HISTORICAL' ? 'active' : ''}`}
                onClick={() => setActiveLayer('HISTORICAL')}
              >
                MPCB History
              </button>
            </div>
          </div>

          <div className="map-canvas-container">
            {maptilerStaticUrl && !maptilerError && (
              <img
                className="maptiler-basemap-layer"
                src={maptilerStaticUrl}
                alt="MapTiler Basemap Layer"
                onError={() => setMaptilerError(true)}
              />
            )}
            <svg
              className="river-corridor-svg"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-label="Indrayani River Schematic Map"
            >
              {/* Background Geographic Grid */}
              <defs>
                <pattern id="grid-pattern" width="10" height="10" patternUnits="userSpaceOnUse">
                  <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#1e293b" strokeWidth="0.5" />
                </pattern>
                <linearGradient id="riverGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.85" />
                  <stop offset="50%" stopColor="#0284c7" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#0369a1" stopOpacity="0.85" />
                </linearGradient>
              </defs>

              <rect
                width="100"
                height="100"
                fill={maptilerStaticUrl && !maptilerError ? 'transparent' : 'url(#grid-pattern)'}
              />

              {/* Bhima River Confluence Baseline (Schematic Confluence Line at Tulapur) */}
              <path
                d="M 80 15 C 84 45, 87 75, 95 98"
                fill="none"
                stroke="#1e3a8a"
                strokeWidth="2.8"
                strokeOpacity="0.5"
                strokeDasharray="2 2"
              />
              <text x="84" y="25" fill="#64748b" fontSize="2.8" fontWeight="600">
                Bhima River
              </text>

              {/* Indrayani River Corridor Path */}
              <path
                d={riverPoints}
                fill="none"
                stroke="url(#riverGradient)"
                strokeWidth="3.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* River Flow Direction Indicators */}
              <text x="32" y="30" fill="#38bdf8" fontSize="2.4" fontWeight="600" opacity="0.8">
                Indrayani Flow &rarr;
              </text>

              {/* Corridor Stations */}
              {corridorStations.map((station) => {
                const sx = projectX(station.longitude);
                const sy = projectY(station.latitude);
                const isSelected = station.station_id === selectedStationId;
                const isPrimary = station.station_id === 'MPCB-INDRAYANI-MOSHI-11';

                return (
                  <g
                    key={station.station_id}
                    onClick={() => setSelectedStationId(station.station_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Outer pulse if selected */}
                    {isSelected && (
                      <circle
                        cx={sx}
                        cy={sy}
                        r="4.5"
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth="1.2"
                        opacity="0.8"
                      />
                    )}

                    {/* Station Pin */}
                    <circle
                      cx={sx}
                      cy={sy}
                      r={isPrimary ? '2.8' : '2.2'}
                      fill={isPrimary ? '#10b981' : '#38bdf8'}
                      stroke="#ffffff"
                      strokeWidth="0.8"
                    />

                    {/* Label */}
                    <text
                      x={sx + 3.5}
                      y={sy + 1}
                      fill={isSelected ? '#fbbf24' : '#e2e8f0'}
                      fontSize="2.7"
                      fontWeight={isSelected ? '700' : '500'}
                    >
                      {station.station_name}
                      {isPrimary ? ' [MPCB Ref]' : ''}
                    </text>
                  </g>
                );
              })}

              {/* User Location Marker */}
              {(() => {
                const ux = projectX(coords.longitude);
                const uy = projectY(coords.latitude);
                return (
                  <g>
                    {coords.accuracyMeters != null && (
                      <circle
                        cx={ux}
                        cy={uy}
                        r="4"
                        fill="#22c55e"
                        fillOpacity="0.2"
                        stroke="#22c55e"
                        strokeWidth="0.6"
                      />
                    )}
                    <circle cx={ux} cy={uy} r="2.5" fill="#ef4444" stroke="#ffffff" strokeWidth="0.8" />
                    <text x={ux + 3.5} y={uy + 1.2} fill="#ef4444" fontSize="2.8" fontWeight="800">
                      User ({coords.source === 'GPS_BROWSER' ? 'GPS' : 'Point'})
                    </text>
                  </g>
                );
              })()}
            </svg>

            {/* Map Legend */}
            <div className="map-legend">
              <div className="legend-item">
                <div className="legend-swatch" style={{ background: '#0284c7' }} />
                <span>Indrayani River Centerline</span>
              </div>
              <div className="legend-item">
                <div className="legend-swatch" style={{ background: '#10b981' }} />
                <span>MPCB Station 11 (Moshi Ref)</span>
              </div>
              <div className="legend-item">
                <div className="legend-swatch" style={{ background: '#38bdf8' }} />
                <span>Corridor Pilgrimage/Ghat Station</span>
              </div>
              <div className="legend-item">
                <div className="legend-swatch" style={{ background: '#ef4444' }} />
                <span>User Position &amp; Accuracy</span>
              </div>
              {isKeyConfigured && (
                <div className="legend-item maptiler-attribution-item">
                  <a
                    href={MAPTILER_ATTRIBUTION_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="maptiler-attribution-link"
                  >
                    {MAPTILER_ATTRIBUTION}
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: IMD Weather Warnings & Station Inspector */}
        <div className="env-side-panel">
          {/* IMD Warnings Card */}
          <div className="imd-warnings-card">
            <div className="panel-section-title">
              <span>IMD Weather Warnings</span>
              <span className="badge-notice">
                {imd?.provider_status === 'CONFIGURED_LIVE' ? 'LIVE' : 'DISTRICT ADVISORY'}
              </span>
            </div>

            {imd?.warnings && imd.warnings.length > 0 ? (
              imd.warnings.map((warn) => (
                <div key={warn.warning_id} className={`imd-warning-box level-${warn.warning_level}`}>
                  <div className="warning-headline">
                    [{warn.warning_level}] {warn.headline}
                  </div>
                  <div className="warning-desc">{warn.description}</div>
                  <div className="warning-meta">
                    <span>
                      District: {warn.district}, {warn.state}
                    </span>
                    <span>Issued by: {warn.issued_by}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="imd-warning-box level-GREEN">
                <div className="warning-headline">[GREEN] No Active Weather Warnings</div>
                <div className="warning-desc">
                  India Meteorological Department has not posted active severe weather warnings for Pune District.
                </div>
              </div>
            )}
          </div>

          {/* Active Station Inspector Card */}
          {activeStation && (
            <div className="station-inspector-card">
              <div className="panel-section-title">
                <span>Station Reference</span>
                <span className="badge-notice">{activeStation.station_id}</span>
              </div>

              <div className="station-meta-grid">
                <div className="meta-field">
                  <span className="meta-label">Location:</span>
                  <span className="meta-val">
                    {activeStation.village}, {activeStation.taluka}
                  </span>
                </div>
                <div className="meta-field">
                  <span className="meta-label">District / Basin:</span>
                  <span className="meta-val">
                    {activeStation.district} / {activeStation.basin_name}
                  </span>
                </div>
                <div className="meta-field">
                  <span className="meta-label">Coordinates:</span>
                  <span className="meta-val">
                    {activeStation.latitude.toFixed(5)}°N, {activeStation.longitude.toFixed(5)}°E
                  </span>
                </div>
                <div className="meta-field">
                  <span className="meta-label">Monitoring Body:</span>
                  <span className="meta-val">{activeStation.monitoring_body}</span>
                </div>
              </div>

              <div className="redesign-state-card monitoring-state" style={{ padding: '8px 12px' }}>
                <AlertTriangle size={15} />
                <div>
                  <strong style={{ fontSize: '0.78rem' }}>Telemetry Status</strong>
                  <span style={{ fontSize: '0.74rem' }}>
                    {activeStation.telemetry_status}: Telemetry currently unavailable.
                  </span>
                </div>
              </div>

              <div style={{ fontSize: '0.74rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
                <ExternalLink size={12} />
                <span>Citation: {activeStation.source_citation}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 6. 48-Hour Hourly Precipitation Visualizer */}
      {weatherData?.hourly && weatherData.hourly.length > 0 && (
        <div className="hourly-precip-card">
          <div className="panel-section-title">
            <span>Hourly Precipitation &amp; Rain Probability (Next 24 Hours)</span>
            <span style={{ fontSize: '0.76rem', color: '#64748b' }}>
              Source: Open-Meteo High-Resolution Forecast
            </span>
          </div>

          <div className="hourly-chart-container">
            {weatherData.hourly.slice(0, 24).map((item, idx) => {
              const precip = item.precipitation_mm ?? 0;
              const prob = item.precipitation_probability_pct ?? 0;
              const barHeightPct = Math.min(100, Math.max(4, precip * 15)); // Scale 0-7mm to height
              const hourLabel = item.timestamp ? new Date(item.timestamp).getHours() + ':00' : `+${idx}h`;

              return (
                <div key={item.timestamp || idx} className="hourly-col" title={`${precip}mm (${prob}% probability)`}>
                  <span className="hourly-precip-label">{precip > 0 ? `${precip.toFixed(1)}` : '0'}</span>
                  <div className="bar-wrapper">
                    <div
                      className="precip-bar"
                      style={{
                        height: `${barHeightPct}%`,
                        backgroundColor: prob > 50 ? '#0284c7' : '#94a3b8',
                      }}
                    />
                  </div>
                  <span className="hourly-time-label">{hourLabel}</span>
                  <span style={{ fontSize: '0.62rem', color: '#64748b' }}>{prob}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 7. Historical Surface-Water Quality Records Archive (MPCB Station 11) */}
      <div className="historical-records-card">
        <div className="panel-section-title">
          <span>Historical Surface Water Quality Archive &bull; MPCB Station 11</span>
          <span style={{ fontSize: '0.76rem', color: '#64748b' }}>
            Maharashtra Pollution Control Board (National Water Quality Monitoring)
          </span>
        </div>

        {historicalRecords.length > 0 ? (
          <table className="history-table">
            <thead>
              <tr>
                <th>Record Date</th>
                <th>Parameter</th>
                <th>Measured Value</th>
                <th>Unit</th>
                <th>Source Agency</th>
                <th>Notes / Classification</th>
              </tr>
            </thead>
            <tbody>
              {historicalRecords.map((rec, i) => (
                <tr key={`${rec.record_date}-${rec.parameter_name}-${i}`}>
                  <td>
                    <Calendar size={13} style={{ display: 'inline', marginRight: 4, verticalAlign: -1 }} />
                    {rec.record_date}
                  </td>
                  <td><strong>{rec.parameter_name}</strong></td>
                  <td>{rec.measured_value != null ? rec.measured_value : '—'}</td>
                  <td>{rec.unit}</td>
                  <td>{rec.source_agency}</td>
                  <td style={{ fontSize: '0.76rem', color: '#64748b' }}>{rec.disclaimer}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '16px', color: '#64748b', fontSize: '0.84rem' }}>
            No historical records loaded for this station.
          </div>
        )}
      </div>
    </div>
  );
};

