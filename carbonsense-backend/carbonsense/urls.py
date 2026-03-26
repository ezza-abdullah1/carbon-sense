"""
URL configuration for carbonsense project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

try:
    urlpatterns.append(
        path('api/recommendations/', include('recommendations.urls')),
    )
except Exception:
    pass  # recommendations app has stale model imports (AreaInfo/EmissionData removed)
