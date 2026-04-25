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

// Calculate sector sum for an emission data point
function calculateSectorSum(emission: EmissionDataPoint, sectors: Sector[]): number {
  let sum = 0;
  if (sectors.includes('transport')) sum += emission.transport;
  if (sectors.includes('industry')) sum += emission.industry;
  if (sectors.includes('energy')) sum += emission.energy;
  if (sectors.includes('waste')) sum += emission.waste;
  if (sectors.includes('buildings')) sum += emission.buildings;
  return sum;
}

// Time interval type
export type TimeInterval = 'monthly' | 'yearly';

// Filter emissions by time interval (last N months or years)
function filterByTimeInterval(emissions: EmissionDataPoint[], interval: TimeInterval): EmissionDataPoint[] {
  if (emissions.length === 0) return emissions;

  // Find the latest date in the data
  const latestDate = emissions.reduce((max, e) => e.date > max ? e.date : max, emissions[0].date);
  const latest = new Date(latestDate);

  let cutoffDate: Date;
  if (interval === 'monthly') {
    // Last 12 months
    cutoffDate = new Date(latest);
    cutoffDate.setMonth(cutoffDate.getMonth() - 12);
  } else {
    // Last 3 years
    cutoffDate = new Date(latest);
    cutoffDate.setFullYear(cutoffDate.getFullYear() - 3);
  }

  const cutoffStr = cutoffDate.toISOString().split('T')[0];
  return emissions.filter(e => e.date >= cutoffStr);
}

// Get latest emissions for each area (for map visualization)
export async function fetchLatestEmissionsByArea(
  dataType: 'historical' | 'forecast' = 'historical',
  sectors?: Sector[],
  interval: TimeInterval = 'monthly'
): Promise<Record<string, number>> {
  const allEmissions = await fetchEmissions({ data_type: dataType });
  const emissions = filterByTimeInterval(allEmissions, interval);

  // Group by area and get latest date
  const areaEmissions: Record<string, { date: string; total: number }> = {};

  emissions.forEach(emission => {
    // Calculate value based on selected sectors or use total
    const value = sectors && sectors.length > 0
      ? calculateSectorSum(emission, sectors)
      : emission.total;

    // Skip if value is 0 when filtering by sectors
    if (sectors && sectors.length > 0 && value === 0) return;

    if (!areaEmissions[emission.area_id] || emission.date > areaEmissions[emission.area_id].date) {
      areaEmissions[emission.area_id] = {
        date: emission.date,
        total: value
      };
    }
  });

  // Convert to simple Record<string, number>
  const result: Record<string, number> = {};
  Object.keys(areaEmissions).forEach(areaId => {
    result[areaId] = areaEmissions[areaId].total;
  });

  return result;
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

// Calculate leaderboard from emissions data
export async function fetchLeaderboard(
  dataType: 'historical' | 'forecast' = 'historical',
  sectors?: Sector[],
  interval: TimeInterval = 'monthly'
) {
  const latestEmissions = await fetchLatestEmissionsByArea(dataType, sectors, interval);
  const areas = await fetchAreas();

  // Calculate trend (mock for now - would need historical comparison)
  const leaderboard = Object.entries(latestEmissions)
    .map(([areaId, emissions]) => {
      const area = areas.find(a => a.id === areaId);
      return {
        rank: 0, // Will be set after sorting
        areaId,
        areaName: area?.name || areaId,
        emissions,
        trend: Math.random() > 0.5 ? 'up' : 'down' as 'up' | 'down' | 'stable',
        trendPercentage: Math.random() * 10
      };
    })
    .sort((a, b) => b.emissions - a.emissions)
    .map((entry, index) => ({ ...entry, rank: index + 1 }));

  return leaderboard;
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

// ---- Agentic RAG Recommendations ----

export type RecommendationSection =
  | 'summary'
  | 'immediate_actions'
  | 'long_term_strategies'
  | 'policy_recommendations'
  | 'monitoring_metrics'
  | 'risk_factors'
  | 'overall';

export interface RecommendationContent {
  summary: string;
  immediate_actions: string[];
  long_term_strategies: string[];
  policy_recommendations: string[];
  monitoring_metrics: string[];
  risk_factors: string[];
}

export interface RecommendationConfidence {
  overall: number;
  evidence_strength: number;
  data_completeness: number;
  geographic_relevance: number;
}

export interface PipelineTraceStep {
  step: number;
  name: string;
  status: string;
  duration_ms: number;
  data: Record<string, unknown>;
  error?: string;
}

export interface PipelineTrace {
  total_duration_ms: number;
  steps: PipelineTraceStep[];
  step_count: number;
}

export interface RecommendationResponse {
  success: boolean;
  recommendation_id: string;
  query: {
    area_name: string;
    area_id: string;
    sector: string;
    coordinates: { lat: number; lng: number };
  };
  recommendations: RecommendationContent;
  confidence: RecommendationConfidence;
  retrieved_context?: {
    policy_titles?: (string | null)[];
    news_titles?: (string | null)[];
    web_titles?: (string | null)[];
  };
  critic?: Record<string, unknown>;
  pipeline_trace?: PipelineTrace;
  generated_at: string;
  from_cache: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  ts: string;
  extra_context_count?: number;
}

export interface ChatTurnResponse {
  recommendation_id: string;
  reply: string;
  history: ChatMessage[];
  used_extra_lookup: boolean;
}

export interface FeedbackResponse {
  ok: boolean;
  feedback_id: string;
  recommendation_id: string;
  section: RecommendationSection;
  rating: 1 | -1;
}

export interface GenerateRecommendationsPayload {
  coordinates: { lat: number; lng: number };
  sector: 'transport' | 'industry' | 'energy' | 'waste' | 'buildings';
  area_name: string;
  area_id: string;
}

export async function generateRecommendations(
  payload: GenerateRecommendationsPayload,
): Promise<RecommendationResponse> {
  const response = await fetch(`${API_BASE_URL}/recommendations/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`Failed to generate recommendations: ${response.status} ${text}`);
  }
  return response.json();
}

export async function chatRecommendation(
  recommendationId: string,
  message: string,
): Promise<ChatTurnResponse> {
  const response = await fetch(
    `${API_BASE_URL}/recommendations/${recommendationId}/chat`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    },
  );
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`Chat failed: ${response.status} ${text}`);
  }
  return response.json();
}

export async function fetchChatHistory(
  recommendationId: string,
): Promise<{ recommendation_id: string; messages: ChatMessage[] }> {
  const response = await fetch(
    `${API_BASE_URL}/recommendations/${recommendationId}/chat/history`,
  );
  if (!response.ok) {
    throw new Error('Failed to load chat history');
  }
  return response.json();
}

export async function submitRecommendationFeedback(
  recommendationId: string,
  section: RecommendationSection,
  rating: 1 | -1,
  comment?: string,
): Promise<FeedbackResponse> {
  const response = await fetch(
    `${API_BASE_URL}/recommendations/${recommendationId}/feedback`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section, rating, comment: comment ?? '' }),
    },
  );
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`Feedback failed: ${response.status} ${text}`);
  }
  return response.json();
}

export async function getRecommendation(recommendationId: string): Promise<{
  id: string;
  area_id: string;
  area_name: string;
  sector: string;
  content_json: RecommendationContent;
  retrieved_context: Record<string, unknown>;
  generated_at: string;
}> {
  const response = await fetch(
    `${API_BASE_URL}/recommendations/${recommendationId}`,
  );
  if (!response.ok) {
    throw new Error('Failed to load recommendation');
  }
  return response.json();
}
