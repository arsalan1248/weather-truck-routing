import math
from datetime import timedelta

from django.conf import settings

from .geo import quick_distance_miles
from .risk import risk_score
from .weather import fetch_forecasts, hour_floor

CORRIDOR_WIDTH_MILES = 60
MAX_POINTS = 250
MILES_PER_DEGREE = 69.0


def corridor_points(route_samples, width_miles=CORRIDOR_WIDTH_MILES, max_points=MAX_POINTS):
    """
    A regular grid of points covering the area within `width_miles` of any route.

    Spacing grows until the grid fits in `max_points`, which keeps the weather
    request small. Points snap to one shared grid so overlapping routes don't
    add duplicates. Returns the points and the spacing in miles.
    """
    samples = [p for route in route_samples for p in route]
    mean_lat = sum(lat for lat, _ in samples) / len(samples)
    lon_scale = math.cos(math.radians(mean_lat))

    spacing = 10.0
    while True:
        lat_step = spacing / MILES_PER_DEGREE
        lon_step = spacing / (MILES_PER_DEGREE * lon_scale)
        reach = math.ceil(width_miles / spacing)

        cells = set()
        for lat, lon in samples:
            row, col = round(lat / lat_step), round(lon / lon_step)
            for r in range(row - reach, row + reach + 1):
                for c in range(col - reach, col + reach + 1):
                    if (r, c) not in cells and quick_distance_miles((lat, lon), (r * lat_step, c * lon_step)) <= width_miles:
                        cells.add((r, c))

        if len(cells) <= max_points:
            return [(r * lat_step, c * lon_step) for r, c in sorted(cells)], spacing
        spacing *= 1.25


def build_heatmap(route_samples, departure, load_lb):
    """Risk scores for every grid point, for every hour from departure to HEATMAP_HOURS later."""
    points, spacing_miles = corridor_points(route_samples)
    start = hour_floor(departure)
    hours = settings.HEATMAP_HOURS
    forecasts = fetch_forecasts(points, start, start + timedelta(hours=hours))

    scores = []
    for hour in range(hours + 1):
        moment = start + timedelta(hours=hour)
        scores.append([round(risk_score(*forecast.at(moment), load_lb), 2) for forecast in forecasts])

    return {
        'start_time': start,
        'hours': hours,
        'spacing_miles': round(spacing_miles, 1),
        'points': [[round(lon, 4), round(lat, 4)] for lat, lon in points],
        'scores': scores,
    }
