import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getMapTilerApiKey,
  isMapTilerConfigured,
  getMapTilerStaticMapUrl,
  getMapTilerStatus,
  MAPTILER_ATTRIBUTION,
  MAPTILER_ATTRIBUTION_URL,
} from '../services/maptiler';

describe('MapTiler Service & Basemap Integration', () => {
  const originalApiKey = import.meta.env.VITE_MAPTILER_API_KEY;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    import.meta.env.VITE_MAPTILER_API_KEY = originalApiKey;
  });

  it('provides correct MapTiler attribution strings', () => {
    expect(MAPTILER_ATTRIBUTION).toContain('MapTiler');
    expect(MAPTILER_ATTRIBUTION).toContain('OpenStreetMap');
    expect(MAPTILER_ATTRIBUTION_URL).toBe('https://www.maptiler.com/copyright/');
  });

  it('detects when MapTiler API key is configured or missing', () => {
    import.meta.env.VITE_MAPTILER_API_KEY = 'test_valid_key_123';
    expect(isMapTilerConfigured()).toBe(true);
    expect(getMapTilerApiKey()).toBe('test_valid_key_123');

    import.meta.env.VITE_MAPTILER_API_KEY = '';
    expect(isMapTilerConfigured()).toBe(false);
    expect(getMapTilerApiKey()).toBeNull();

    import.meta.env.VITE_MAPTILER_API_KEY = 'your_maptiler_api_key_here';
    expect(isMapTilerConfigured()).toBe(false);
    expect(getMapTilerApiKey()).toBeNull();

    import.meta.env.VITE_MAPTILER_API_KEY = 'replace-with-key';
    expect(isMapTilerConfigured()).toBe(false);
    expect(getMapTilerApiKey()).toBeNull();
  });

  it('generates valid MapTiler static map URL with all parameters', () => {
    import.meta.env.VITE_MAPTILER_API_KEY = 'test_key_xyz';

    const url = getMapTilerStaticMapUrl(73.8567, 18.5204, 12, 800, 600, 'dataviz-dark');
    expect(url).toBe(
      'https://api.maptiler.com/maps/dataviz-dark/static/73.85670,18.52040,12/800x600@2x.png?key=test_key_xyz',
    );
  });

  it('generates valid URL for different styles including satellite and topo', () => {
    import.meta.env.VITE_MAPTILER_API_KEY = 'test_key_xyz';

    const satelliteUrl = getMapTilerStaticMapUrl(73.8785, 18.6836, 14, 1024, 768, 'satellite');
    expect(satelliteUrl).toBe(
      'https://api.maptiler.com/maps/satellite/static/73.87850,18.68360,14/1024x768@2x.png?key=test_key_xyz',
    );

    const topoUrl = getMapTilerStaticMapUrl(73.768, 18.718, 10, 600, 400, 'topo-v2');
    expect(topoUrl).toBe(
      'https://api.maptiler.com/maps/topo-v2/static/73.76800,18.71800,10/600x400@2x.png?key=test_key_xyz',
    );
  });

  it('returns null when API key is missing or blank', () => {
    import.meta.env.VITE_MAPTILER_API_KEY = '';
    const url = getMapTilerStaticMapUrl(73.8567, 18.5204);
    expect(url).toBeNull();
  });

  it('reports accurate status for diagnostics and UI badges', () => {
    import.meta.env.VITE_MAPTILER_API_KEY = 'test_key_live';
    const activeStatus = getMapTilerStatus('dataviz-dark');
    expect(activeStatus.isConfigured).toBe(true);
    expect(activeStatus.hasKey).toBe(true);
    expect(activeStatus.activeStyle).toBe('dataviz-dark');
    expect(activeStatus.attribution).toContain('MapTiler');

    import.meta.env.VITE_MAPTILER_API_KEY = '';
    const fallbackStatus = getMapTilerStatus('dataviz-dark');
    expect(fallbackStatus.isConfigured).toBe(false);
    expect(fallbackStatus.hasKey).toBe(false);
  });
});
