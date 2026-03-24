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
# Helper: get the currently active forecast run
# ============================================================================

def _get_active_run():
    run = cache.get('active_forecast_run')
    if run is None:
        run = ForecastRun.objects.filter(is_active=True).first()
        if run:
            cache.set('active_forecast_run', run, CACHE_TTL)
    return run


def _sector_field(run):
    """Map forecast_run.sector to the frontend sector column name."""
    mapping = {
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
    return mapping.get(run.sector.lower(), 'energy') if run else 'energy'


# ============================================================================
# Areas endpoint — maps Supabase locations → frontend AreaInfo shape
# ============================================================================

class AreaInfoViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cached = cache.get('areas_list')
        if cached is not None:
            return Response(cached)

        run = _get_active_run()
        if not run:
            return Response([])

        sector = _sector_field(run)
        locations = Location.objects.filter(forecast_run=run)

        results = []
        for loc in locations:
            results.append({
                'id': make_area_id(loc.source, sector),
                'name': loc.source,
                'coordinates': [loc.latitude, loc.longitude],
                'bounds': [
                    [loc.latitude - 0.1, loc.longitude - 0.1],
                    [loc.latitude + 0.1, loc.longitude + 0.1],
                ],
            })
        cache.set('areas_list', results, CACHE_TTL)
        return Response(results)

    def retrieve(self, request, pk=None):
        run = _get_active_run()
        if not run:
            return Response({'detail': 'Not found.'}, status=404)

        sector = _sector_field(run)
        # Reverse the slug to find the location
        for loc in Location.objects.filter(forecast_run=run):
            if make_area_id(loc.source, sector) == pk:
                return Response({
                    'id': pk,
                    'name': loc.source,
                    'coordinates': [loc.latitude, loc.longitude],
                    'bounds': [
                        [loc.latitude - 0.1, loc.longitude - 0.1],
                        [loc.latitude + 0.1, loc.longitude + 0.1],
                    ],
                })
        return Response({'detail': 'Not found.'}, status=404)


# ============================================================================
# Emissions endpoint — maps Supabase emission_points → frontend shape
# ============================================================================

class EmissionDataViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        # Build cache key from query params
        cache_key = f"emissions_{request.query_params.urlencode()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        run = _get_active_run()
        if not run:
            return Response([])

        sector = _sector_field(run)

        queryset = EmissionPoint.objects.filter(
            location__forecast_run=run,
        ).select_related('location')

        # Filter by area_id
        area_id = request.query_params.get('area_id')
        if area_id:
            # Find the matching location
            matching_loc_ids = [
                loc.id for loc in Location.objects.filter(forecast_run=run)
                if make_area_id(loc.source, sector) == area_id
            ]
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
            # Build the per-sector emission row
            emission_row = {
                'transport': 0, 'industry': 0, 'energy': 0,
                'waste': 0, 'buildings': 0,
            }
            emission_row[sector] = ep.emissions

            results.append({
                'id': ep.id,
                'area_id': make_area_id(ep.location.source, sector),
                'area_name': ep.location.source,
                'date': ep.date.isoformat(),
                **emission_row,
                'total': ep.emissions,
                'type': ep.point_type,
            })

        cache.set(cache_key, results, CACHE_TTL)
        return Response(results)

    def retrieve(self, request, pk=None):
        run = _get_active_run()
        if not run:
            return Response({'detail': 'Not found.'}, status=404)

        sector = _sector_field(run)

        try:
            ep = EmissionPoint.objects.select_related('location').get(
                pk=pk, location__forecast_run=run
            )
        except EmissionPoint.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

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
# Leaderboard endpoint — computed from LocationSummary
# ============================================================================

class LeaderboardViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        cached = cache.get('leaderboard_list')
        if cached is not None:
            return Response(cached)

        run = _get_active_run()
        if not run:
            return Response([])

        sector = _sector_field(run)
        summaries = LocationSummary.objects.filter(
            location__forecast_run=run
        ).select_related('location').order_by('-forecast_12m_average')

        results = []
        for rank, s in enumerate(summaries, 1):
            trend_map = {'increasing': 'up', 'declining': 'down', 'stable': 'stable'}
            results.append({
                'rank': rank,
                'area_id': make_area_id(s.location.source, sector),
                'area_name': s.location.source,
                'emissions': s.forecast_12m_average,
                'trend': trend_map.get(s.trend, 'stable'),
                'trend_percentage': abs(s.change_pct),
            })

        cache.set('leaderboard_list', results, CACHE_TTL)
        return Response(results)
