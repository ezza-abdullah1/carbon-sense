import type { UCSummary, Sector } from './api';

// YlOrRd 9-class ColorBrewer palette
const YLORRD_9 = [
  '#ffffcc', '#ffeda0', '#fed976', '#feb24c',
  '#fd8d3c', '#fc4e2a', '#e31a1c', '#bd0026', '#800026',
];

/**
 * Compute quantile break points for a sorted array of values.
 */
export function computeQuantileBreaks(values: number[], nBuckets: number): number[] {
  if (values.length === 0) return [];
  const sorted = [...values].sort((a, b) => a - b);
  const breaks: number[] = [];
  for (let i = 1; i < nBuckets; i++) {
    const idx = Math.floor((i / nBuckets) * sorted.length);
    breaks.push(sorted[Math.min(idx, sorted.length - 1)]);
  }
  return breaks;
}

/**
 * Map a value to a YlOrRd color using quantile breaks.
 */
export function getYlOrRdColor(value: number, breaks: number[]): string {
  if (breaks.length === 0) return YLORRD_9[0];
  for (let i = 0; i < breaks.length; i++) {
    if (value <= breaks[i]) return YLORRD_9[i];
  }
  return YLORRD_9[YLORRD_9.length - 1];
}

/**
 * Get the full YlOrRd palette for legend rendering.
 */
export function getYlOrRdPalette(): string[] {
  return YLORRD_9;
}

/**
 * Format tonnes for display: 1,234 t / 1.2 kt / 1.3 Mt
 */
export function formatTonnes(t: number): string {
  if (t >= 1_000_000) return `${(t / 1_000_000).toFixed(1)} Mt`;
  if (t >= 10_000) return `${Math.round(t).toLocaleString()} t`;
  if (t >= 1_000) return `${Math.round(t).toLocaleString()} t`;
  return `${t.toFixed(0)} t`;
}

/**
 * Get the emission value for a UC given selected sectors.
 * Uses display_t (monthly or annual depending on view_mode set by backend).
 */
export function getUCEmission(uc: UCSummary, sectors: Sector[]): number {
  let total = 0;
  if (sectors.includes('transport') && uc.sectors.transport) {
    total += uc.sectors.transport.display_t;
  }
  if (sectors.includes('buildings') && uc.sectors.buildings) {
    total += uc.sectors.buildings.display_t;
  }
  if (sectors.includes('waste') && uc.sectors.waste) {
    if (typeof uc.sectors.waste === 'object') {
      total += uc.sectors.waste.display_t;
    }
  }
  if (sectors.includes('energy') && typeof uc.sectors.energy === 'number') {
    total += uc.sectors.energy;
  }
  if (sectors.includes('industry') && typeof uc.sectors.industry === 'number') {
    total += uc.sectors.industry;
  }
  return total;
}

// ML-1 Pakistan Railways polyline coordinates
export const RAILWAY_COORDS: [number, number][] = [
  [31.12, 74.35], [31.26, 74.41], [31.38, 74.42], [31.46, 74.38],
  [31.52, 74.36], [31.57, 74.33], [31.65, 74.28], [31.72, 74.24],
];

// Key map markers
export const AIRPORT_COORDS: [number, number] = [31.5216, 74.4036];
export const CITY_CENTRE_COORDS: [number, number] = [31.5204, 74.3587];
