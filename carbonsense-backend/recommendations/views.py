from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from recommendations.agent import RecommendationAgent
from recommendations.conversation import ConversationManager
from recommendations.feedback import FeedbackService
from recommendations.models import (
    Recommendation,
    RecommendationCache,
    RecommendationConversation,
)
from recommendations.serializers import (
    ChatTurnSerializer,
    ConversationSerializer,
    FeedbackSerializer,
    RecommendationDetailSerializer,
    RecommendationRequestSerializer,
)


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
        return Response({'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # TTL-based dedup so two refreshes within the cache window do not re-run the LLM.
    cache_entry = RecommendationCache.objects.filter(
        area_id=data['area_id'],
        sector=data['sector'],
        expires_at__gt=timezone.now(),
    ).first()

    if cache_entry:
        cached = dict(cache_entry.response_data or {})
        cached['from_cache'] = True
        return Response(cached)

    try:
        agent = RecommendationAgent()
        # Diagnostic — make it obvious which provider the running process is using.
        print(
            f"[generate] LLM_PROVIDER={settings.LLM_PROVIDER} "
            f"backend={agent.llm.provider_name} model={agent.llm.model_name} "
            f"available={agent.llm.available}"
        )
        result = agent.generate(
            area_id=data['area_id'],
            area_name=data['area_name'],
            sector=data['sector'],
            coordinates=data['coordinates'],
            trace=True,
        )
    except Exception as exc:
        return Response(
            {'success': False, 'error': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    ttl_hours = int(getattr(settings, 'RECOMMENDATION_CACHE_TTL_HOURS', 24))
    RecommendationCache.objects.update_or_create(
        area_id=data['area_id'],
        sector=data['sector'],
        defaults={
            'response_data': result,
            'confidence_scores': result.get('confidence', {}),
            'expires_at': timezone.now() + timedelta(hours=ttl_hours),
            'policy_doc_count': len((result.get('retrieved_context') or {}).get('policy_titles', [])),
            'emissions_data_hash': '',
        },
    )

    result['from_cache'] = False
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_recommendation(request, rid):
    """GET /api/recommendations/<uuid:rid> — rehydrate a stored recommendation."""
    rec = get_object_or_404(Recommendation, pk=rid)
    payload = RecommendationDetailSerializer(rec).data
    return Response(payload)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat(request, rid):
    """POST /api/recommendations/<uuid:rid>/chat — follow-up Q&A."""
    serializer = ChatTurnSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        manager = ConversationManager()
        result = manager.handle_turn(
            recommendation_id=rid,
            user_message=serializer.validated_data['message'],
        )
    except Recommendation.DoesNotExist:
        return Response({'error': 'recommendation_not_found'},
                        status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({'error': str(exc)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_chat_history(request, rid):
    """GET /api/recommendations/<uuid:rid>/chat — return current conversation."""
    rec = get_object_or_404(Recommendation, pk=rid)
    conv = RecommendationConversation.objects.filter(recommendation=rec).first()
    if not conv:
        return Response({'recommendation_id': str(rec.id), 'messages': []})
    return Response({
        'recommendation_id': str(rec.id),
        'messages': conv.messages or [],
        **ConversationSerializer(conv).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_feedback(request, rid):
    """POST /api/recommendations/<uuid:rid>/feedback — thumbs up/down per section."""
    serializer = FeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        fb = FeedbackService.record(
            recommendation_id=rid,
            section=serializer.validated_data['section'],
            rating=serializer.validated_data['rating'],
            comment=serializer.validated_data.get('comment', ''),
        )
    except Recommendation.DoesNotExist:
        return Response({'error': 'recommendation_not_found'},
                        status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({'error': str(exc)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'ok': True,
        'feedback_id': str(fb.id),
        'recommendation_id': str(fb.recommendation_id),
        'section': fb.section,
        'rating': fb.rating,
    }, status=status.HTTP_201_CREATED)
