from rest_framework import serializers

from recommendations.models import (
    Recommendation,
    RecommendationConversation,
    RecommendationFeedback,
)


class CoordinatesSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class RecommendationRequestSerializer(serializers.Serializer):
    coordinates = CoordinatesSerializer()
    sector = serializers.ChoiceField(
        choices=['transport', 'industry', 'energy', 'waste', 'buildings']
    )
    area_name = serializers.CharField(max_length=255)
    area_id = serializers.CharField(max_length=255)


class ChatTurnSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000)


class FeedbackSerializer(serializers.Serializer):
    SECTION_CHOICES = [
        'summary', 'immediate_actions', 'long_term_strategies',
        'policy_recommendations', 'monitoring_metrics', 'risk_factors', 'overall',
    ]

    section = serializers.ChoiceField(choices=SECTION_CHOICES)
    rating = serializers.IntegerField(min_value=-1, max_value=1)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_rating(self, value):
        if value not in (-1, 1):
            raise serializers.ValidationError("rating must be +1 or -1")
        return value


class RecommendationDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = [
            'id', 'area_id', 'area_name', 'sector', 'coordinates',
            'content_json', 'retrieved_context', 'model_used', 'provider',
            'generation_ms', 'generated_at',
        ]


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationConversation
        fields = ['id', 'messages', 'created_at', 'updated_at']


class FeedbackRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationFeedback
        fields = ['id', 'section', 'rating', 'comment', 'created_at']
