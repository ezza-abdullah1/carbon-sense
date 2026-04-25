from django.urls import path

from recommendations.views import (
    chat,
    generate_recommendations,
    get_chat_history,
    get_recommendation,
    submit_feedback,
)

urlpatterns = [
    path('generate', generate_recommendations, name='generate-recommendations'),
    path('<uuid:rid>', get_recommendation, name='get-recommendation'),
    path('<uuid:rid>/chat', chat, name='recommendation-chat'),
    path('<uuid:rid>/chat/history', get_chat_history, name='recommendation-chat-history'),
    path('<uuid:rid>/feedback', submit_feedback, name='recommendation-feedback'),
]
