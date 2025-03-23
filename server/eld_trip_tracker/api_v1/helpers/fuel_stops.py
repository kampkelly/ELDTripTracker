from datetime import timedelta

import polyline
from django.contrib.gis.geos import LineString, Point
from django.utils import timezone

from api_v1.helpers.distance import Distance
from api_v1.lib.logger import general_logger
from api_v1.lib.mapbox import MapBoxAPI
from api_v1.models import Stop

SECONDS_IN_HOURS = 3600
METER_TO_MILES_DIVISION = 1609.34


class FuelStop:
    """
    This class provides methods to find optimal fuel stops and add them to a trip route.
    """

    def __init__(self):
        """
        Initializes the FuelStop object with Distance and MapBoxAPI instances.
        """
        self.distance = Distance()
        self.mapbox_api = MapBoxAPI()

    def find_optimal_fuel_stop(self, route_geometry, max_distance):
        """Find best fuel station within search window using Mapbox

        Args:
            route_geometry (LineString): The geometry of the route.
            max_distance (float): The maximum distance to search for a fuel stop.

        Returns:
            tuple: A tuple containing the fuel station data and the target point.
        """
        try:
            # get the ideal target point
            target_point = self.distance.get_point_at_distance(
                route_geometry, max_distance
            )

            data = self.mapbox_api.get_point_of_interest(
                "gas_station", target_point.y, target_point.x
            )

            stations = data.get("features", [])
            if stations:
                return stations[0], target_point
            else:
                general_logger.info("No fuel stations found within the search area.")
                return None, target_point

        except Exception as e:
            general_logger.error(f"Fuel station search failed: {str(e)}")
            raise e

    def add_fuel_stops(self, trip, route, initial_route_data):
        """create Route with optimized fuel stops

        Args:
            trip (Trip): The trip object.
            route (Route): The route object.
            initial_route_data (dict): Initial route data containing distance, duration, and geometry.

        Returns:
            tuple: A tuple containing the updated trip, route, total distance travelled, total duration, and geometry.
        """
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
        pickup_distance = pickup_route["distance"] / METER_TO_MILES_DIVISION
        pickup_duration = pickup_route["duration"] / SECONDS_IN_HOURS

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
            trip.total_duration = total_duration
            trip.total_distance = total_distance_travelled
            trip.save()
            general_logger.info(
                "Trip completed without fuel stops as initial distance was short."
            )
            return trip, route, total_distance_travelled, total_duration, geometry

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
            general_logger.info("Added pickup stop as it was within 1000 miles.")

        while remaining_distance > 1000:
            # find optimal fuel station near target distance
            fuel_stop, target_point = self.find_optimal_fuel_stop(geometry, 900)
            
            if not fuel_stop:
                return trip, route, total_distance_travelled, total_duration, geometry

            # first get distance from previous stop to detour
            coords = (
                f"{previous_location_x},{previous_location_y};"
                f"{target_point.y},{target_point.x}"
            )
            # add detour point
            coords_list.append((target_point.y, target_point.x))
            data = self.mapbox_api.get_direction(coords)

            if not data.get("routes"):
                raise Exception("No route found")

            detour_route = data["routes"][0]
            detour_distance = detour_route["distance"] / METER_TO_MILES_DIVISION
            detour_duration = detour_route["duration"] / SECONDS_IN_HOURS
            total_distance_travelled += detour_distance
            total_duration += detour_duration
            general_logger.info(
                f"Detour: distance={detour_distance}, duration={detour_duration}, "
                f"total_distance={total_distance_travelled}, total_duration={total_duration}"
            )

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
            gas_distance = gas_route["distance"] / METER_TO_MILES_DIVISION
            gas_duration = gas_route["duration"] / SECONDS_IN_HOURS
            total_distance_travelled_before_gas = total_distance_travelled
            total_duration_before_gas = total_duration
            total_distance_travelled += gas_distance
            total_duration += gas_duration
            general_logger.info(
                f"Gas stop: distance={gas_distance}, duration={gas_duration}, "
                f"total_distance={total_distance_travelled}, total_duration={total_duration}"
            )

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
            general_logger.info("Added fuel stop.")

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
                    temp_pickup_duration = (
                        temp_pickup_route["duration"] / SECONDS_IN_HOURS
                    )
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
                    general_logger.info("Added pickup stop after fuel stop.")
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
            remaining_distance = remaining_route["distance"] / METER_TO_MILES_DIVISION
            remaining_duration = remaining_route["duration"] / SECONDS_IN_HOURS

            previous_location_x, previous_location_y = (
                fuel_stop["geometry"]["coordinates"][0],
                fuel_stop["geometry"]["coordinates"][1],
            )
            general_logger.info(
                f"Remaining distance: {remaining_distance}, remaining duration: {remaining_duration}"
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
                general_logger.info("Added dropoff stop.")
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
        final_distance = final_route["distance"] / METER_TO_MILES_DIVISION
        final_duration = final_route["duration"] / SECONDS_IN_HOURS

        route.geometry = LineString(polyline.decode(final_geometry, 5))
        route.save()
        trip.total_duration = total_duration
        trip.total_distance = total_distance_travelled
        trip.save()

        general_logger.info(
            "Final trip details: "
            f"{final_distance}, {final_duration}, ----, {total_duration}"
        )

        return trip, route, total_distance_travelled, total_duration, final_geometry
