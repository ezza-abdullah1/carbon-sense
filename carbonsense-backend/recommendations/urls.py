from django.urls import path
from .views import generate_recommendations

urlpatterns = [
    path('generate', generate_recommendations, name='generate-recommendations'),
]
