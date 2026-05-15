from django.urls import path

from .views import generate_recommendations, submit_feedback

urlpatterns = [
    path('generate', generate_recommendations, name='generate-recommendations'),
    path('feedback', submit_feedback, name='submit-recommendation-feedback'),
]
