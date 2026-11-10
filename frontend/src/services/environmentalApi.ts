/**
 * API service client for CLIMAFORGE Real-Time Environmental Intelligence
 * and Indrayani River Environmental Monitoring.
 */

import type {
  IMDWarningsResponse,
  IndrayaniMonitoringResponse,
  RiverHistoricalRecord,
  RiverStationReference,
  WeatherCurrentObservation,
  WeatherForecastResponse,
} from '../types/environmental';
import { authenticatedFetch, getApiBaseUrl } from './api';

/**
 * Fetch current ambient weather observation for specified coordinates.
 */
export async function fetchCurrentWeather(
  latitude?: number,
  longitude?: number,
): Promise<WeatherCurrentObservation> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  if (latitude !== undefined) query.set('lat', latitude.toString());
  if (longitude !== undefined) query.set('lon', longitude.toString());

  const url = `${baseUrl}/api/environmental/weather?${query.toString()}`;
  const response = await authenticatedFetch(url, { method: 'GET' });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch current weather (HTTP ${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Fetch complete weather and 48-hour precipitation forecast.
 */
export async function fetchWeatherForecast(
  latitude?: number,
  longitude?: number,
  locationName?: string,
  forceRefresh = false,
): Promise<WeatherForecastResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  if (latitude !== undefined) query.set('lat', latitude.toString());
  if (longitude !== undefined) query.set('lon', longitude.toString());
  if (locationName) query.set('location_name', locationName);
  if (forceRefresh) query.set('force_refresh', 'true');

  const url = `${baseUrl}/api/environmental/forecast?${query.toString()}`;
  const response = await authenticatedFetch(url, { method: 'GET' });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch weather forecast (HTTP ${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Fetch official IMD weather warnings for Pune District.
 */
export async function fetchIMDWarnings(
  district = 'Pune',
  state = 'Maharashtra',
  forceRefresh = false,
): Promise<IMDWarningsResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams({ district, state });
  if (forceRefresh) query.set('force_refresh', 'true');

  const url = `${baseUrl}/api/environmental/warnings?${query.toString()}`;
  const response = await authenticatedFetch(url, { method: 'GET' });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch IMD warnings (HTTP ${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Fetch unified Indrayani River environmental monitoring snapshot.
 */
export async function fetchIndrayaniMonitoring(
  stationId?: string,
  forceRefresh = false,
): Promise<IndrayaniMonitoringResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  if (stationId) query.set('station_id', stationId);
  if (forceRefresh) query.set('force_refresh', 'true');

  const url = `${baseUrl}/api/environmental/indrayani?${query.toString()}`;
  const response = await authenticatedFetch(url, { method: 'GET' });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch Indrayani monitoring summary (HTTP ${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Retrieve verified reference stations along Indrayani corridor.
 */
export async function fetchIndrayaniStations(): Promise<RiverStationReference[]> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/environmental/indrayani/stations`;
  const response = await authenticatedFetch(url, { method: 'GET' });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch Indrayani stations (HTTP ${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Retrieve historical environmental records for specified station.
 */
export async function fetchIndrayaniHistory(
  stationId = 'MPCB-INDRAYANI-MOSHI-11',
): Promise<RiverHistoricalRecord[]> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/environmental/indrayani/history?station_id=${encodeURIComponent(stationId)}`;
  const response = await authenticatedFetch(url, { method: 'GET' });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch historical environmental records (HTTP ${response.status}): ${errorText}`);
  }

  return response.json();
}

