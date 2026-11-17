from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TripRequestSerializer
from .services.planner import plan_trip
from .services.routing import RoutingError
from .services.weather import WeatherError


class HealthView(APIView):
    """The frontend calls this on load, so a cold server is already starting by the time a trip is planned."""

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
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(trip, status=status.HTTP_201_CREATED)
