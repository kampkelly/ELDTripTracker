from api_v1.helpers.distance import Distance
from api_v1.helpers.fuel_stops import FuelStop
from api_v1.lib.logger import general_logger
from api_v1.lib.mapbox import MapBoxAPI
from api_v1.models import Trip
from api_v1.serializers import TripSerializer
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

    def post(self, request):
        # Validate and create trip
        serializer = TripSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        trip = serializer.save()

        try:
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

    def _build_response(self, trip):
        """
        Construct a response containing trip data.
        """
        return {
            "trip": TripSerializer(trip).data,
        }


class TripDetailAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.distance = Distance()
        self.fuel_stop = FuelStop()
        self.mapbox_api = MapBoxAPI()

    def get(self, request, pk, format=None):
        """
        Return a single SKU by primary key (pk).
        """
        trip = Trip.objects.filter(pk=pk).first()
        if not trip:
            return Response(
                {"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # move this to post endpoint
        try:
            # Calculate route using Mapbox Directions API
            route_data = self._calculate_initial_route(trip)
            self._calculate_fuel_stops(trip, route_data)

            return Response(build_response(trip), status=status.HTTP_201_CREATED)

        except Exception as e:
            general_logger.error(f"Error occured: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

    def _calculate_fuel_stops(self, trip, initial_route_data):
        """Create Route with optimized fuel stops"""

        total_distance_travelled = initial_route_data["distance"]
        total_duration = initial_route_data["duration"]

        previous_location_x, previous_location_y = (
            trip.current_location.x,
            trip.current_location.y,
        )

        geometry = initial_route_data["geometry"]
        remaining_distance = initial_route_data["distance"]
        remaining_duration = initial_route_data["duration"]
        if remaining_distance > 1000:
            total_distance_travelled = 0
            total_duration = 0
        general_logger.info(
            f"Initial distance: {remaining_distance}, duration: {remaining_duration}"
        )

        # check pickup location
        coords = (
            f"{trip.current_location.x},{trip.current_location.y};"
            f"{trip.pickup_location.x},{trip.pickup_location.y}"
        )
        data = self.mapbox_api.get_direction(coords)

        if not data.get("routes"):
            raise Exception("No route found")

        pickup_route = data["routes"][0]
        pickup_distance = pickup_route["distance"] / 1609.34

        while remaining_distance > 1000:
            # find optimal fuel station near target distance
            fuel_stop, target_point = self.fuel_stop.find_optimal_fuel_stop(
                geometry, 900
            )

            # first get distance from previous stop to detour
            coords = f"{previous_location_x},{previous_location_y};{target_point.y},{target_point.x}"
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
            data = self.mapbox_api.get_direction(coords)

            if not data.get("routes"):
                raise Exception("No route found")

            gas_route = data["routes"][0]
            gas_distance = gas_route["distance"] / 1609.34
            gas_duration = gas_route["duration"] / 3600
            total_distance_travelled += gas_distance
            total_duration += gas_duration

            # get distance, duration from station to dropoff
            if total_distance_travelled < pickup_distance:
                coords = (
                    f"{fuel_stop['geometry']['coordinates'][0]},"
                    f"{fuel_stop['geometry']['coordinates'][1]};"
                    f"{trip.pickup_location.x},"
                    f"{trip.pickup_location.y};"
                    f"{trip.dropoff_location.x},"
                    f"{trip.dropoff_location.y}"
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
                break

        general_logger.info(
            f"Trip finished: {total_distance_travelled}, {total_duration}"
        )
        return total_distance_travelled, total_duration
