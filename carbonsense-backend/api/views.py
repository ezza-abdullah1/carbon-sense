import json
import math
import os
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.conf import settings
from .models import (
    User, ForecastRun, Location, EmissionPoint,
    LocationSummary, AggregateForecastPoint, make_area_id,
)
from .serializers import SignupSerializer, LoginSerializer, UserSerializer

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')

CACHE_TTL = 300  # 5 minutes


# ============================================================================
# Auth views (unchanged)
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        login(request, user)
        user_data = UserSerializer(user).data
        return Response({'user': user_data}, status=status.HTTP_201_CREATED)
    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        user_data = UserSerializer(user).data
        return Response({'user': user_data}, status=status.HTTP_200_OK)
    return Response({'error': serializer.errors}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# ============================================================================
# Helpers: multi-sector support
# ============================================================================

SECTOR_MAP = {
    'power': 'energy',
    'electricity-generation': 'energy',
    'energy': 'energy',
    'transportation': 'transport',
    'transport': 'transport',
    'industrial': 'industry',
    'industry': 'industry',
    'manufacturing': 'industry',
    'waste': 'waste',
    'buildings': 'buildings',
    'residential': 'buildings',
    'commercial': 'buildings',
}


def _get_active_runs():
    """Get ALL active forecast runs (one per sector)."""
    runs = cache.get('active_forecast_runs')
    if runs is None:
        runs = list(ForecastRun.objects.filter(is_active=True))
        if runs:
            cache.set('active_forecast_runs', runs, CACHE_TTL)
    return runs


def _sector_field(run):
    return SECTOR_MAP.get(run.sector.lower(), 'energy') if run else 'energy'


def _safe_float(val, default=0.0):
    """Return default if val is NaN, None, or inf."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return default
    return val


# ============================================================================
# Areas endpoint — locations from ALL active runs
# ============================================================================

class AreaInfoViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cached = cache.get('areas_list')
        if cached is not None:
            return Response(cached)

        runs = _get_active_runs()
        if not runs:
            return Response([])

        results = []
        for run in runs:
            sector = _sector_field(run)
            locs = Location.objects.filter(forecast_run=run)
            # Pre-fetch summaries for sub_sector_data in one query
            summary_map = {
                s.location_id: s
                for s in LocationSummary.objects.filter(location__in=locs)
            }
            for loc in locs:
                lat = _safe_float(loc.latitude)
                lng = _safe_float(loc.longitude)
                summary = summary_map.get(loc.id)
                sub_sector = None
                if summary and summary.sub_sector_data:
                    sub_sector = summary.sub_sector_data
                results.append({
                    'id': make_area_id(loc.source, sector),
                    'name': loc.source,
                    'coordinates': [lat, lng],
                    'bounds': [
                        [lat - 0.1, lng - 0.1],
                        [lat + 0.1, lng + 0.1],
                    ],
                    'subSectorData': sub_sector,
                    'ucCode': loc.uc_code or '',
                })

        cache.set('areas_list', results, CACHE_TTL)
        return Response(results)

    def retrieve(self, request, pk=None):
        runs = _get_active_runs()
        for run in runs:
            sector = _sector_field(run)
            for loc in Location.objects.filter(forecast_run=run):
                if make_area_id(loc.source, sector) == pk:
                    lat = _safe_float(loc.latitude)
                    lng = _safe_float(loc.longitude)
                    summary = LocationSummary.objects.filter(location=loc).first()
                    sub_sector = summary.sub_sector_data if summary else None
                    return Response({
                        'id': pk,
                        'name': loc.source,
                        'coordinates': [lat, lng],
                        'bounds': [
                            [lat - 0.1, lng - 0.1],
                            [lat + 0.1, lng + 0.1],
                        ],
                        'subSectorData': sub_sector,
                    })
        return Response({'detail': 'Not found.'}, status=404)


# ============================================================================
# Emissions endpoint — emission_points from ALL active runs
# ============================================================================

class EmissionDataViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cache_key = f"emissions_{request.query_params.urlencode()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        runs = _get_active_runs()
        if not runs:
            return Response([])

        # Build a map: run_id -> sector_field
        run_ids = [r.id for r in runs]
        run_sector = {r.id: _sector_field(r) for r in runs}

        queryset = EmissionPoint.objects.filter(
            location__forecast_run_id__in=run_ids,
        ).select_related('location', 'location__forecast_run')

        # Filter by area_id
        area_id = request.query_params.get('area_id')
        if area_id:
            matching_loc_ids = []
            for run in runs:
                sector = _sector_field(run)
                for loc in Location.objects.filter(forecast_run=run):
                    if make_area_id(loc.source, sector) == area_id:
                        matching_loc_ids.append(loc.id)
            queryset = queryset.filter(location_id__in=matching_loc_ids)

        # Filter by data_type (maps to point_type)
        data_type = request.query_params.get('data_type')
        if data_type:
            queryset = queryset.filter(point_type=data_type)

        # Filter by date range
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        queryset = queryset.order_by('-date')

        results = []
        for ep in queryset:
            sector = run_sector.get(ep.location.forecast_run_id, 'energy')
            val = _safe_float(ep.emissions)
            emission_row = {
                'transport': 0, 'industry': 0, 'energy': 0,
                'waste': 0, 'buildings': 0,
            }
            emission_row[sector] = val

            results.append({
                'id': ep.id,
                'area_id': make_area_id(ep.location.source, sector),
                'area_name': ep.location.source,
                'date': ep.date.isoformat(),
                **emission_row,
                'total': val,
                'type': ep.point_type,
            })

        cache.set(cache_key, results, CACHE_TTL)
        return Response(results)

    def retrieve(self, request, pk=None):
        runs = _get_active_runs()
        if not runs:
            return Response({'detail': 'Not found.'}, status=404)

        run_ids = [r.id for r in runs]
        run_sector = {r.id: _sector_field(r) for r in runs}

        try:
            ep = EmissionPoint.objects.select_related('location', 'location__forecast_run').get(
                pk=pk, location__forecast_run_id__in=run_ids
            )
        except EmissionPoint.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

        sector = run_sector.get(ep.location.forecast_run_id, 'energy')
        emission_row = {
            'transport': 0, 'industry': 0, 'energy': 0,
            'waste': 0, 'buildings': 0,
        }
        emission_row[sector] = ep.emissions

        return Response({
            'id': ep.id,
            'area_id': make_area_id(ep.location.source, sector),
            'area_name': ep.location.source,
            'date': ep.date.isoformat(),
            **emission_row,
            'total': ep.emissions,
            'type': ep.point_type,
        })


# ============================================================================
# Leaderboard endpoint — computed from ALL active runs
# ============================================================================

class LeaderboardViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cached = cache.get('leaderboard_list')
        if cached is not None:
            return Response(cached)

        runs = _get_active_runs()
        if not runs:
            return Response([])

        all_entries = []
        for run in runs:
            sector = _sector_field(run)
            summaries = LocationSummary.objects.filter(
                location__forecast_run=run
            ).select_related('location')

            for s in summaries:
                trend_map = {'increasing': 'up', 'declining': 'down', 'stable': 'stable'}
                all_entries.append({
                    'area_id': make_area_id(s.location.source, sector),
                    'area_name': s.location.source,
                    'emissions': s.forecast_12m_average,
                    'trend': trend_map.get(s.trend, 'stable'),
                    'trend_percentage': abs(s.change_pct),
                })

        # Sort by emissions descending and assign ranks
        all_entries.sort(key=lambda x: x['emissions'], reverse=True)
        results = [{'rank': i + 1, **entry} for i, entry in enumerate(all_entries)]

        cache.set('leaderboard_list', results, CACHE_TTL)
        return Response(results)


# ============================================================================
# Helpers: load JSON data files (cached in-process)
# ============================================================================

_json_cache = {}


def _load_data_file(filename):
    """Load a JSON file from the data directory, caching in memory."""
    if filename not in _json_cache:
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, encoding='utf-8') as f:
            _json_cache[filename] = json.load(f)
    return _json_cache[filename]


# ============================================================================
# UC Summary endpoint — unified per-UC data from all sectors
# ============================================================================

def _build_transport_by_uc(data_type):
    """Transport: 151 UCs from carbonsense_transport_v16.json.
    Supports historical (60 months) and forecast (12 months)."""
    data = _load_data_file('carbonsense_transport_v16.json')
    result = {}
    for uc in data.get('uc_emissions', []):
        code = uc.get('uc_code', '')
        sw = uc.get('spatial_weights', {})

        if data_type == 'forecast':
            fc = uc.get('forecast', {})
            monthly = fc.get('monthly_t', [])
            result[code] = {
                'annual_t': _safe_float(fc.get('annual_t')),
                'road_annual_t': _safe_float(fc.get('road_annual_t')),
                'dom_avi_annual_t': _safe_float(fc.get('dom_avi_annual_t')),
                'intl_avi_annual_t': _safe_float(fc.get('intl_avi_annual_t')),
                'rail_annual_t': _safe_float(fc.get('rail_annual_t')),
                'road_pct': _safe_float(fc.get('road_pct')),
                'road_weight': _safe_float(sw.get('road_weight')),
                'rail_weight': _safe_float(sw.get('rail_weight')),
                'intensity_t_per_km2': _safe_float(fc.get('intensity_t_per_km2')),
                'rank_in_division': fc.get('rank_in_division', 0),
                'ci_lower_annual_t': _safe_float(fc.get('ci_lower_annual_t')),
                'ci_upper_annual_t': _safe_float(fc.get('ci_upper_annual_t')),
                'dominant_source': uc.get('dominant_source', ''),
                'risk_flags': uc.get('risk_flags', []),
                'monthly_t': monthly,
            }
        else:
            # Historical
            hist = uc.get('historical', {})
            series = hist.get('monthly_series', [])
            monthly = [_safe_float(m.get('total_t')) for m in series]
            # Use last 12 months for annual figure
            last12 = monthly[-12:] if len(monthly) >= 12 else monthly
            annual = sum(last12)
            result[code] = {
                'annual_t': round(annual, 2),
                'road_annual_t': _safe_float(hist.get('road_t')),
                'dom_avi_annual_t': _safe_float(hist.get('dom_avi_t')),
                'intl_avi_annual_t': _safe_float(hist.get('intl_avi_t')),
                'rail_annual_t': _safe_float(hist.get('rail_t')),
                'road_pct': 0.0,  # not in historical breakdown
                'road_weight': _safe_float(sw.get('road_weight')),
                'rail_weight': _safe_float(sw.get('rail_weight')),
                'intensity_t_per_km2': round(
                    annual / max(_safe_float(uc.get('area_km2')), 0.01), 1
                ),
                'rank_in_division': 0,
                'ci_lower_annual_t': _safe_float(hist.get('ci_lower_t')),
                'ci_upper_annual_t': _safe_float(hist.get('ci_upper_t')),
                'dominant_source': uc.get('dominant_source', ''),
                'risk_flags': uc.get('risk_flags', []),
                'monthly_t': monthly,
            }
    return result


def _build_buildings_by_uc(data_type):
    """Buildings: 151 UCs from JSON. Supports historical / forecast toggle."""
    data = _load_data_file('carbonsense_buildings_v15.json')
    result = {}
    for uc in data.get('uc_data', []):
        code = uc.get('uc_code', '')
        ae = uc.get('annual_emissions', {})
        risk = uc.get('risk', {})

        # Monthly time-series from the requested period
        series = uc.get('forecast' if data_type == 'forecast' else 'historical', [])
        monthly_t = []
        monthly_res_t = []
        monthly_nonres_t = []
        for row in (series if isinstance(series, list) else []):
            monthly_t.append(_safe_float(row.get('total_t')))
            monthly_res_t.append(_safe_float(row.get('residential_t')))
            monthly_nonres_t.append(_safe_float(row.get('non_residential_t')))

        # For historical, sum the last 12 months as the annual figure
        if data_type == 'historical' and monthly_t:
            last12 = monthly_t[-12:] if len(monthly_t) >= 12 else monthly_t
            total_t = sum(last12)
            res_t = sum(monthly_res_t[-12:]) if monthly_res_t else 0.0
            nonres_t = sum(monthly_nonres_t[-12:]) if monthly_nonres_t else 0.0
        else:
            total_t = _safe_float(ae.get('total_t'))
            res_t = _safe_float(ae.get('residential_t'))
            nonres_t = _safe_float(ae.get('non_residential_t'))

        result[code] = {
            'residential_t': round(res_t, 2),
            'non_residential_t': round(nonres_t, 2),
            'total_t': round(total_t, 2),
            'intensity_t_km2': _safe_float(ae.get('intensity_t_km2')),
            'ci_lower_90_t': _safe_float(ae.get('ci_lower_90_t')),
            'ci_upper_90_t': _safe_float(ae.get('ci_upper_90_t')),
            'rank_in_district': ae.get('rank_in_district', 0),
            'monthly_t': monthly_t,
            'risk': {k: v for k, v in risk.items() if isinstance(v, bool)},
        }
    return result


def _build_waste_by_uc(data_type):
    """Waste: 108 UCs from carbonsense_per_location_waste_v2_3.json.
    Supports both historical (allocated via pop_weight) and forecast."""
    waste_by_uc = {}

    data = _load_data_file('carbonsense_per_location_waste_v2_3.json')
    alloc = data.get('aggregate_forecast', {}).get('uc_allocation', [])

    for uc in alloc:
        code = uc.get('uc_code', '')
        if not code:
            continue

        if data_type == 'forecast':
            em = uc.get('emissions', {})
            cd = uc.get('chart_data', [])
            monthly = [_safe_float(m.get('predicted')) for m in cd
                        if isinstance(m, dict)]
            waste_by_uc[code] = {
                'annual_t': _safe_float(em.get('total_annual_t')),
                'monthly_t': monthly,
                'point_source_t': _safe_float(em.get('point_source_t')),
                'solid_waste_t': _safe_float(em.get('area_sw_t')),
                'wastewater_t': _safe_float(em.get('area_ww_t')),
                'point_pct': _safe_float(em.get('point_pct')),
                'risk_level': em.get('risk_level', ''),
                'rank_in_district': uc.get('rank_in_district', 0),
                'intensity_t_per_km2': _safe_float(uc.get('intensity_t_per_km2')),
            }
        else:
            # Historical (allocated via pop_weight)
            hist = uc.get('historical', [])
            ha = uc.get('historical_annual', {})
            monthly = [_safe_float(m.get('total_t')) for m in hist]
            waste_by_uc[code] = {
                'annual_t': _safe_float(ha.get('total_t')),
                'monthly_t': monthly,
                'point_source_t': _safe_float(ha.get('point_source_t')),
                'solid_waste_t': _safe_float(ha.get('area_sw_t')),
                'wastewater_t': _safe_float(ha.get('area_ww_t')),
                'point_pct': 0.0,
                'risk_level': uc.get('emissions', {}).get('risk_level', ''),
                'rank_in_district': uc.get('rank_in_district', 0),
                'intensity_t_per_km2': _safe_float(uc.get('intensity_t_per_km2')),
            }
    return waste_by_uc


def _build_industry_uc_mapping():
    """Build UC_XXXX -> PB-LAH-UCYYY mapping via centroid matching (cached)."""
    cache_key = '_industry_uc_mapping'
    if cache_key in _json_cache:
        return _json_cache[cache_key]

    import math
    spatial = _load_data_file('carbonsense_lahore_spatial_v1.2.json')
    geo_path = os.path.join(DATA_DIR, 'lahore_ucs.geojson')
    with open(geo_path, encoding='utf-8') as f:
        geo = json.load(f)

    def _dist(lat1, lon1, lat2, lon2):
        return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

    mapping = {}
    for suc in spatial.get('uc_emissions', []):
        sc = suc['centroid']
        best_dist = 999
        best_code = ''
        for gf in geo['features']:
            gp = gf['properties']
            d = _dist(sc[0], sc[1], gp['centroid_lat'], gp['centroid_lon'])
            if d < best_dist:
                best_dist = d
                best_code = f"PB-LAH-UC{gp['uc_id']:03d}"
        mapping[suc['uc_id']] = best_code

    _json_cache[cache_key] = mapping
    return mapping


def _build_industry_by_uc(data_type):
    """Industry/Manufacturing: 151 UCs from carbonsense_lahore_spatial_v1.2.json.
    Supports historical (48 months) and forecast (12 months)."""
    data = _load_data_file('carbonsense_lahore_spatial_v1.2.json')
    uc_mapping = _build_industry_uc_mapping()
    result = {}

    for suc in data.get('uc_emissions', []):
        uc_code = uc_mapping.get(suc['uc_id'], '')
        if not uc_code:
            continue

        if data_type == 'forecast':
            fc = suc.get('forecast', {})
            series = fc.get('monthly_series', [])
            monthly = [_safe_float(m.get('total_t')) for m in series]
            result[uc_code] = {
                'annual_t': _safe_float(fc.get('annual_total_t')),
                'by_sector': fc.get('by_sector_annual', {}),
                'intensity_t_per_km2': _safe_float(fc.get('intensity_t_per_km2')),
                'rank_in_district': fc.get('rank_in_district', 0),
                'ci_lower_t': _safe_float(fc.get('annual_ci_lo')),
                'ci_upper_t': _safe_float(fc.get('annual_ci_hi')),
                'monthly_t': monthly,
                'dominant_sector': suc.get('dominant_sector', ''),
                'risk_flags': suc.get('risk_flags', []),
            }
        else:
            hist = suc.get('historical', {})
            series = hist.get('monthly_series', [])
            monthly = [_safe_float(m.get('total_t')) for m in series]
            last12 = monthly[-12:] if len(monthly) >= 12 else monthly
            annual = sum(last12)
            result[uc_code] = {
                'annual_t': round(annual, 2),
                'by_sector': hist.get('by_sector_total', {}),
                'intensity_t_per_km2': round(
                    annual / max(_safe_float(suc.get('area_km2')), 0.01), 1
                ),
                'rank_in_district': 0,
                'ci_lower_t': 0.0,
                'ci_upper_t': 0.0,
                'monthly_t': monthly,
                'dominant_sector': suc.get('dominant_sector', ''),
                'risk_flags': suc.get('risk_flags', []),
            }
    return result


def _build_energy_totals(data_type):
    """Power/Energy: point sources from DB (no UC mapping).
    Returns district total to be evenly distributed across UCs."""
    total = 0.0
    runs = _get_active_runs()
    for run in runs:
        sector = _sector_field(run)
        if sector != 'energy':
            continue
        locs = Location.objects.filter(forecast_run=run)
        for loc in locs:
            pts = EmissionPoint.objects.filter(
                location=loc, point_type=data_type
            )
            for p in pts:
                total += _safe_float(p.emissions)

    # Fallback to JSON
    if total == 0.0:
        try:
            pdata = _load_data_file('power_new.json')
            for loc in pdata.get('locations', []):
                for cd in loc.get('chart_data', []):
                    if isinstance(cd, dict) and cd.get('type') == data_type:
                        total += _safe_float(cd.get('value'))
        except Exception:
            pass
    return total


def _get_monthly_dates(data_type):
    """Return the list of date strings for each sector's monthly_t arrays."""
    # Transport: historical has dates in monthly_series; forecast uses
    # division_total.dates
    t_data = _load_data_file('carbonsense_transport_v16.json')
    if data_type == 'forecast':
        t_dates = t_data.get('division_total', {}).get('dates', [])
    else:
        # Build from first UC's historical series
        first_uc = t_data['uc_emissions'][0] if t_data.get('uc_emissions') else {}
        series = first_uc.get('historical', {}).get('monthly_series', [])
        t_dates = [m['date'] for m in series]

    # Buildings: dates are embedded in each entry
    b_data = _load_data_file('carbonsense_buildings_v15.json')
    first_buc = b_data['uc_data'][0] if b_data.get('uc_data') else {}
    b_series = first_buc.get(
        'forecast' if data_type == 'forecast' else 'historical', []
    )
    b_dates = [row['date'] for row in b_series if isinstance(row, dict)]

    # Waste: dates in historical or chart_data
    w_data = _load_data_file('carbonsense_per_location_waste_v2_3.json')
    alloc = w_data.get('aggregate_forecast', {}).get('uc_allocation', [])
    first_wuc = alloc[0] if alloc else {}
    if data_type == 'forecast':
        w_series = first_wuc.get('chart_data', [])
        w_dates = [row['date'] for row in w_series if isinstance(row, dict)]
    else:
        w_series = first_wuc.get('historical', [])
        w_dates = [row['date'] for row in w_series if isinstance(row, dict)]

    # Industry/Manufacturing: dates from monthly_series
    i_data = _load_data_file('carbonsense_lahore_spatial_v1.2.json')
    first_iuc = i_data['uc_emissions'][0] if i_data.get('uc_emissions') else {}
    if data_type == 'forecast':
        i_series = first_iuc.get('forecast', {}).get('monthly_series', [])
    else:
        i_series = first_iuc.get('historical', {}).get('monthly_series', [])
    i_dates = [m['date'] for m in i_series if isinstance(m, dict)]

    return {
        'transport': t_dates,
        'buildings': b_dates,
        'waste': w_dates,
        'industry': i_dates,
    }


def _find_month_index(dates, target_month):
    """Find the index matching target_month (e.g. '2025-12') in a dates list.
    Dates are like '2025-12-01'. Returns -1 if not found."""
    prefix = target_month  # e.g. '2025-12'
    for i, d in enumerate(dates):
        if d.startswith(prefix):
            return i
    return -1


class UCSummaryViewSet(viewsets.ViewSet):
    """
    Returns one entry per Union Council (151 total) with all sector data.

    Query params:
        data_type:  'historical' or 'forecast' (default: 'forecast')
        view_mode:  'monthly' or 'yearly' (default: 'yearly')
        month:      'YYYY-MM' (only used when view_mode=monthly)

    Each sector entry includes `display_t` — the value to color the
    choropleth by (single month's value in monthly mode, annual sum in
    yearly mode).
    """
    permission_classes = [AllowAny]

    def list(self, request):
        data_type = request.query_params.get('data_type', 'forecast')
        if data_type not in ('historical', 'forecast'):
            data_type = 'forecast'
        view_mode = request.query_params.get('view_mode', 'yearly')
        if view_mode not in ('monthly', 'yearly'):
            view_mode = 'yearly'
        target_month = request.query_params.get('month', '')

        cache_key = f'uc_summary_{data_type}_{view_mode}_{target_month}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        # --- Gather sector data ---
        transport_by_uc = _build_transport_by_uc(data_type)
        buildings_by_uc = _build_buildings_by_uc(data_type)
        waste_by_uc = _build_waste_by_uc(data_type)
        industry_by_uc = _build_industry_by_uc(data_type)
        energy_total = _build_energy_totals(data_type)

        # --- Resolve month index for monthly mode ---
        month_indices = {}  # sector -> index into monthly_t
        month_label = ''
        if view_mode == 'monthly' and target_month:
            sector_dates = _get_monthly_dates(data_type)
            for sector_key, dates in sector_dates.items():
                month_indices[sector_key] = _find_month_index(
                    dates, target_month
                )
            month_label = target_month

        # --- Assemble 151 UC entries ---
        buildings_data = _load_data_file('carbonsense_buildings_v15.json')
        transport_data = _load_data_file('carbonsense_transport_v16.json')

        transport_meta = {
            uc['uc_code']: uc for uc in transport_data.get('uc_emissions', [])
        }
        buildings_meta = {
            uc['uc_code']: uc for uc in buildings_data.get('uc_data', [])
        }

        all_codes = sorted(
            set(transport_meta.keys()) | set(buildings_meta.keys())
        )
        n_ucs = len(all_codes) or 1

        # Energy: still point-source only, distribute evenly
        if view_mode == 'monthly':
            n_months_energy = max(
                len(_get_monthly_dates(data_type).get('buildings', [])), 1
            )
            energy_share = (energy_total / n_months_energy) / n_ucs
        else:
            energy_share = energy_total / n_ucs

        # --- Available months list (for frontend dropdown) ---
        sector_dates = _get_monthly_dates(data_type)
        all_dates = sorted(set(
            sector_dates.get('transport', [])
            + sector_dates.get('buildings', [])
            + sector_dates.get('waste', [])
            + sector_dates.get('industry', [])
        ))
        available_months = sorted(set(d[:7] for d in all_dates))

        results = []
        for uc_code in all_codes:
            tmeta = transport_meta.get(uc_code, {})
            bmeta = buildings_meta.get(uc_code, {})
            uc_name = tmeta.get('uc_name') or bmeta.get('uc_name', '')
            area_km2 = _safe_float(
                tmeta.get('area_km2') or bmeta.get('area_km2')
            )
            lat = _safe_float(
                tmeta.get('centroid_lat')
                or (bmeta.get('coordinates', {}).get('lat'))
            )
            lon = _safe_float(
                tmeta.get('centroid_lon')
                or (bmeta.get('coordinates', {}).get('lon'))
            )

            t_data = transport_by_uc.get(uc_code)
            b_data = buildings_by_uc.get(uc_code)
            w_data = waste_by_uc.get(uc_code)
            i_data = industry_by_uc.get(uc_code)

            # Compute display_t per sector
            def _get_display(sector_data, sector_key, annual_key='annual_t'):
                if not sector_data:
                    return 0.0
                if view_mode == 'yearly':
                    return _safe_float(sector_data.get(annual_key))
                # monthly
                idx = month_indices.get(sector_key, -1)
                mt = sector_data.get('monthly_t', [])
                if 0 <= idx < len(mt):
                    return _safe_float(mt[idx])
                return 0.0

            t_display = _get_display(t_data, 'transport')
            b_display = _get_display(b_data, 'buildings', 'total_t')
            w_display = _get_display(w_data, 'waste')
            i_display = _get_display(i_data, 'industry')

            # Add display_t to each sector dict
            if t_data:
                t_data = {**t_data, 'display_t': round(t_display, 2)}
            if b_data:
                b_data = {**b_data, 'display_t': round(b_display, 2)}
            if w_data:
                w_data = {**w_data, 'display_t': round(w_display, 2)}
            if i_data:
                i_data = {**i_data, 'display_t': round(i_display, 2)}

            total_display = (
                t_display + b_display + w_display + i_display
                + energy_share
            )

            results.append({
                'uc_code': uc_code,
                'uc_name': uc_name,
                'area_km2': area_km2,
                'centroid': [lat, lon],
                'data_type': data_type,
                'view_mode': view_mode,
                'month_label': month_label,
                'sectors': {
                    'transport': t_data,
                    'buildings': b_data,
                    'waste': w_data,
                    'industry': i_data,
                    'energy': round(energy_share, 2),
                },
                'display_t': round(total_display, 2),
                'total_annual_t': round(
                    (t_data['annual_t'] if t_data else 0)
                    + (b_data['total_t'] if b_data else 0)
                    + (w_data['annual_t'] if w_data else 0)
                    + (i_data['annual_t'] if i_data else 0)
                    + (energy_total / n_ucs),
                    2
                ),
                'available_months': available_months,
            })

        cache.set(cache_key, results, CACHE_TTL)
        return Response(results)

    def retrieve(self, request, pk=None):
        """Retrieve a single UC summary by uc_code."""
        all_data = self.list(request).data
        for entry in all_data:
            if entry['uc_code'] == pk:
                return Response(entry)
        return Response({'detail': 'Not found.'}, status=404)
