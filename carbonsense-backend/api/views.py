import math
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.core.cache import cache
from .models import (
    User, ForecastRun, Location, EmissionPoint,
    LocationSummary, AggregateForecastPoint, make_area_id,
)
from .serializers import SignupSerializer, LoginSerializer, UserSerializer

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
            for loc in Location.objects.filter(forecast_run=run):
                lat = _safe_float(loc.latitude)
                lng = _safe_float(loc.longitude)
                results.append({
                    'id': make_area_id(loc.source, sector),
                    'name': loc.source,
                    'coordinates': [lat, lng],
                    'bounds': [
                        [lat - 0.1, lng - 0.1],
                        [lat + 0.1, lng + 0.1],
                    ],
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
                    return Response({
                        'id': pk,
                        'name': loc.source,
                        'coordinates': [lat, lng],
                        'bounds': [
                            [lat - 0.1, lng - 0.1],
                            [lat + 0.1, lng + 0.1],
                        ],
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
