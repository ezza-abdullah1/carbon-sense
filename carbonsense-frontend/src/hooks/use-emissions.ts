import { useQuery } from '@tanstack/react-query';
import {
  fetchAreas,
  fetchEmissions,
  fetchEmissionsTimeline,
  fetchLatestEmissionsByArea,
  fetchTimeSeriesData,
  fetchLeaderboard,
  fetchStats,
  fetchUCBoundaries,
  fetchUCSummaries,
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

// Aggregate stats for dashboard KPI cards. Tiny payload, cached on the
// backend — safe to fire on every page load.
export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    staleTime: 5 * 60 * 1000,
  });
}

// Pre-aggregated timeline (one row per date, totals across all areas).
// Use this instead of `useEmissions()` whenever you only need a sum-by-date
// chart — it returns ~72 rows instead of ~25,000.
export function useEmissionsTimeline(
  dataType: 'historical' | 'forecast' = 'historical',
) {
  return useQuery({
    queryKey: ['emissions-timeline', dataType],
    queryFn: () => fetchEmissionsTimeline(dataType),
    staleTime: 5 * 60 * 1000,
  });
}

// Raw emission rows. Heavy — only call this when the user is on a tab that
// genuinely needs to slice/pivot the underlying data (Trends, Forecast,
// Data Explorer). Pass `enabled: false` (or a tab-active boolean) when the
// caller is the dashboard's overview tab.
export function useEmissions(params?: EmissionsQueryParams, enabled = true) {
  return useQuery({
    queryKey: ['emissions', params],
    queryFn: () => fetchEmissions(params),
    staleTime: 5 * 60 * 1000,
    enabled,
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

// Hook to fetch UC polygon boundaries (static GeoJSON, cached forever)
export function useUCBoundaries() {
  return useQuery({
    queryKey: ['uc-boundaries'],
    queryFn: fetchUCBoundaries,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}

// Hook to fetch unified per-UC summaries from all sectors
export function useUCSummaries(
  dataType: 'historical' | 'forecast' = 'forecast',
  viewMode: 'monthly' | 'yearly' = 'yearly',
  month?: string,
) {
  return useQuery({
    queryKey: ['uc-summaries', dataType, viewMode, month],
    queryFn: () => fetchUCSummaries(dataType, viewMode, month),
    staleTime: 5 * 60 * 1000,
  });
}

// Combined historical + forecast time series for a single area.
// Disabled when `areaId` is missing — without an areaId the underlying
// fetcher would pull every emission point twice (once per data_type), which
// is exactly what we're trying to avoid.
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
    staleTime: 5 * 60 * 1000,
    enabled: !!areaId,
  });
}
