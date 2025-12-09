// API client for fetching emissions data
const API_BASE_URL = 'http://localhost:8000/api';

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

export interface AreaInfo {
  id: string;
  name: string;
  coordinates: [number, number];
  bounds: [[number, number], [number, number]];
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

// Get latest emissions for each area (for map visualization)
export async function fetchLatestEmissionsByArea(dataType: 'historical' | 'forecast' = 'historical'): Promise<Record<string, number>> {
  const emissions = await fetchEmissions({ data_type: dataType });

  // Group by area and get latest date
  const areaEmissions: Record<string, { date: string; total: number }> = {};

  emissions.forEach(emission => {
    if (!areaEmissions[emission.area_id] || emission.date > areaEmissions[emission.area_id].date) {
      areaEmissions[emission.area_id] = {
        date: emission.date,
        total: emission.total
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
export async function fetchLeaderboard(dataType: 'historical' | 'forecast' = 'historical') {
  const latestEmissions = await fetchLatestEmissionsByArea(dataType);
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
