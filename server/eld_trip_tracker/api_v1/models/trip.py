from django.contrib.gis.db import models as gis_models
from django.db import models

from .base import CommonFieldsMixin


class Trip(CommonFieldsMixin):
    current_location = gis_models.PointField(srid=4326)
    pickup_location = gis_models.PointField(srid=4326)
    dropoff_location = gis_models.PointField(srid=4326)
    current_cycle_hours = models.FloatField()
    total_distance = models.FloatField(blank=True, null=True)
    total_duration = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Trip from {self.pickup_location} to {self.dropoff_location} ({self.id})"
        )
