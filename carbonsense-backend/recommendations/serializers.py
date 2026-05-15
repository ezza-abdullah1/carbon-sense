from rest_framework import serializers


class CoordinatesSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class RecommendationRequestSerializer(serializers.Serializer):
    coordinates = CoordinatesSerializer()
    sector = serializers.ChoiceField(
        choices=['transport', 'industry', 'energy', 'waste', 'buildings']
    )
    area_name = serializers.CharField(max_length=255)
    area_id = serializers.CharField(max_length=100)


class RecommendationFeedbackSerializer(serializers.Serializer):
    run_id = serializers.UUIDField(required=False, allow_null=True)
    area_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    sector = serializers.ChoiceField(
        choices=['transport', 'industry', 'energy', 'waste', 'buildings'],
        required=False,
        allow_blank=True,
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback_text = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=''
    )
    helpful_action_indices = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=20),
        required=False,
        default=list,
        max_length=20,
    )
    unhelpful_action_indices = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=20),
        required=False,
        default=list,
        max_length=20,
    )

    def validate(self, attrs):
        if not attrs.get('run_id') and not attrs.get('area_id'):
            raise serializers.ValidationError(
                "Either run_id or (area_id + sector) must be provided."
            )
        return attrs
