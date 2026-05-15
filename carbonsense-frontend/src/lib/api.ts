// API client for fetching emissions data
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface EmissionDataPoint {
  id: number;
  area_id: string;
  area_name: string;
  date: string;
  transport: number;
  industry: number;
  energy: number;
  waste: number;
  buildings: number;
  total: number;
  type: 'historical' | 'forecast';
}

export interface SubSectorData {
  // transport sub-sectors
  road?: number;
  dom_avi?: number;
  intl_avi?: number;
  railways?: number;
  road_pct?: number;
  intensity_t_per_km2?: number;
  dominant_source?: string;
  risk_flags?: string[];
  rank_in_division?: number;
  // waste sub-sectors
  point_source?: number;
  solid_waste?: number;
  wastewater?: number;
  point_pct?: number;
  risk_level?: string;
  data_quality_flag?: string;
  pop_weight?: number;
  // allow any additional future fields
  [key: string]: number | string | string[] | boolean | null | undefined;
}

export interface AreaInfo {
  id: string;
  name: string;
  coordinates: [number, number];
  bounds: [[number, number], [number, number]];
  subSectorData?: SubSectorData | null;
  ucCode?: string;
}

// ---- UC Summary types (unified per-UC data from all sectors) ----

export interface TransportSectorData {
  annual_t: number;
  road_annual_t: number;
  dom_avi_annual_t: number;
  intl_avi_annual_t: number;
  rail_annual_t: number;
  road_pct: number;
  road_weight: number;
  rail_weight: number;
  intensity_t_per_km2: number;
  rank_in_division: number;
  ci_lower_annual_t: number;
  ci_upper_annual_t: number;
  dominant_source: string;
  risk_flags: string[];
  monthly_t: number[];
}

export interface BuildingsSectorData {
  residential_t: number;
  non_residential_t: number;
  total_t: number;
  intensity_t_km2: number;
  ci_lower_90_t: number;
  ci_upper_90_t: number;
  rank_in_district: number;
  risk: Record<string, boolean>;
}

export interface WasteSectorData {
  annual_t: number;
  monthly_t: number[];
  point_source_t: number;
  solid_waste_t: number;
  wastewater_t: number;
  point_pct: number;
  risk_level: string;
}

export interface IndustrySectorData {
  annual_t: number;
  by_sector: Record<string, number>;
  intensity_t_per_km2: number;
  rank_in_district: number;
  ci_lower_t: number;
  ci_upper_t: number;
  monthly_t: number[];
  dominant_sector: string;
  risk_flags: string[];
}

export interface UCSummary {
  uc_code: string;
  uc_name: string;
  area_km2: number;
  centroid: [number, number];
  data_type: 'historical' | 'forecast';
  view_mode: 'monthly' | 'yearly';
  month_label: string;
  display_t: number;
  sectors: {
    transport?: (TransportSectorData & { display_t: number }) | null;
    buildings?: (BuildingsSectorData & { display_t: number }) | null;
    waste?: (WasteSectorData & { display_t: number }) | null;
    industry?: (IndustrySectorData & { display_t: number }) | null;
    energy?: number;
  };
  total_annual_t: number;
  available_months: string[];
}

export interface EmissionsQueryParams {
  area_id?: string;
  sector?: string;
  start_date?: string;
  end_date?: string;
  data_type?: 'historical' | 'forecast';
}

// Fetch all areas
export async function fetchAreas(): Promise<AreaInfo[]> {
  const response = await fetch(`${API_BASE_URL}/areas/`);
  if (!response.ok) {
    throw new Error('Failed to fetch areas');
  }
  return response.json();
}

