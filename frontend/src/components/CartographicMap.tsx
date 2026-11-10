import React, { useMemo } from 'react';
import type { MapTilerStyle } from '../services/maptiler';

interface CartographicMapProps {
  centerLat: number;
  centerLon: number;
  zoom?: number;
  style?: MapTilerStyle | 'schematic';
  maptilerUrl?: string | null;
  maptilerError?: boolean;
  onMapTilerError?: () => void;
  className?: string;
  styleObj?: React.CSSProperties;
}

interface TileInfo {
  key: string;
  url: string;
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * High-performance, zero-dependency cartographic basemap renderer.
 * Uses MapTiler static image when working; seamlessly degrades to
 * CartoDB / ESRI / OpenStreetMap slippy tiles if MapTiler is unconfigured or returns HTTP 403.
 */
export const CartographicMap: React.FC<CartographicMapProps> = ({
  centerLat,
  centerLon,
  zoom = 12,
  style = 'dataviz-dark',
  maptilerUrl,
  maptilerError = false,
  onMapTilerError,
  className = '',
  styleObj,
}) => {
  // If schematic is explicitly chosen, don't render geographic tiles
  const isSchematic = style === 'schematic';

  // Calculate standard Web Mercator Slippy Map tiles covering an 1000x600 viewport
  const tiles = useMemo<TileInfo[]>(() => {
    if (isSchematic) return [];

    const width = 1000;
    const height = 600;
    const tileSize = 256;
    const n = Math.pow(2, zoom);

    // Bounded coordinates
    const clampedLat = Math.max(-85.0511, Math.min(85.0511, centerLat));
    const clampedLon = ((centerLon + 180) % 360) - 180;

    const centerTileX = ((clampedLon + 180) / 360) * n;
    const latRad = (clampedLat * Math.PI) / 180;
    const centerTileY =
      ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;

    const centerPixelX = centerTileX * tileSize;
    const centerPixelY = centerTileY * tileSize;

    const minPixelX = centerPixelX - width / 2;
    const minPixelY = centerPixelY - height / 2;

    const startX = Math.floor(minPixelX / tileSize);
    const endX = Math.floor((minPixelX + width) / tileSize);
    const startY = Math.floor(minPixelY / tileSize);
    const endY = Math.floor((minPixelY + height) / tileSize);

    const result: TileInfo[] = [];

    for (let x = startX; x <= endX; x++) {
      for (let y = startY; y <= endY; y++) {
        // Tile coordinate wrapping
        const tileX = ((x % n) + n) % n;
        const tileY = y;
        if (tileY < 0 || tileY >= n) continue;

        let tileUrl = '';
        if (style === 'satellite') {
          // High-resolution ESRI World Imagery
          tileUrl = `https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${zoom}/${tileY}/${tileX}`;
        } else if (style === 'topo-v2' || style === 'streets-v2') {
          // CartoDB Voyager / Street details
          const sub = ['a', 'b', 'c', 'd'][(x + y) % 4];
          tileUrl = `https://${sub}.basemaps.cartocdn.com/rastertiles/voyager/${zoom}/${tileX}/${tileY}.png`;
        } else {
          // Dark matter basemap (matches CLIMAFORGE dark theme)
          const sub = ['a', 'b', 'c', 'd'][(x + y) % 4];
          tileUrl = `https://${sub}.basemaps.cartocdn.com/dark_all/${zoom}/${tileX}/${tileY}.png`;
        }

        result.push({
          key: `${zoom}-${tileX}-${tileY}`,
          url: tileUrl,
          left: x * tileSize - minPixelX,
          top: y * tileSize - minPixelY,
          width: tileSize,
          height: tileSize,
        });
      }
    }

    return result;
  }, [centerLat, centerLon, zoom, style, isSchematic]);

  if (isSchematic) {
    return null;
  }

  // 1. If MapTiler static image is available and healthy, show it
  if (maptilerUrl && !maptilerError) {
    return (
      <img
        src={maptilerUrl}
        alt="MapTiler Basemap Layer"
        className={`maptiler-basemap-layer ${className}`}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          zIndex: 1,
          ...styleObj,
        }}
        onError={() => onMapTilerError?.()}
      />
    );
  }

  // 2. Fallback: High-resolution cartographic slippy tile grid
  return (
    <div
      className={`cartographic-tile-grid ${className}`}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        pointerEvents: 'none',
        zIndex: 1,
        background: '#0f172a',
        ...styleObj,
      }}
      aria-hidden="true"
    >
      {tiles.map((tile) => (
        <img
          key={tile.key}
          src={tile.url}
          alt=""
          loading="lazy"
          style={{
            position: 'absolute',
            left: `${tile.left}px`,
            top: `${tile.top}px`,
            width: `${tile.width}px`,
            height: `${tile.height}px`,
            opacity: style === 'satellite' ? 0.85 : 0.75,
            filter: style === 'dataviz-dark' ? 'brightness(0.9) contrast(1.1)' : undefined,
          }}
        />
      ))}
    </div>
  );
};
