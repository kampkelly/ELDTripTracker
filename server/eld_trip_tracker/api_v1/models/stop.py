from django.contrib.gis.db import models as gis_models
from django.db import models

from .base import CommonFieldsMixin
from .route import Route


class Stop(CommonFieldsMixin):
    STOP_TYPES = (
        ("fuel", "Fuel Stop"),
        ("rest_break", "30-Minute Break"),
        ("mandatory_rest", "10-Hour Rest"),
        ("pickup", "Pickup"),
        ("dropoff", "Dropoff"),
    )
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="stops")
    stop_type = models.CharField(max_length=20, choices=STOP_TYPES)
    location = gis_models.PointField(srid=4326)
    duration = models.FloatField()
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.get_stop_type_display()} at {self.timestamp}"
