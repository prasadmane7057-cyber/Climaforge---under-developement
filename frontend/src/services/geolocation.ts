/**
 * Browser Geolocation helper with consent tracking, accuracy estimation,
 * and predefined Indrayani corridor presets.
 */

export interface LocationPreset {
  id: string;
  name: string;
  description: string;
  latitude: number;
  longitude: number;
  isRiverCorridor: boolean;
}

export const GEOLOCATION_PRESETS: LocationPreset[] = [
  {
    id: 'moshi-mpcb',
    name: 'Indrayani River — Moshi (MPCB Ref)',
    description: 'Downstream of Moshi Village (MPCB Station 11, Taluka Haveli, Pune)',
    latitude: 18.68365,
    longitude: 73.87855,
    isRiverCorridor: true,
  },
  {
    id: 'dehu-ghat',
    name: 'Indrayani River — Dehu Ghat',
    description: 'Sant Tukaram Maharaj Temple & Ghats, Upper Basin Corridor',
    latitude: 18.7180,
    longitude: 73.7680,
    isRiverCorridor: true,
  },
  {
    id: 'alandi-ghat',
    name: 'Indrayani River — Alandi Ghat',
    description: 'Sant Dnyaneshwar Maharaj Samadhi Temple, Middle Basin Corridor',
    latitude: 18.6770,
    longitude: 73.8960,
    isRiverCorridor: true,
  },
  {
    id: 'tulapur-sangam',
    name: 'Indrayani-Bhima Confluence — Tulapur',
    description: 'Triveni Sangam confluence with Bhima River, Lower Basin Corridor',
    latitude: 18.5770,
    longitude: 74.0150,
    isRiverCorridor: true,
  },
  {
    id: 'pcmc-central',
    name: 'Pimpri-Chinchwad (PCMC Central)',
    description: 'Pimpri-Chinchwad Municipal Corporation area, Pune District',
    latitude: 18.6279,
    longitude: 73.8010,
    isRiverCorridor: false,
  },
  {
    id: 'pune-city',
    name: 'Pune City (Shivajinagar)',
    description: 'Pune District Central, Maharashtra, India',
    latitude: 18.5204,
    longitude: 73.8567,
    isRiverCorridor: false,
  },
];

export interface GeolocationPositionResult {
  latitude: number;
  longitude: number;
  accuracyMeters: number | null;
  altitudeMeters: number | null;
  timestamp: number;
  source: 'GPS_BROWSER' | 'MANUAL_PRESET' | 'MANUAL_COORDINATES';
  presetName?: string;
}

/**
 * Checks if navigator.geolocation is supported in the current environment.
 */
export function isGeolocationSupported(): boolean {
  return typeof window !== 'undefined' && 'navigator' in window && 'geolocation' in navigator;
}

/**
 * Requests the current position from the browser Geolocation API with explicit timeout and high accuracy.
 */
export function requestBrowserPosition(
  options: PositionOptions = { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
): Promise<GeolocationPositionResult> {
  return new Promise((resolve, reject) => {
    if (!isGeolocationSupported()) {
      reject(new Error('Geolocation is not supported by your browser environment.'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracyMeters: pos.coords.accuracy ?? null,
          altitudeMeters: pos.coords.altitude ?? null,
          timestamp: pos.timestamp,
          source: 'GPS_BROWSER',
        });
      },
      (err) => {
        let message = 'Unable to retrieve location.';
        switch (err.code) {
          case err.PERMISSION_DENIED:
            message = 'Geolocation permission was denied. You can select a preset location instead.';
            break;
          case err.POSITION_UNAVAILABLE:
            message = 'Position information is unavailable. Please choose a preset location.';
            break;
          case err.TIMEOUT:
            message = 'Geolocation request timed out. Please retry or choose a preset location.';
            break;
        }
        reject(new Error(message));
      },
      options,
    );
  });
}

