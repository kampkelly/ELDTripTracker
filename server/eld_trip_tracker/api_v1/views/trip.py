from datetime import timedelta

import polyline
from api_v1.helpers.distance import Distance
from api_v1.helpers.fuel_stops import FuelStop
from api_v1.lib.logger import general_logger
from api_v1.lib.mapbox import MapBoxAPI
from api_v1.models import DailyLog, DutyStatus, Route, Stop, Trip
from api_v1.serializers import TripSerializer
from django.contrib.gis.geos import LineString, Point
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView


def build_response(trip):
    """
    Construct a response containing trip data.
    """
    return {
        "trip": TripSerializer(trip).data,
    }


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_query_param = "page"
    max_page_size = 5

    def get_paginated_response(self, data):
        """
        Customize the paginated response format.
        """
        return Response(
            {
                "links": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "count": self.page.paginator.count,
                "results": data,
            }
        )


class TripListCreateAPIView(APIView):

    pagination_class = StandardResultsSetPagination

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.distance = Distance()
        self.fuel_stop = FuelStop()
        self.mapbox_api = MapBoxAPI()

    def post(self, request):
        try:
            serializer = TripSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            Stop.objects.all().delete()
            DailyLog.objects.all().delete()
            DutyStatus.objects.all().delete()
            Route.objects.all().delete()
            Trip.objects.all().delete()
            trip = serializer.save()

            route_data = self._calculate_initial_route(trip)
            created_route = Route.objects.create(
                trip=trip,
                geometry=LineString(polyline.decode(route_data["geometry"], 5)),
            )
            trip, route, _, _, _ = self._calculate_fuel_stops(
                trip, created_route, route_data
            )
            trip = self._calculate_rest_stops(trip, route)
            trip = self.update_durations_from_stops(trip)

            self.create_logs(trip)

            daily_logs = trip.daily_logs.all().order_by("date")

            for daily_log in daily_logs:
                grid = self.eld_log.generate_log_grid(daily_log)
                log_data = self.eld_log.get_log_metadata(trip, grid)
                log_data["entries"] = grid
                log_data["total_miles"] = round(daily_log.total_miles, 2)
                self.eld_log.generate_eld_log(
                    output_path=f"outputs/daily_log_{daily_log.date}.pdf",
                    background_image="blank-paper-log.png",
                    daily_data=log_data,
                )

            return Response(build_response(trip), status=status.HTTP_201_CREATED)
        except Exception as e:
            trip.delete()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, pk=None, format=None):
        """
        Retrieve a list of trips, paginated.
        """
        trips = Trip.objects.all()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(trips, request, view=self)
        if page is not None:
            serializer = TripSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create_logs(self, trip):
        trip.create_daily_logs()

    def _calculate_initial_route(self, trip):
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
            "distance": best_route["distance"] / 1609.34,  # Convert meters to miles
            "duration": best_route["duration"] / 3600,  # Convert seconds to hours
        }

    def _calculate_fuel_stops(self, trip, route, initial_route_data):
        """Create Route with optimized fuel stops"""

        coords_list = []
        total_distance_travelled = initial_route_data["distance"]
        total_duration = initial_route_data["duration"]

        previous_location_x, previous_location_y = (
            trip.current_location.x,
            trip.current_location.y,
        )
        coords_list.append((previous_location_x, previous_location_y))

        geometry = initial_route_data["geometry"]
        remaining_distance = initial_route_data["distance"]
        remaining_duration = initial_route_data["duration"]

        # check pickup location
        coords = (
            f"{previous_location_x},{previous_location_y};"
            f"{trip.pickup_location.x},{trip.pickup_location.y}"
        )
        data = self.mapbox_api.get_direction(coords)

        if not data.get("routes"):
            raise Exception("No route found")

        pickup_route = data["routes"][0]
        pickup_distance = pickup_route["distance"] / 1609.34
        pickup_duration = pickup_route["duration"] / 3600

        if remaining_distance > 1000:
            total_distance_travelled = 0
            total_duration = 0
        else:
            # add stops for pickup and dropoff
            coords_list.append((trip.pickup_location.x, trip.pickup_location.y))
            coords_list.append((trip.dropoff_location.x, trip.dropoff_location.y))

            Stop.objects.create(
                route=route,
                stop_type="pickup",
                location=Point(
                    trip.pickup_location.x, trip.pickup_location.y, srid=4326
                ),
                duration=1,  # 30 minutes for fueling
                timestamp=timezone.now() + timedelta(hours=pickup_duration),
            )
            Stop.objects.create(
                route=route,
                stop_type="dropoff",
                location=Point(
                    trip.dropoff_location.x, trip.dropoff_location.y, srid=4326
                ),
                duration=1,
                timestamp=timezone.now() + timedelta(hours=total_duration),
            )
            return total_distance_travelled, total_duration
        general_logger.info(
            f"Initial distance: {remaining_distance}, duration: {remaining_duration}"
        )

        if pickup_distance < 1000:
            coords_list.append((trip.pickup_location.x, trip.pickup_location.y))
            # add stop for pickup
            Stop.objects.create(
                route=route,
                stop_type="pickup",
                location=Point(
                    trip.pickup_location.x, trip.pickup_location.y, srid=4326
                ),
                duration=1,
                timestamp=timezone.now() + timedelta(hours=pickup_duration),
            )

        while remaining_distance > 1000:
            # find optimal fuel station near target distance
            fuel_stop, target_point = self.fuel_stop.find_optimal_fuel_stop(
                geometry, 900
            )

            # first get distance from previous stop to detour
            coords = f"{previous_location_x},{previous_location_y};{target_point.y},{target_point.x}"
            # add detour point
            coords_list.append((target_point.y, target_point.x))
            data = self.mapbox_api.get_direction(coords)

            if not data.get("routes"):
                raise Exception("No route found")

            detour_route = data["routes"][0]
            detour_distance = detour_route["distance"] / 1609.34
            detour_duration = detour_route["duration"] / 3600
            total_distance_travelled += detour_distance
            total_duration += detour_duration

            # get distance, duration from detour target to station
            coords = (
                f"{target_point.y},{target_point.x};"
                f"{fuel_stop['geometry']['coordinates'][0]},"
                f"{fuel_stop['geometry']['coordinates'][1]}"
            )
            # add station point
            coords_list.append(
                (
                    fuel_stop["geometry"]["coordinates"][0],
                    fuel_stop["geometry"]["coordinates"][1],
                )
            )
            data = self.mapbox_api.get_direction(coords)

            if not data.get("routes"):
                raise Exception("No route found")

            gas_route = data["routes"][0]
            gas_distance = gas_route["distance"] / 1609.34
            gas_duration = gas_route["duration"] / 3600
            total_distance_travelled_before_gas = total_distance_travelled
            total_duration_before_gas = total_duration
            total_distance_travelled += gas_distance
            total_duration += gas_duration

            # stop for station
            Stop.objects.create(
                route=route,
                stop_type="fuel",
                location=Point(
                    fuel_stop["geometry"]["coordinates"][0],
                    fuel_stop["geometry"]["coordinates"][1],
                    srid=4326,
                ),
                duration=0.5,  # 30 minutes for fueling
                timestamp=timezone.now() + timedelta(hours=total_duration_before_gas),
            )

            # get distance, duration from station to dropoff
            if total_distance_travelled_before_gas < pickup_distance:
                coords = (
                    f"{fuel_stop['geometry']['coordinates'][0]},"
                    f"{fuel_stop['geometry']['coordinates'][1]};"
                    f"{trip.pickup_location.x},"
                    f"{trip.pickup_location.y};"
                    f"{trip.dropoff_location.x},"
                    f"{trip.dropoff_location.y}"
                )
                # add pickup locatiion only
                if total_distance_travelled + 1000 > pickup_distance:
                    coords_list.append((trip.pickup_location.x, trip.pickup_location.y))
                    # get distance so far to pickup
                    pickup_coords = ";".join(
                        [f"{coord[0]},{coord[1]}" for coord in coords_list]
                    )
                    data = self.mapbox_api.get_direction(pickup_coords)

                    if not data.get("routes"):
                        raise Exception("No route found")

                    temp_pickup_route = data["routes"][0]
                    temp_pickup_duration = temp_pickup_route["duration"] / 3600
                    Stop.objects.create(
                        route=route,
                        stop_type="pickup",
                        location=Point(
                            trip.pickup_location.x, trip.pickup_location.y, srid=4326
                        ),
                        duration=1,
                        timestamp=timezone.now()
                        + timedelta(hours=temp_pickup_duration),
                    )
            else:
                coords = (
                    f"{fuel_stop['geometry']['coordinates'][0]},"
                    f"{fuel_stop['geometry']['coordinates'][1]};"
                    f"{trip.dropoff_location.x},"
                    f"{trip.dropoff_location.y}"
                )
            data = self.mapbox_api.get_direction(coords)

            if not data.get("routes"):
                raise Exception("No route found")

            remaining_route = data["routes"][0]
            geometry = remaining_route["geometry"]
            remaining_distance = remaining_route["distance"] / 1609.34
            remaining_duration = remaining_route["duration"] / 3600

            previous_location_x, previous_location_y = (
                fuel_stop["geometry"]["coordinates"][0],
                fuel_stop["geometry"]["coordinates"][1],
            )

            if remaining_distance < 1000:
                total_distance_travelled += remaining_distance
                total_duration += remaining_duration
                coords_list.append((trip.dropoff_location.x, trip.dropoff_location.y))

                # add dropoff location
                Stop.objects.create(
                    route=route,
                    stop_type="dropoff",
                    location=Point(
                        trip.dropoff_location.x, trip.dropoff_location.y, srid=4326
                    ),
                    duration=1,
                    timestamp=timezone.now() + timedelta(hours=total_duration),
                )
                break

        general_logger.info(
            f"Trip finished: {total_distance_travelled}, {total_duration}"
        )
        general_logger.info(f"coords list: {coords_list}")

        # final trip details
        coords = ";".join([f"{coord[0]},{coord[1]}" for coord in coords_list])

        data = self.mapbox_api.get_direction(coords)
        if not data.get("routes"):
            raise Exception("No route found")

        final_route = data["routes"][0]
        final_geometry = final_route["geometry"]
        final_distance = final_route["distance"] / 1609.34
        final_duration = final_route["duration"] / 3600

        route.geometry = LineString(polyline.decode(final_geometry, 5))
        route.save()
        trip.total_duration = total_duration
        trip.total_distance = total_distance_travelled
        trip.save()

        general_logger.info(f"Final trip details: {final_distance}, {final_duration}")

        return trip, route, total_distance_travelled, total_duration, final_geometry

    def _calculate_rest_stops(self, trip, route):
        """Calculate required rest stops based on HOS rules"""
        # Convert total duration to minutes for precise calculations
        total_driving_minutes = int(trip.total_duration * 60)
        accumulated_driving = 0
        rest_break_count = 0
        mandatory_rest_added = False

        # Calculate 30-minute breaks every 8 hours (480 minutes)
        while accumulated_driving < total_driving_minutes:
            remaining_driving = total_driving_minutes - accumulated_driving
            time_until_break = 480 - (accumulated_driving % 480)

            if time_until_break > remaining_driving:
                break  # No more full breaks needed

            # Add rest break
            accumulated_driving += time_until_break
            rest_break_count += 1

            # Calculate break position in hours
            break_position_hours = accumulated_driving / 60
            fraction = accumulated_driving / total_driving_minutes

            Stop.objects.create(
                route=route,
                stop_type="rest_break",
                location=self._interpolate_point(route.geometry, fraction),
                duration=0.5,
                timestamp=timezone.now() + timedelta(hours=break_position_hours),
            )

            # Check for 70-hour limit violation after each break
            current_cycle_total = trip.current_cycle_hours + (accumulated_driving / 60)
            if not mandatory_rest_added and current_cycle_total >= 70:
                # Add mandatory 34-hour restart
                self._add_mandatory_rest(trip, route, break_position_hours)
                mandatory_rest_added = True

                # Reset accumulated driving time after restart
                accumulated_driving = 0
                trip.current_cycle_hours = 0  # Reset cycle after restart
                trip.save()

                # Continue trip after restart
                continue

            accumulated_driving += 30  # Add break time

        # Check for final mandatory rest
        if not mandatory_rest_added:
            total_cycle = trip.current_cycle_hours + (total_driving_minutes / 60)
            if total_cycle > 70:
                available_driving = (70 - trip.current_cycle_hours) * 60
                if available_driving > 0:
                    fraction = available_driving / total_driving_minutes
                    self._add_mandatory_rest(trip, route, available_driving / 60)

        # Update total duration with break times
        trip.total_duration += rest_break_count * 0.5
        trip.save()

        return trip

    def _add_mandatory_rest(self, trip, route, position_hours):
        """Create mandatory 34-hour restart stop"""
        fraction = position_hours / trip.total_duration
        Stop.objects.create(
            route=route,
            stop_type="mandatory_rest",
            location=self._interpolate_point(route.geometry, fraction),
            duration=34,  # 34-hour restart
            timestamp=trip.created_at + timedelta(hours=position_hours),
        )
        # Adjust total duration to account for rest period
        trip.total_duration += 34
        trip.save()

    def _interpolate_point(self, route_geometry, fraction):
        """Precise point interpolation along route geometry using Shapely's interpolate."""
        line_string = route_geometry
        if fraction < 0 or fraction > 1:
            raise ValueError("Fraction must be between 0 and 1")

        total_length = line_string.length
        target_length = total_length * fraction

        interpolated_point = line_string.interpolate(target_length)

        return Point(interpolated_point.x, interpolated_point.y, srid=4326)

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

            general_logger.info(f"Adding to temp duration: {duration_to_add}")

        # Update the trip's total duration
        general_logger.info(f"Before updating total duration: {trip.total_duration}")
        trip.total_duration += duration_to_add
        general_logger.info(f"Updated trip total duration: {trip.total_duration}")
        trip.save()

        return trip


class TripDetailAPIView(APIView):
    def get(self, request, pk, format=None):
        """
        Return a single Trip by primary key (pk).
        """
        try:
            trip = Trip.objects.filter(pk=pk).first()
            if not trip:
                return Response(
                    {"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND
                )

            return Response(build_response(trip), status=status.HTTP_201_CREATED)

        except Exception as e:
            general_logger.error(f"Error occured: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