// Fetch emissions data with optional filters
export async function fetchEmissions(params?: EmissionsQueryParams): Promise<EmissionDataPoint[]> {
  const queryParams = new URLSearchParams();
  if (params?.area_id) queryParams.append('area_id', params.area_id);
  if (params?.sector) queryParams.append('sector', params.sector);
  if (params?.start_date) queryParams.append('start_date', params.start_date);
  if (params?.end_date) queryParams.append('end_date', params.end_date);
  if (params?.data_type) queryParams.append('data_type', params.data_type);

  const url = `${API_BASE_URL}/emissions/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error('Failed to fetch emissions');
  }

  return response.json();
}

// Sector type
export type Sector = 'transport' | 'industry' | 'energy' | 'waste' | 'buildings';

// Time interval type — kept for the public API of the hooks; sector/interval
// filtering used to happen on the client over thousands of rows, but those
// concerns now live in the backend (or in the consumer using stats/leaderboard).
export type TimeInterval = 'monthly' | 'yearly';

// Latest emission value per area, computed in the database. Single tiny call;
// the old implementation fetched ~54k rows just to derive this dictionary.
//
// `sectors` and `interval` are accepted for backward compatibility with
// existing call sites but are now unused — the backend returns the latest
// value across all data, and sector filtering should be done at the consumer
// (or moved into the backend if it becomes hot).
export async function fetchLatestEmissionsByArea(
  dataType: 'historical' | 'forecast' = 'historical',
  _sectors?: Sector[],
  _interval: TimeInterval = 'monthly'
): Promise<Record<string, number>> {
  const params = new URLSearchParams({ data_type: dataType });
  const response = await fetch(
    `${API_BASE_URL}/emissions/latest-by-area/?${params.toString()}`,
  );
  if (!response.ok) {
    throw new Error('Failed to fetch latest emissions by area');
  }
  return response.json();
}

// Get time series data for charts
export async function fetchTimeSeriesData(
  area_id?: string,
  dataType: 'historical' | 'forecast' = 'historical'
): Promise<EmissionDataPoint[]> {
  const params: EmissionsQueryParams = { data_type: dataType };
  if (area_id) params.area_id = area_id;

  const emissions = await fetchEmissions(params);
  return emissions.sort((a, b) => a.date.localeCompare(b.date));
}

// Leaderboard — backed by the real `/api/leaderboard/` endpoint, which
// returns rows with real trend data (the previous client-side version
// invented `trend`/`trendPercentage` with `Math.random()`).
//
// `dataType`, `sectors`, `interval` are accepted to preserve the existing
// hook signature; the backend currently ranks by 12-month forecast average
// across all sectors. If sector-aware leaderboards are needed later, push
// the filter into the backend rather than recomputing on the client.
import type { LeaderboardEntry } from '@shared/schema';

interface LeaderboardRowAPI {
  rank: number;
  area_id: string;
  area_name: string;
  emissions: number;
  trend: 'up' | 'down' | 'stable';
  trend_percentage: number;
}

export async function fetchLeaderboard(
  _dataType: 'historical' | 'forecast' = 'historical',
  _sectors?: Sector[],
  _interval: TimeInterval = 'monthly'
): Promise<LeaderboardEntry[]> {
  const response = await fetch(`${API_BASE_URL}/leaderboard/`);
  if (!response.ok) {
    throw new Error('Failed to fetch leaderboard');
  }
  const rows: LeaderboardRowAPI[] = await response.json();
  return rows.map((r) => ({
    rank: r.rank,
    areaId: r.area_id,
    areaName: r.area_name,
    emissions: r.emissions,
    trend: r.trend,
    trendPercentage: r.trend_percentage,
  }));
}

// ---- Aggregate stats for dashboard KPI cards ----

export interface Stats {
  total_sources: number;
  sectors_tracked: number;
  // Top-level fields default to historical data (matches the original KPI
  // intent). For forecast-only or combined values, read from the nested
  // breakdowns below.
  years_of_data: number;
  total_emissions: number;
  sector_totals: Record<Sector, number>;
  historical: { years_of_data: number; total_emissions: number };
  forecast: { years_of_data: number; total_emissions: number };
}

export async function fetchStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE_URL}/stats/`);
  if (!response.ok) {
    throw new Error('Failed to fetch stats');
  }
  return response.json();
}

// ---- Pre-aggregated emissions timeline (monthly totals across all areas) ----

export interface EmissionTimelinePoint {
  date: string;
  total: number;
}

export async function fetchEmissionsTimeline(
  dataType: 'historical' | 'forecast' = 'historical',
): Promise<EmissionTimelinePoint[]> {
  const params = new URLSearchParams({ data_type: dataType });
  const response = await fetch(
    `${API_BASE_URL}/emissions/timeline/?${params.toString()}`,
  );
  if (!response.ok) {
    throw new Error('Failed to fetch emissions timeline');
  }
  return response.json();
}

// ---- Facility-level point sources (energy, industry, waste) ----
//
// Some sectors have data at individual-facility level — power plants,
// fertilizer factories, dumpsites, wastewater plants. The map renders
// them as point markers rather than colouring UC polygons. Sectors
// without facility-level data (transport, buildings) return [].

export interface PointSourceSummary {
  last_historical_date: string;
  last_historical_emissions: number;
  forecast_12m_total: number;
  forecast_12m_average: number;
  total_historical_tonnes: number;
  change_pct: number;
  trend: 'increasing' | 'declining' | 'stable';
}

export interface PointSource {
  source: string;
  type: string;
  lat: number;
  lng: number;
  emissions: number;
  sector: Sector;
  summary: PointSourceSummary | null;
}

export async function fetchPointSources(
  sector: Sector,
  dataType: 'historical' | 'forecast' = 'historical',
): Promise<PointSource[]> {
  const params = new URLSearchParams({ sector, data_type: dataType });
  const response = await fetch(`${API_BASE_URL}/point-sources/?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch point sources for sector "${sector}"`);
  }
  return response.json();
}

// ---- UC Boundaries (static GeoJSON) ----

export async function fetchUCBoundaries(): Promise<GeoJSON.FeatureCollection> {
  const response = await fetch('/geo/lahore-ucs.geojson');
  if (!response.ok) {
    throw new Error('Failed to fetch UC boundaries');
  }
  return response.json();
}

// ---- UC Summaries (unified per-UC data) ----

export async function fetchUCSummaries(
  dataType: 'historical' | 'forecast' = 'forecast',
  viewMode: 'monthly' | 'yearly' = 'yearly',
  month?: string,
): Promise<UCSummary[]> {
  const params = new URLSearchParams({ data_type: dataType, view_mode: viewMode });
  if (viewMode === 'monthly' && month) {
    params.append('month', month);
  }
  const response = await fetch(`${API_BASE_URL}/uc-summary/?${params.toString()}`);
  if (!response.ok) {
    throw new Error('Failed to fetch UC summaries');
  }
  return response.json();
}
