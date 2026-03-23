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
