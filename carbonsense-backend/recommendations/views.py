from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from .serializers import RecommendationRequestSerializer
from .models import RecommendationCache
from .agent import RecommendationAgent


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_recommendations(request):
    """
    Generate AI-powered emission reduction recommendations using Agentic RAG.

    POST /api/recommendations/generate
    Body: {
        "coordinates": {"lat": 31.5204, "lng": 74.3587},
        "sector": "transport",
        "area_name": "Gulberg",
        "area_id": "gulberg_transport"
    }
    """
    serializer = RecommendationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data

    # Check cache first
    cache_entry = RecommendationCache.objects.filter(
        area_id=data['area_id'],
        sector=data['sector'],
        expires_at__gt=timezone.now()
    ).first()

    if cache_entry:
        return Response(cache_entry.response_data)

    # Generate fresh recommendations
    try:
        agent = RecommendationAgent()
        result = agent.generate(
            area_id=data['area_id'],
            area_name=data['area_name'],
            sector=data['sector'],
            coordinates=data['coordinates']
        )
        return Response(result)
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
