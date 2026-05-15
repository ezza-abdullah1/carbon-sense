from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    signup_view,
    login_view,
    logout_view,
    current_user_view,
    EmissionDataViewSet,
    AreaInfoViewSet,
    LeaderboardViewSet,
    UCSummaryViewSet,
    stats_view,
    latest_emissions_by_area,
    emissions_timeline,
    power_plants_view,
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'emissions', EmissionDataViewSet, basename='emission')
router.register(r'areas', AreaInfoViewSet, basename='area')
router.register(r'leaderboard', LeaderboardViewSet, basename='leaderboard')
router.register(r'uc-summary', UCSummaryViewSet, basename='uc-summary')

urlpatterns = [
    # Authentication endpoints
    path('auth/signup', signup_view, name='signup'),
    path('auth/login', login_view, name='login'),
    path('auth/logout', logout_view, name='logout'),
    path('auth/me', current_user_view, name='current-user'),

    # Aggregate stats for dashboard KPI cards (no row-level fetch needed)
    path('stats/', stats_view, name='stats'),

    # Pre-aggregated emission shapes — keep raw `/emissions/` for actual row queries.
    path('emissions/latest-by-area/', latest_emissions_by_area, name='latest-by-area'),
    path('emissions/timeline/', emissions_timeline, name='emissions-timeline'),

    # Energy point sources (power plants). Not a UC sector — has lat/lng coords.
    path('power-plants/', power_plants_view, name='power-plants'),

    # Include router URLs
    path('', include(router.urls)),
]
