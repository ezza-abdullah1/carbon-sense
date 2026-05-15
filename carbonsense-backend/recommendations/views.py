import hashlib
import logging
import os
from datetime import date

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .agent import RecommendationAgent
from .models import RecommendationCache, RecommendationFeedback
from .n8n_client import N8nClient, N8nUnavailable
from .serializers import (
    RecommendationFeedbackSerializer,
    RecommendationRequestSerializer,
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_recommendations(request):
    """Generate emission-reduction recommendations.

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
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Django-side cache (covers template_fallback path and acts as belt-and-
    # braces over n8n's own Supabase cache).
    cache_entry = RecommendationCache.objects.filter(
        area_id=data['area_id'],
        sector=data['sector'],
        expires_at__gt=timezone.now(),
    ).first()
    if cache_entry:
        cached = dict(cache_entry.response_data)
        cached['from_cache'] = True
        return Response(cached)

    try:
        agent = RecommendationAgent()
        result = agent.generate(
            area_id=data['area_id'],
            area_name=data['area_name'],
            sector=data['sector'],
            coordinates=data['coordinates'],
            trace=True,
        )
        return Response(result)
    except Exception as e:
        logger.exception("Recommendation generation failed")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _derive_anon_id(request) -> str:
    """Derive a stable-per-day, anonymous voter ID from request headers."""
    ip = (
        request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        or request.META.get('REMOTE_ADDR', '')
        or 'unknown'
    )
    ua = request.META.get('HTTP_USER_AGENT', 'unknown')
    daily_salt = os.environ.get('FEEDBACK_DAILY_SALT_PREFIX', 'cs-anon')
    today_str = date.today().isoformat()
    blob = f"{ip}|{ua}|{daily_salt}|{today_str}"
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:32]


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_feedback(request):
    """Record anonymous user feedback on a recommendation.

    POST /api/recommendations/feedback
    Body: {
        "run_id": "<uuid from generate response, optional>",
        "area_id": "...",
        "sector": "transport",
        "rating": 1..5,
        "feedback_text": "...",
        "helpful_action_indices": [0, 2],
        "unhelpful_action_indices": [3]
    }

    Primary path: forward to n8n /feedback (writes to Supabase).
    Fallback: persist locally so a sweeper job can replay it later.
    """
    serializer = RecommendationFeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    payload = dict(serializer.validated_data)
    payload['anon_id'] = _derive_anon_id(request)

    client = N8nClient()
    if client.configured:
        try:
            result = client.submit_feedback(payload)
            return Response({'ok': True, 'forwarded': True, **result})
        except N8nUnavailable as e:
            logger.warning(f"n8n feedback forward failed, buffering locally: {e}")

    # Local buffer — sweeper job (TODO) will replay these to n8n later.
    RecommendationFeedback.objects.create(
        run_id=payload.get('run_id'),
        area_id=payload.get('area_id', ''),
        sector=payload.get('sector', ''),
        rating=payload['rating'],
        feedback_text=payload.get('feedback_text', ''),
        helpful_action_indices=payload.get('helpful_action_indices', []),
        unhelpful_action_indices=payload.get('unhelpful_action_indices', []),
        anon_id=payload['anon_id'],
        forwarded_to_n8n=False,
    )
    return Response({'ok': True, 'forwarded': False, 'buffered': True})
