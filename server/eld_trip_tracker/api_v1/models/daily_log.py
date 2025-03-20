from django.db import models

from .base import CommonFieldsMixin
from .trip import Trip


class DailyLog(CommonFieldsMixin):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="daily_logs")
    date = models.DateField()
    total_miles = models.FloatField()
    total_mileage = models.FloatField()
    remarks = models.TextField(blank=True)
    driver_signature = models.CharField(max_length=250, null=False, unique=False)

    class Meta:
        unique_together = ["trip", "date"]

    def __str__(self):
        return f"Log for {self.date} - Trip {self.trip_id}"
