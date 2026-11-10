/**
 * MapTiler API Integration Service for CLIMAFORGE.
 *
 * Provides cartographic basemap resolution, style selection,
 * coordinate framing, and graceful fallback handling.
 */

export type MapTilerStyle = 'dataviz-dark' | 'streets-v2' | 'topo-v2' | 'satellite';

export interface MapTilerConfigStatus {
  isConfigured: boolean;
  hasKey: boolean;
  activeStyle: MapTilerStyle;
  attribution: string;
  attributionUrl: string;
}

export const MAPTILER_ATTRIBUTION = '© MapTiler © OpenStreetMap contributors';
export const MAPTILER_ATTRIBUTION_URL = 'https://www.maptiler.com/copyright/';

/**
 * Retrieves the configured MapTiler API key from the environment.
 * Never logs or exposes the key value.
 */
export function getMapTilerApiKey(): string | null {
  const envKey = import.meta.env.VITE_MAPTILER_API_KEY;
  if (!envKey || typeof envKey !== 'string') {
    return null;
  }
  const trimmed = envKey.trim();
  const lower = trimmed.toLowerCase();
  if (
    !trimmed ||
    lower.startsWith('replace') ||
    lower.startsWith('your') ||
    lower.startsWith('<') ||
    lower.includes('placeholder')
  ) {
    return null;
  }
  return trimmed;
}

/**
 * Checks whether a valid, non-placeholder MapTiler API key is configured.
 */
export function isMapTilerConfigured(): boolean {
  return getMapTilerApiKey() !== null;
}

/**
 * Builds a MapTiler static map image URL for a given center coordinate, zoom, and resolution.
 * Returns null if the API key is unconfigured, allowing clean fallback.
 */
export function getMapTilerStaticMapUrl(
  longitude: number,
  latitude: number,
  zoom = 12,
  width = 800,
  height = 500,
  style: MapTilerStyle = 'dataviz-dark',
): string | null {
  const key = getMapTilerApiKey();
  if (!key) {
    return null;
  }

  // Ensure dimensions are within reasonable bounds
  const clampedW = Math.min(2048, Math.max(100, Math.round(width)));
  const clampedH = Math.min(2048, Math.max(100, Math.round(height)));
  const clampedZ = Math.min(20, Math.max(1, zoom));

  return `https://api.maptiler.com/maps/${style}/static/${longitude.toFixed(5)},${latitude.toFixed(5)},${clampedZ}/${clampedW}x${clampedH}@2x.png?key=${encodeURIComponent(key)}`;
}

/**
 * Returns configuration metadata for UI status indicators.
 */
export function getMapTilerStatus(activeStyle: MapTilerStyle = 'dataviz-dark'): MapTilerConfigStatus {
  return {
    isConfigured: isMapTilerConfigured(),
    hasKey: getMapTilerApiKey() !== null,
    activeStyle,
    attribution: MAPTILER_ATTRIBUTION,
    attributionUrl: MAPTILER_ATTRIBUTION_URL,
  };
}
