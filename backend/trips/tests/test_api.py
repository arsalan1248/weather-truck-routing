from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from trips.services.routing import RouteOption, RoutingError
from trips.services.weather import Forecast, hour_floor

# Two 100-mile routes; B is slower.
ROUTE_A = RouteOption(
    points=[(30 + i / 69, -97.0) for i in range(101)],
    miles=[float(i) for i in range(101)],
    seconds=[i * 60.0 for i in range(101)],
)
ROUTE_B = RouteOption(
    points=[(30 + i / 69, -97.5) for i in range(101)],
    miles=[float(i) for i in range(101)],
    seconds=[i * 75.0 for i in range(101)],
)


def calm_forecasts(points, start, end):
    hours = int((end - start).total_seconds() // 3600) + 2
    return [Forecast(hour_floor(start), [5.0] * hours, [0.0] * hours, [0.0] * hours) for _ in points]


def stormy_on_route_a(points, start, end):
    """50 mph wind wherever the longitude is -97 (route A), calm elsewhere."""
    hours = int((end - start).total_seconds() // 3600) + 2
    return [
        Forecast(hour_floor(start), [50.0 if lon == -97.0 else 5.0] * hours, [0.0] * hours, [0.0] * hours)
        for _, lon in points
    ]


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
@patch('trips.services.planner.fetch_route_options', return_value=[ROUTE_A, ROUTE_B])
class TripApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.payload = {
            'origin': {'name': 'Southtown', 'lat': 30.0, 'lon': -97.0},
            'destination': {'name': 'Northtown', 'lat': 31.45, 'lon': -97.0},
            'departure_time': (timezone.now() + timedelta(hours=2)).isoformat(),
            'load_weight_lb': 35_000,
            'checkpoint_interval_miles': 25,
        }

    def post(self):
        return self.client.post('/api/trips/', self.payload, content_type='application/json')

    @patch('trips.services.planner.fetch_forecasts', side_effect=calm_forecasts)
    def test_calm_weather_recommends_the_fastest_route(self, _forecasts, _routes):
        response = self.post()

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['recommended_route_id'], 'A')
        self.assertEqual(len(data['routes']), 2)
        self.assertEqual(len(data['routes'][0]['checkpoints']), 5)  # miles 0, 25, 50, 75, 100

    @patch('trips.services.planner.fetch_forecasts', side_effect=stormy_on_route_a)
    def test_avoids_the_route_with_dangerous_wind(self, _forecasts, _routes):
        data = self.post().json()

        self.assertEqual(data['recommended_route_id'], 'B')
        route_a = next(r for r in data['routes'] if r['id'] == 'A')
        # 50 mph is Severe, and with a 35,000 lb load it becomes No Travel.
        self.assertEqual(route_a['summary']['worst_risk'], 'No Travel')
        self.assertEqual(route_a['checkpoints'][0]['risk'], 'No Travel')

    def test_rejects_an_unsupported_interval(self, _routes):
        self.payload['checkpoint_interval_miles'] = 30

        response = self.post()

        self.assertEqual(response.status_code, 400)
        self.assertIn('checkpoint_interval_miles', response.json())

    def test_rejects_a_departure_in_the_past(self, _routes):
        self.payload['departure_time'] = (timezone.now() - timedelta(days=1)).isoformat()

        response = self.post()

        self.assertEqual(response.status_code, 400)
        self.assertIn('departure_time', response.json())

    def test_routing_failure_is_a_502(self, mock_routes):
        mock_routes.side_effect = RoutingError('The routing service is unavailable, please try again shortly.')

        self.assertEqual(self.post().status_code, 502)

    @patch('trips.services.heatmap.fetch_forecasts', side_effect=calm_forecasts)
    @patch('trips.services.planner.fetch_forecasts', side_effect=calm_forecasts)
    def test_heatmap_has_a_score_per_point_per_hour(self, _planner_forecasts, _heatmap_forecasts, _routes):
        trip_id = self.post().json()['trip_id']

        response = self.client.get(f'/api/trips/{trip_id}/heatmap/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['scores']), 49)
        self.assertTrue(all(len(hour) == len(data['points']) for hour in data['scores']))

    def test_unknown_trip_heatmap_is_a_404(self, _routes):
        self.assertEqual(self.client.get('/api/trips/nope/heatmap/').status_code, 404)
