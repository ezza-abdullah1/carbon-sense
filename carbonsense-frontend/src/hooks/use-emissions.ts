import { useQuery } from '@tanstack/react-query';
import {
  fetchAreas,
  fetchEmissions,
  fetchLatestEmissionsByArea,
  fetchTimeSeriesData,
  fetchLeaderboard,
  type EmissionsQueryParams,
  type Sector,
  type TimeInterval
} from '@/lib/api';

// Hook to fetch all areas
export function useAreas() {
  return useQuery({
    queryKey: ['areas'],
    queryFn: fetchAreas,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook to fetch emissions with filters
export function useEmissions(params?: EmissionsQueryParams) {
  return useQuery({
    queryKey: ['emissions', params],
    queryFn: () => fetchEmissions(params),
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

// Hook to fetch latest emissions by area (for map)
export function useLatestEmissions(
  dataType: 'historical' | 'forecast' = 'historical',
  sectors?: Sector[],
  interval: TimeInterval = 'monthly'
) {
  return useQuery({
    queryKey: ['latest-emissions', dataType, sectors, interval],
    queryFn: () => fetchLatestEmissionsByArea(dataType, sectors, interval),
    staleTime: 1 * 60 * 1000,
  });
}

// Hook to fetch time series data (for charts)
export function useTimeSeriesData(areaId?: string, dataType: 'historical' | 'forecast' = 'historical') {
  return useQuery({
    queryKey: ['timeseries', areaId, dataType],
    queryFn: () => fetchTimeSeriesData(areaId, dataType),
    staleTime: 1 * 60 * 1000,
  });
}

// Hook to fetch leaderboard
export function useLeaderboard(
  dataType: 'historical' | 'forecast' = 'historical',
  sectors?: Sector[],
  interval: TimeInterval = 'monthly'
) {
  return useQuery({
    queryKey: ['leaderboard', dataType, sectors, interval],
    queryFn: () => fetchLeaderboard(dataType, sectors, interval),
    staleTime: 1 * 60 * 1000,
  });
}

// Hook to fetch combined time series data (historical + forecast for trend comparison)
export function useCombinedTimeSeriesData(areaId?: string) {
  return useQuery({
    queryKey: ['combined-timeseries', areaId],
    queryFn: async () => {
      const [historical, forecast] = await Promise.all([
        fetchTimeSeriesData(areaId, 'historical'),
        fetchTimeSeriesData(areaId, 'forecast'),
      ]);
      return { historical, forecast };
    },
    staleTime: 1 * 60 * 1000,
  });
}
