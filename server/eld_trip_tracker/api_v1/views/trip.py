import json

import polyline
from api_v1.helpers.distance import Distance
from api_v1.helpers.eld_logs import ELDLog
from api_v1.helpers.fuel_stops import FuelStop
from api_v1.helpers.trip_calculator import TripCalculator
from api_v1.lib.llm import SUMMARY_RESPONSE_TEMPLATE, get_llm
from api_v1.lib.logger import general_logger
from api_v1.lib.mapbox import MapBoxAPI
from api_v1.models import DailyLog, DutyStatus, Route, Stop, Trip
from api_v1.serializers import TripSerializer
from django.contrib.gis.geos import LineString
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


def get_stops(trip, stops):
    stops_data = [
        {
            "coordinates": [trip.current_location.x, trip.current_location.y],
            "timestamp": trip.created_at,
            "duration": 0,
            "stop_type": "current location",
        }
    ]

    for stop in stops:
        stops_data.append(
            {
                "coordinates": [stop.location.x, stop.location.y],
                "timestamp": stop.timestamp,
                "duration": stop.duration,
                "stop_type": stop.stop_type.replace("_", " "),
            }
        )

    return stops_data


def build_frontend_response(trip, stops, eld_logs):
    """
    Construct a response containing trip data.
    """
    stops_data = get_stops(trip, stops)
    stops_duration = sum(stop["duration"] for stop in stops_data)
    return {
        "id": trip.id,
        "total_distance": trip.total_distance,
        "total_duration": trip.total_duration,
        "driving_duration": trip.total_duration - stops_duration,
        "stops": stops_data,
        "eld_logs": eld_logs,
        "hos": {},
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
        self.eld_log = ELDLog()
        self.trip_calculator = TripCalculator()

    def post(self, request):
        try:
            serializer = TripSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            trip = serializer.save()

            route_data = self.trip_calculator.calculate_initial_route(trip)
            created_route = Route.objects.create(
                trip=trip,
                geometry=LineString(polyline.decode(route_data["geometry"], 5)),
            )
            trip, route, _, _, _ = self.trip_calculator.calculate_fuel_stops(
                trip, created_route, route_data
            )
            trip = self.trip_calculator.calculate_rest_stops(trip, route)
            trip = self.trip_calculator.update_durations_from_stops(trip)

            trip.create_daily_logs()

            daily_logs = trip.daily_logs.all().order_by("date")

            eld_logs = self.eld_log.generate_eld_logs(trip, daily_logs)

            stops = Stop.objects.filter(route__trip=trip).order_by("timestamp")
            response = build_frontend_response(trip, stops, eld_logs)

            return Response(response, status=status.HTTP_201_CREATED)
        except Exception as e:
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


class TripDetailAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.distance = Distance()
        self.fuel_stop = FuelStop()
        self.mapbox_api = MapBoxAPI()
        self.eld_log = ELDLog()
        self.trip_calculator = TripCalculator()

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

            daily_logs = trip.daily_logs.all().order_by("date")

            eld_logs = self.eld_log.generate_eld_logs(trip, daily_logs)

            stops = Stop.objects.filter(route__trip=trip).order_by("timestamp")
            response = build_frontend_response(trip, stops, eld_logs)

            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            general_logger.error(f"Error occured: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, pk, format=None):
        trip = Trip.objects.filter(pk=pk).first()
        if not trip:
            return Response(
                {"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND
            )
        llm = get_llm()

        formatted_data = json.dumps(request.data)
        prompt = SUMMARY_RESPONSE_TEMPLATE.format(
            data=formatted_data,
            start_location=trip.current_location_name,
            end_location=trip.dropoff_location_name,
            start_time=trip.created_at,
        )
        general_logger.info(f"Calling llm with data: {formatted_data}")
        llm_response = str(llm.complete(prompt))

        general_logger.info(f"LLM response: {llm_response}")
        response = {"summary": llm_response}

        return Response(response, status=status.HTTP_200_OK)
