from django.db import models

from .base import CommonFieldsMixin
from .daily_log import DailyLog


class DutyStatus(CommonFieldsMixin):
    STATUS_CHOICES = (
        ("off-duty", "Off Duty"),
        ("sleeper", "Sleeper Berth"),
        ("driving", "Driving"),
        ("on-duty", "On Duty (Not Driving)"),
    )
    daily_log = models.ForeignKey(
        DailyLog, on_delete=models.CASCADE, related_name="duty_statuses"
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    status_description = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return f"{self.get_status_display()} {self.start_time}-{self.end_time}"
