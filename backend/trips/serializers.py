from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers


class PlaceSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

    def to_internal_value(self, data):
        place = super().to_internal_value(data)
        return {'name': place['name'], 'point': (place['lat'], place['lon'])}


class TripRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.IntegerField(min_value=0, max_value=200_000)
    checkpoint_interval_miles = serializers.ChoiceField(choices=settings.CHECKPOINT_INTERVALS_MILES)

    def validate_departure_time(self, value):
        now = timezone.now()
        # A little slack for the time it takes to fill in the form.
        if value < now - timedelta(hours=1):
            raise serializers.ValidationError('Departure time is in the past.')
        if value > now + timedelta(days=settings.MAX_DAYS_AHEAD):
            raise serializers.ValidationError(
                f'Forecasts only go about a week ahead, so departure must be within {settings.MAX_DAYS_AHEAD} days.'
            )
        return value

    def validate(self, attrs):
        if attrs['origin']['point'] == attrs['destination']['point']:
            raise serializers.ValidationError('Origin and destination must be different places.')
        return attrs
