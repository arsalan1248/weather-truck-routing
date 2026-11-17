from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TripRequestSerializer
from .services.heatmap import build_heatmap
from .services.planner import plan_trip
from .services.routing import RoutingError
from .services.weather import WeatherError


def service_unavailable(exc):
    return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class HealthView(APIView):
    """The frontend calls this on load to wake the server up on free hosting."""

    def get(self, request):
        return Response({'status': 'ok'})


class TripCreateView(APIView):
    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            trip = plan_trip(
                origin=data['origin'],
                destination=data['destination'],
                departure=data['departure_time'],
                load_lb=data['load_weight_lb'],
                interval_miles=data['checkpoint_interval_miles'],
            )
        except (RoutingError, WeatherError) as exc:
            return service_unavailable(exc)

        return Response(trip, status=status.HTTP_201_CREATED)


class TripHeatmapView(APIView):
    def get(self, request, trip_id):
        trip = cache.get(f'trip:{trip_id}')
        if trip is None:
            return Response({'detail': 'Trip not found or expired. Plan it again.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            return Response(build_heatmap(trip))
        except WeatherError as exc:
            return service_unavailable(exc)
