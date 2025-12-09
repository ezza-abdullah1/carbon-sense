from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, EmissionData, AreaInfo, LeaderboardEntry


class SignupSerializer(serializers.ModelSerializer):
    """Serializer for user signup."""

    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'password']
        read_only_fields = ['id']

    def validate_email(self, value):
        """Validate that email is not already in use."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already in use")
        return value

    def create(self, validated_data):
        """Create a new user with encrypted password."""
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        """Validate and authenticate the user."""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )

            if not user:
                raise serializers.ValidationError(
                    "Invalid email or password",
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                "Must include 'email' and 'password'",
                code='authorization'
            )

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details (without password)."""

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class AreaInfoSerializer(serializers.ModelSerializer):
    """Serializer for area information."""

    coordinates = serializers.SerializerMethodField()
    bounds = serializers.SerializerMethodField()

    class Meta:
        model = AreaInfo
        fields = ['id', 'name', 'coordinates', 'bounds']

    def get_coordinates(self, obj):
        """Get coordinates as [lat, lng]."""
        return [obj.latitude, obj.longitude]

    def get_bounds(self, obj):
        """Get bounds as [[lat_min, lng_min], [lat_max, lng_max]]."""
        return [
            [obj.bounds_lat_min, obj.bounds_lng_min],
            [obj.bounds_lat_max, obj.bounds_lng_max]
        ]


class EmissionDataSerializer(serializers.ModelSerializer):
    """Serializer for emission data."""

    area_id = serializers.CharField(source='area.id', read_only=True)
    area_name = serializers.CharField(source='area.name', read_only=True)
    type = serializers.CharField(source='data_type', read_only=True)

    class Meta:
        model = EmissionData
        fields = [
            'id', 'area_id', 'area_name', 'date',
            'transport', 'industry', 'energy', 'waste', 'buildings',
            'total', 'type'
        ]
        read_only_fields = ['id', 'total']


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    """Serializer for leaderboard entries."""

    area_id = serializers.CharField(source='area.id', read_only=True)
    area_name = serializers.CharField(source='area.name', read_only=True)

    class Meta:
        model = LeaderboardEntry
        fields = [
            'rank', 'area_id', 'area_name', 'emissions',
            'trend', 'trend_percentage'
        ]


class EmissionQuerySerializer(serializers.Serializer):
    """Serializer for emission data query parameters."""

    SECTOR_CHOICES = ['transport', 'industry', 'energy', 'waste', 'buildings']
    DATA_TYPE_CHOICES = ['historical', 'forecast']
    INTERVAL_CHOICES = ['monthly', 'yearly', 'custom']

    area_id = serializers.CharField(required=False)
    sector = serializers.ChoiceField(choices=SECTOR_CHOICES, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    data_type = serializers.ChoiceField(choices=DATA_TYPE_CHOICES, required=False)
    interval = serializers.ChoiceField(choices=INTERVAL_CHOICES, required=False)
