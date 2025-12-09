from rest_framework import status, viewsets, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.db.models import Q
from .models import User, EmissionData, AreaInfo, LeaderboardEntry
from .serializers import (
    SignupSerializer,
    LoginSerializer,
    UserSerializer,
    EmissionDataSerializer,
    AreaInfoSerializer,
    LeaderboardEntrySerializer,
    EmissionQuerySerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    """
    User signup endpoint.

    POST /api/auth/signup
    Body: { "email": "user@example.com", "name": "User Name", "password": "password123" }
    """
    serializer = SignupSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        login(request, user)
        user_data = UserSerializer(user).data
        return Response(
            {'user': user_data},
            status=status.HTTP_201_CREATED
        )

    return Response(
        {'error': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint.

    POST /api/auth/login
    Body: { "email": "user@example.com", "password": "password123" }
    """
    serializer = LoginSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        user_data = UserSerializer(user).data
        return Response(
            {'user': user_data},
            status=status.HTTP_200_OK
        )

    return Response(
        {'error': serializer.errors},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint.

    POST /api/auth/logout
    """
    logout(request)
    return Response(
        {'message': 'Successfully logged out'},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """
    Get current authenticated user.

    GET /api/auth/me
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class EmissionDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing emission data.

    GET /api/emissions/
    GET /api/emissions/{id}/

    Query parameters:
    - area_id: Filter by area ID
    - sector: Filter by sector (transport, industry, energy, waste, buildings)
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - data_type: Filter by data type (historical, forecast)
    - interval: Time interval (monthly, yearly, custom)
    """
    queryset = EmissionData.objects.all()
    serializer_class = EmissionDataSerializer
    permission_classes = [AllowAny]  # Changed for easier testing

    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = EmissionData.objects.select_related('area').all()

        # Validate and get query parameters
        query_serializer = EmissionQuerySerializer(data=self.request.query_params)
        if not query_serializer.is_valid():
            return queryset

        params = query_serializer.validated_data

        # Filter by area
        if 'area_id' in params:
            queryset = queryset.filter(area_id=params['area_id'])

        # Filter by date range
        if 'start_date' in params:
            queryset = queryset.filter(date__gte=params['start_date'])
        if 'end_date' in params:
            queryset = queryset.filter(date__lte=params['end_date'])

        # Filter by data type
        if 'data_type' in params:
            queryset = queryset.filter(data_type=params['data_type'])

        return queryset


class AreaInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing area information.

    GET /api/areas/
    GET /api/areas/{id}/
    """
    queryset = AreaInfo.objects.all()
    serializer_class = AreaInfoSerializer
    permission_classes = [AllowAny]  # Changed for easier testing


class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing leaderboard entries.

    GET /api/leaderboard/
    """
    queryset = LeaderboardEntry.objects.select_related('area').all()
    serializer_class = LeaderboardEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get leaderboard entries, optionally filtered by date range."""
        queryset = super().get_queryset()

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(period_start__gte=start_date)
        if end_date:
            queryset = queryset.filter(period_end__lte=end_date)

        return queryset.order_by('rank')
