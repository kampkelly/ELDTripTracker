from django.contrib.gis.db import models as gis_models
from django.db import models

from .base import CommonFieldsMixin
from .trip import Trip


class Route(CommonFieldsMixin):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="route")
    geometry = gis_models.LineStringField(srid=4326)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Route for Trip {self.trip_id}"
