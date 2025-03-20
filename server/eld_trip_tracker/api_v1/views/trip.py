from api_v1.models import Trip
from api_v1.serializers import TripSerializer
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView


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
            return Response(self._build_response(trip), status=status.HTTP_201_CREATED)
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
