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
        return self._parse_location(value, "current_location")

    def validate_pickup_location(self, value):
        return self._parse_location(value, "pickup_location")

    def validate_dropoff_location(self, value):
        return self._parse_location(value, "dropoff_location")

    def _parse_location(self, location_data, field_name):
        try:
            name = location_data["name"]
            lat, lon = map(float, location_data["coordinates"])
            point = Point(lon, lat, srid=4326)
            return {"name": name, "point": point}
        except (KeyError, ValueError, TypeError) as e:
            raise serializers.ValidationError(f"Invalid {field_name} data: {e}")

    def create(self, validated_data):
        current_location_data = validated_data.pop("current_location")
        pickup_location_data = validated_data.pop("pickup_location")
        dropoff_location_data = validated_data.pop("dropoff_location")

        trip = Trip.objects.create(
            current_location=current_location_data["point"],
            current_location_name=current_location_data["name"],
            pickup_location=pickup_location_data["point"],
            pickup_location_name=pickup_location_data["name"],
            dropoff_location=dropoff_location_data["point"],
            dropoff_location_name=dropoff_location_data["name"],
            **validated_data,
        )
        return trip

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
