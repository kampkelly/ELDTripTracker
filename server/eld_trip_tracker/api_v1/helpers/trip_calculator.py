from datetime import timedelta

from api_v1.helpers.distance import Distance
from api_v1.helpers.fuel_stops import (
    METER_TO_MILES_DIVISION,
    SECONDS_IN_HOURS,
    FuelStop,
)
from api_v1.lib.logger import general_logger
from api_v1.lib.mapbox import MapBoxAPI
from api_v1.models import Stop
from django.utils import timezone


class TripCalculator:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.distance = Distance()
        self.fuel_stop = FuelStop()
        self.mapbox_api = MapBoxAPI()

    def calculate_initial_route(self, trip):
        """Get route details from Mapbox Directions API"""
        coords = (
            f"{trip.current_location.x},{trip.current_location.y};"
            f"{trip.pickup_location.x},{trip.pickup_location.y};"
            f"{trip.dropoff_location.x},{trip.dropoff_location.y}"
        )

        data = self.mapbox_api.get_direction(coords)
        if not data.get("routes"):
            raise Exception("No route found")

        best_route = data["routes"][0]
        return {
            "geometry": best_route["geometry"],  # Polyline
            "distance": best_route["distance"]
            / METER_TO_MILES_DIVISION,  # Convert meters to miles
            "duration": best_route["duration"]
            / SECONDS_IN_HOURS,  # Convert seconds to hours
        }

    def calculate_fuel_stops(self, trip, route, initial_route_data):
        """Create Route with optimized fuel stops"""
        return self.fuel_stop.add_fuel_stops(trip, route, initial_route_data)

    def calculate_rest_stops(self, trip, route):
        """Calculate required rest stops based on HOS rules"""
        total_driving_minutes = int(trip.total_duration * 60)
        all_accumulated_driving = 0
        accumulated_driving = 0
        rest_break_count = 0
        mandatory_rest_added = False

        # Calculate 30-minute breaks every 8 hours (480 minutes)
        timezone_now = timezone.now()
        added_locations = set()
        while all_accumulated_driving < total_driving_minutes:
            remaining_driving = total_driving_minutes - accumulated_driving
            time_until_break = 480 - (accumulated_driving % 480)

            if time_until_break > remaining_driving:
                break  # No more full breaks needed

            # Add rest break
            accumulated_driving += time_until_break
            all_accumulated_driving += time_until_break
            rest_break_count += 1

            # Calculate break position in hours
            break_position_hours = accumulated_driving / 60
            fraction = accumulated_driving / total_driving_minutes

            current_cycle_total = trip.current_cycle_hours + (accumulated_driving / 60)
            if current_cycle_total < 70:
                adjusted_break_position_hours = (
                    break_position_hours
                    if not mandatory_rest_added
                    else break_position_hours + 34
                )
                if self.distance.interpolate_point(route.geometry, fraction) not in added_locations:
                    timezone_now = timezone_now + timedelta(hours=break_position_hours)
                    Stop.objects.create(
                        route=route,
                        stop_type="rest_break",
                        location=self.distance.interpolate_point(route.geometry, fraction),
                        duration=0.5,
                        timestamp=timezone.now() + timedelta(hours=adjusted_break_position_hours),
                    )
                    added_locations.add(self.distance.interpolate_point(route.geometry, fraction))
                mandatory_rest_added = False

            # Check for 70-hour limit violation after each break
            if not mandatory_rest_added and current_cycle_total >= 70:
                # Add mandatory 34-hour restart
                trip = self._add_mandatory_rest(trip, route, break_position_hours - (current_cycle_total - 70))
                mandatory_rest_added = True

                # Reset accumulated driving time after restart
                accumulated_driving = 0
                trip.current_cycle_hours = 0  # Reset cycle after restart
                trip.save()

                # Continue trip after restart
                continue

            accumulated_driving += 30  # Add break time

        return trip

    def _add_mandatory_rest(self, trip, route, position_hours):
        """Create mandatory 34-hour restart stop"""
        fraction = position_hours / trip.total_duration
        Stop.objects.create(
            route=route,
            stop_type="mandatory_rest",
            location=self.distance.interpolate_point(route.geometry, fraction),
            duration=34,  # 34-hour restart
            timestamp=trip.created_at + timedelta(hours=position_hours),
        )

        return trip

    def update_durations_from_stops(self, trip):
        """
        Updates the timestamp of each stop in a trip based on the duration of the preceding stop.
        Also updates the trip's total duration.
        """
        stops = Stop.objects.filter(route__trip=trip).order_by("timestamp")

        duration_to_add = 0

        for stop in stops:
            general_logger.info(f"Stop location: {stop}")
        for ind, stop in enumerate(stops, 0):
            # Update the next stop
            duration_to_add += stop.duration
            if ind + 1 <= len(stops) - 1:
                next_stop = stops[ind + 1]
                next_stop = Stop.objects.get(id=next_stop.id)
                general_logger.info(
                    f"Before update: {next_stop.stop_type}, {next_stop.timestamp}"
                )
                next_stop.timestamp = next_stop.timestamp + timedelta(
                    hours=duration_to_add
                )
                general_logger.info(
                    f"Updating next stop: {next_stop.stop_type}, "
                    f"{next_stop.timestamp}, duration: {stop.duration}, all: {duration_to_add}"
                )
                next_stop.save()
                general_logger.info(
                    f"Next stop updated: {next_stop.stop_type}, {next_stop.timestamp}"
                )

            general_logger.info(f"Adding to temp duration: {duration_to_add}")

        # Update the trip's total duration
        general_logger.info(f"Before updating total duration: {trip.total_duration}")
        trip.total_duration += duration_to_add
        general_logger.info(f"Updated trip total duration: {trip.total_duration}")
        trip.save()

        return trip
