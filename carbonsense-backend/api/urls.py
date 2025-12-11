from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    logout_view,
    current_user_view,
    EmissionDataViewSet,
    AreaInfoViewSet,
    LeaderboardViewSet
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'emissions', EmissionDataViewSet, basename='emission')
router.register(r'areas', AreaInfoViewSet, basename='area')
router.register(r'leaderboard', LeaderboardViewSet, basename='leaderboard')

urlpatterns = [
    # Authentication endpoints
    # Note: signup and login are now handled by Supabase on the frontend
    # These endpoints are for compatibility and user info retrieval
    path('auth/logout', logout_view, name='logout'),
    path('auth/me', current_user_view, name='current-user'),

    # Include router URLs
    path('', include(router.urls)),
]
