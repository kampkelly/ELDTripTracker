from api_v1.models import Trip
from django.contrib.gis.geos import Point
from rest_framework import serializers


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = [
            "id",
            "current_location",
            "pickup_location",
            "dropoff_location",
            "current_cycle_hours",
            "total_distance",
            "total_duration",
            "created_at",
        ]
        read_only_fields = [
            "total_distance",
            "total_duration",
            "created_at",
            "updated_at",
        ]

    def validate_current_location(self, value):
        return self._parse_point(value)

    def validate_pickup_location(self, value):
        return self._parse_point(value)

    def validate_dropoff_location(self, value):
        return self._parse_point(value)

    def _parse_point(self, value):
        try:
            lat, lon = map(float, value)
            return Point(lon, lat, srid=4326)
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(f"Invalid coordinates: {e}")

    def to_representation(self, instance):
        """Convert GeoJSON fields to a more API-friendly format."""
        representation = super().to_representation(instance)
        representation["current_location"] = {
            "latitude": instance.current_location.y,
            "longitude": instance.current_location.x,
        }
        representation["pickup_location"] = {
            "latitude": instance.pickup_location.y,
            "longitude": instance.pickup_location.x,
        }
        representation["dropoff_location"] = {
            "latitude": instance.dropoff_location.y,
            "longitude": instance.dropoff_location.x,
        }
        return representation
