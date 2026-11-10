/**
 * TypeScript contracts for CLIMAFORGE Real-Time Environmental Intelligence
 * and Indrayani River Environmental Monitoring.
 */

export type FreshnessStatus =
  | 'LIVE'
  | 'FORECAST'
  | 'HISTORICAL'
  | 'UNAVAILABLE'
  | 'STALE'
  | 'SIMULATED';

export type QualityStatus =
  | 'VERIFIED_OBSERVATION'
  | 'PROVIDER_ESTIMATE'
  | 'CALCULATED_FORECAST'
  | 'HISTORICAL_ARCHIVE'
  | 'TELEMETRY_UNVERIFIED'
  | 'OFFLINE_FALLBACK'
  | 'UNAVAILABLE';

export interface GeoCoordinate {
  latitude: number;
  longitude: number;
  accuracy_m?: number | null;
  elevation_m?: number | null;
}

export interface WeatherCurrentObservation {
  temperature_c: number | null;
  relative_humidity_pct: number | null;
  precipitation_mm: number | null;
  rain_mm: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  weather_code: number | null;
  weather_description: string | null;
  observation_timestamp: string | null;
  fetched_timestamp: string;
  quality_status: QualityStatus;
  freshness_status: FreshnessStatus;
}

export interface HourlyPrecipitationItem {
  timestamp: string;
  precipitation_mm: number | null;
  rain_mm: number | null;
  precipitation_probability_pct: number | null;
  temperature_c: number | null;
  wind_speed_kmh: number | null;
}

export interface DailyPrecipitationSummary {
  date: string;
  precipitation_sum_mm: number | null;
  precipitation_probability_max_pct: number | null;
  wind_speed_max_kmh: number | null;
  temp_max_c: number | null;
  temp_min_c: number | null;
}

export interface WeatherForecastResponse {
  latitude: number;
  longitude: number;
  location_name?: string | null;
  timezone: string;
  current?: WeatherCurrentObservation | null;
  hourly: HourlyPrecipitationItem[];
  daily: DailyPrecipitationSummary[];
  provider: string;
  attribution: string;
  fetched_timestamp: string;
  freshness_status: FreshnessStatus;
}

export interface IMDWarningItem {
  warning_id: string;
  district: string;
  state: string;
  warning_level: 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'NO_WARNING';
  warning_type: string;
  valid_from?: string | null;
  valid_to?: string | null;
  headline: string;
  description: string;
  issued_by: string;
  source_url?: string | null;
  freshness_status: FreshnessStatus;
}

export interface IMDWarningsResponse {
  district: string;
  state: string;
  provider_status:
    | 'CONFIGURED_LIVE'
    | 'UNCONFIGURED_FALLBACK'
    | 'DISABLED'
    | 'PROVIDER_UNAVAILABLE';
  warnings: IMDWarningItem[];
  fetched_timestamp: string;
  attribution: string;
  disclaimer: string;
}

export interface RiverStationReference {
  station_id: string;
  station_name: string;
  river_name: string;
  basin_name: string;
  village: string;
  taluka: string;
  district: string;
  state: string;
  country: string;
  latitude: number;
  longitude: number;
  station_type:
    | 'WATER_QUALITY_MONITORING_REFERENCE'
    | 'HYDROLOGICAL_GAUGE'
    | 'PILGRIMAGE_GHAT_REFERENCE'
    | 'BASIN_CONFLUENCE_REFERENCE';
  monitoring_body: string;
  source_citation: string;
  telemetry_status:
    | 'TELEMETRY_UNVERIFIED'
    | 'TELEMETRY_UNAVAILABLE'
    | 'TELEMETRY_OPERATIONAL';
  telemetry_available: boolean;
  disclaimer: string;
}

export interface RiverGaugeReading {
  station_id: string;
  observation_timestamp?: string | null;
  water_level_m?: number | null;
  warning_level_m?: number | null;
  danger_level_m?: number | null;
  discharge_cumecs?: number | null;
  trend?: 'RISING' | 'FALLING' | 'STEADY' | 'UNKNOWN' | null;
  data_source: string;
  quality_status: QualityStatus;
  freshness_status: FreshnessStatus;
}

export interface RiverHistoricalRecord {
  station_id: string;
  record_date: string;
  parameter_name: string;
  measured_value: number | null;
  unit: string;
  source_agency: string;
  disclaimer: string;
}

export interface IndrayaniMonitoringResponse {
  river_name: string;
  district: string;
  primary_reference_station: RiverStationReference;
  corridor_stations: RiverStationReference[];
  local_weather?: WeatherCurrentObservation | null;
  rainfall_forecast_24h_mm?: number | null;
  rainfall_probability_max_pct?: number | null;
  imd_warnings?: IMDWarningsResponse | null;
  river_telemetry_status: string;
  river_gauge_reading?: RiverGaugeReading | null;
  historical_records: RiverHistoricalRecord[];
  data_freshness: FreshnessStatus;
  attribution: string;
  disclaimer: string;
  fetched_timestamp: string;
}

