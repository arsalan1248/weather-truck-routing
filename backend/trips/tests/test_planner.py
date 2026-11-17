from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from trips.services.planner import place_checkpoints, summarise_risk
from trips.services.risk import Risk
from trips.services.routing import RouteOption

DEPARTURE = datetime(2026, 11, 20, 6, 0, tzinfo=timezone.utc)

# 60 miles due north at a steady 60 mph.
STRAIGHT_ROUTE = RouteOption(
    points=[(30 + i / 69, -97.0) for i in range(61)],
    miles=[float(i) for i in range(61)],
    seconds=[i * 60.0 for i in range(61)],
)


class PlaceCheckpointsTests(SimpleTestCase):
    def test_every_interval_plus_the_destination(self):
        checkpoints = place_checkpoints(STRAIGHT_ROUTE, 25, DEPARTURE)
        self.assertEqual([c.mile for c in checkpoints], [0, 25, 50, 60])

    def test_eta_uses_driving_time_to_each_checkpoint(self):
        checkpoints = place_checkpoints(STRAIGHT_ROUTE, 25, DEPARTURE)
        self.assertEqual(checkpoints[1].eta, DEPARTURE + timedelta(minutes=25))
        self.assertEqual(checkpoints[-1].eta, DEPARTURE + timedelta(hours=1))

    def test_covered_miles_add_up_to_the_route(self):
        checkpoints = place_checkpoints(STRAIGHT_ROUTE, 10, DEPARTURE)
        self.assertAlmostEqual(sum(c.covers_miles for c in checkpoints), 60)

    def test_checkpoint_is_placed_along_the_line(self):
        checkpoint = place_checkpoints(STRAIGHT_ROUTE, 25, DEPARTURE)[1]
        self.assertAlmostEqual(checkpoint.point[0], 30 + 25 / 69)


class SummariseRiskTests(SimpleTestCase):
    def test_miles_per_level_and_average(self):
        summary = summarise_risk('A', 100, 3600, [(Risk.LOW, 50), (Risk.HIGH, 30), (Risk.SEVERE, 20)])

        self.assertEqual(summary.high_miles, 30)
        self.assertEqual(summary.severe_miles, 20)
        self.assertEqual(summary.no_travel_miles, 0)
        self.assertAlmostEqual(summary.average_risk, (2 * 30 + 3 * 20) / 100)
