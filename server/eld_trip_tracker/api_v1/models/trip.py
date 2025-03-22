from datetime import datetime, time, timedelta

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone

from .base import CommonFieldsMixin


class Trip(CommonFieldsMixin):
    current_location = gis_models.PointField(srid=4326)
    current_location_name = models.CharField(max_length=255, default="")
    pickup_location = gis_models.PointField(srid=4326)
    pickup_location_name = models.CharField(max_length=255, default="")
    dropoff_location = gis_models.PointField(srid=4326)
    dropoff_location_name = models.CharField(max_length=255, default="")
    current_cycle_hours = models.FloatField()
    total_distance = models.FloatField(blank=True, null=True)
    total_duration = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Trip from {self.pickup_location} to {self.dropoff_location} ({self.id})"
        )

    def create_daily_logs(self):
        from .daily_log import DailyLog
        from .duty_status import DutyStatus
        from .stop import Stop

        stops = Stop.objects.filter(route__trip=self).order_by("timestamp")
        current_datetime = self.created_at
        daily_logs = {}
        daily_mileage = {}  # Track mileage per day

        # Create timeline events
        timeline = []
        for stop in stops:
            # Add driving period before stop
            if stop.timestamp > current_datetime:
                timeline.append(
                    ("driving", current_datetime, stop.timestamp, stop.stop_type)
                )

            # Add the stop itself
            timeline.append(
                (
                    stop.stop_type,
                    stop.timestamp,
                    stop.timestamp + timedelta(hours=stop.duration),
                    stop.stop_type,
                )
            )
            current_datetime = stop.timestamp + timedelta(hours=stop.duration)

        # Process timeline by day
        start_date = self.created_at.date()
        end_date = (self.created_at + timedelta(hours=self.total_duration)).date()

        for day in (
            start_date + timedelta(n) for n in range((end_date - start_date).days + 1)
        ):
            daily_log, _ = DailyLog.objects.get_or_create(
                trip=self,
                date=day,
                defaults={
                    "total_miles": 0,
                    "total_mileage": 0,
                    "remarks": f"Auto-generated log for {day}",
                    "driver_signature": "",
                },
            )
            daily_logs[day] = daily_log
            daily_mileage[day] = 0.0

        # Create duty status entries and calculate mileage
        for event in timeline:
            event_type, start, end, status_description = event
            current_day = start.date()

            while current_day <= end.date():
                day_log = daily_logs[current_day]
                day_start = timezone.make_aware(datetime.combine(current_day, time.min))
                day_end = timezone.make_aware(datetime.combine(current_day, time.max))

                # Calculate overlap with current day
                overlap_start = max(start, day_start)
                overlap_end = min(end, day_end)

                if overlap_start >= overlap_end:
                    current_day += timedelta(days=1)
                    continue

                # Calculate mileage for driving periods
                if event_type == "driving":
                    # Get the fraction of the route for this driving period
                    total_trip_duration = (
                        self.created_at + timedelta(hours=self.total_duration)
                    ) - self.created_at
                    driving_duration = overlap_end - overlap_start
                    fraction = (
                        driving_duration.total_seconds()
                        / total_trip_duration.total_seconds()
                    )

                    # Calculate distance for this driving period
                    driving_distance = self.total_distance * fraction
                    daily_mileage[current_day] += driving_distance

                # Determine status type
                if event_type == "mandatory_rest":
                    status = "off-duty"
                elif event_type == "rest_break":
                    status = "sleeper"
                elif event_type in ("fuel", "pickup", "dropoff"):
                    status = "on-duty"
                else:  # driving
                    status = "driving"

                DutyStatus.objects.create(
                    daily_log=day_log,
                    start_time=overlap_start.time(),
                    end_time=overlap_end.time(),
                    status=status,
                    status_description=status_description,
                )

                # Move to next day if needed
                if overlap_end == day_end:
                    current_day += timedelta(days=1)
                else:
                    break

        # Update daily logs with calculated mileage
        for day, mileage in daily_mileage.items():
            daily_log = daily_logs[day]
            daily_log.total_miles = mileage
            daily_log.save()

        # delete empty daily logs
        for day, daily_log in list(daily_logs.items()):
            if not daily_log.duty_statuses.exists():
                daily_log.delete()
                del daily_logs[day]
