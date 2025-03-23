from datetime import timedelta

from django.utils import timezone

from api_v1.helpers.distance import Distance
from api_v1.helpers.fuel_stops import (
    METER_TO_MILES_DIVISION,
    SECONDS_IN_HOURS,
    FuelStop,
)
from api_v1.lib.logger import general_logger
from api_v1.lib.mapbox import MapBoxAPI
from api_v1.models import Stop


class TripCalculator:
    """
    This class provides methods to calculate routes, fuel stops, and rest stops for a trip.
    """

    def __init__(self, **kwargs):
        """
        Initializes the TripCalculator with necessary helper classes.
        """
        super().__init__(**kwargs)
        self.distance = Distance()
        self.fuel_stop = FuelStop()
        self.mapbox_api = MapBoxAPI()
        general_logger.info("TripCalculator initialized.")

    def calculate_initial_route(self, trip):
        """
        Gets route details from Mapbox Directions API.

        args:
            trip: The trip object containing location information.

        returns:
            A dictionary containing route geometry, distance (in miles), and duration (in hours).

        raises:
            Exception: If no route is found.
        """
        general_logger.info("Calculating initial route.")
        coords = (
            f"{trip.current_location.x},{trip.current_location.y};"
            f"{trip.pickup_location.x},{trip.pickup_location.y};"
            f"{trip.dropoff_location.x},{trip.dropoff_location.y}"
        )

        data = self.mapbox_api.get_direction(coords)
        if not data.get("routes"):
            general_logger.error("No route found.")
            raise Exception("No route found")

        best_route = data["routes"][0]
        general_logger.info("Initial route calculated successfully.")
        return {
            "geometry": best_route["geometry"],  # Polyline
            "distance": best_route["distance"] / METER_TO_MILES_DIVISION,  # Convert meters to miles
            "duration": best_route["duration"] / SECONDS_IN_HOURS,  # Convert seconds to hours
        }

    def calculate_fuel_stops(self, trip, route, initial_route_data):
        """
        Creates a route with optimized fuel stops.

        args:
            trip: The trip object.
            route: The route object.
            initial_route_data: Initial route data.

        returns:
            The result of adding fuel stops to the route.
        """
        general_logger.info("Calculating fuel stops.")
        return self.fuel_stop.add_fuel_stops(trip, route, initial_route_data)

    def calculate_rest_stops(self, trip, route):
        """
        Calculates required rest stops based on HOS rules.

        args:
            trip: The trip object.
            route: The route object.

        returns:
            The updated trip object with rest stops added.
        """
        general_logger.info("Calculating rest stops.")
        total_driving_minutes = int(trip.total_duration * 60)
        all_accumulated_driving = 0
        accumulated_driving = 0
        rest_break_count = 0
        mandatory_rest_added = False

        # calculate 30-minute breaks every 8 hours (480 minutes)
        timezone_now = timezone.now()
        added_locations = set()
        while all_accumulated_driving < total_driving_minutes:
            remaining_driving = total_driving_minutes - accumulated_driving
            time_until_break = 480 - (accumulated_driving % 480)

            if time_until_break > remaining_driving:
                general_logger.info("No more full breaks needed.")
                break  # no more full breaks needed

            # add rest break
            accumulated_driving += time_until_break
            all_accumulated_driving += time_until_break
            rest_break_count += 1

            # calculate break position in hours
            break_position_hours = accumulated_driving / 60
            fraction = accumulated_driving / total_driving_minutes

            current_cycle_total = trip.current_cycle_hours + (accumulated_driving / 60)
            if current_cycle_total < 70:
                adjusted_break_position_hours = (
                    break_position_hours
                    if not mandatory_rest_added
                    else break_position_hours + 34
                )
                if (
                    self.distance.interpolate_point(route.geometry, fraction)
                    not in added_locations
                ):
                    timezone_now = timezone_now + timedelta(hours=break_position_hours)
                    Stop.objects.create(
                        route=route,
                        stop_type="rest_break",
                        location=self.distance.interpolate_point(
                            route.geometry, fraction
                        ),
                        duration=0.5,
                        timestamp=timezone.now()
                        + timedelta(hours=adjusted_break_position_hours),
                    )
                    added_locations.add(
                        self.distance.interpolate_point(route.geometry, fraction)
                    )
                mandatory_rest_added = False

            # check for 70-hour limit violation after each break
            if not mandatory_rest_added and current_cycle_total >= 70:
                # add mandatory 34-hour restart
                trip = self._add_mandatory_rest(
                    trip, route, break_position_hours - (current_cycle_total - 70)
                )
                mandatory_rest_added = True

                # reset accumulated driving time after restart
                accumulated_driving = 0
                trip.current_cycle_hours = 0  # reset cycle after restart
                trip.save()
                general_logger.info("70-hour limit reached. Mandatory rest added.")

                # continue trip after restart
                continue

            accumulated_driving += 30  # add break time
        general_logger.info("Rest stops calculation complete.")
        return trip

    def _add_mandatory_rest(self, trip, route, position_hours):
        """
        Creates a mandatory 34-hour restart stop.

        args:
            trip: The trip object.
            route: The route object.
            position_hours: The position in hours for the rest stop.

        returns:
            The updated trip object.
        """
        general_logger.info("Adding mandatory rest stop.")
        fraction = position_hours / trip.total_duration
        Stop.objects.create(
            route=route,
            stop_type="mandatory_rest",
            location=self.distance.interpolate_point(route.geometry, fraction),
            duration=34,  # 34-hour restart
            timestamp=trip.created_at + timedelta(hours=position_hours),
        )
        general_logger.info("Mandatory rest stop added successfully.")
        return trip

    def update_durations_from_stops(self, trip):
        """
        Updates the timestamp of each stop in a trip based on the duration of the preceding stop.
        Also updates the trip's total duration.

        args:
            trip: The trip object to update.

        returns:
            The updated trip object.
        """
        general_logger.info(f"Updating durations from stops for trip: {trip.id}")
        stops = Stop.objects.filter(route__trip=trip).order_by("timestamp")

        duration_to_add = 0

        for stop in stops:
            general_logger.info(f"Stop location: {stop}")
        for ind, stop in enumerate(stops, 0):
            # update the next stop
            duration_to_add += stop.duration
            if ind + 1 <= len(stops) - 1:
                next_stop = stops[ind + 1]
                next_stop = Stop.objects.get(id=next_stop.id)
                next_stop.timestamp = next_stop.timestamp + timedelta(
                    hours=duration_to_add
                )
                next_stop.save()


        # update the trip's total duration
        general_logger.info(f"Before updating total duration: {trip.total_duration}")
        trip.total_duration += duration_to_add
        general_logger.info(f"Updated trip total duration: {trip.total_duration}")
        trip.save()
        general_logger.info(f"Durations updated successfully for trip: {trip.id}")

        return trip
