import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests
from django.conf import settings

from .geo import cumulative, haversine_miles, quick_distance_miles, thin_out

METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    pass


@dataclass(frozen=True)
class RouteOption:
    points: list  # (lat, lon) from origin to destination
    miles: list  # distance from the origin at each point
    seconds: list  # driving time from the origin at each point

    @property
    def distance_miles(self):
        return self.miles[-1]

    @property
    def duration_seconds(self):
        return self.seconds[-1]


def fetch_route_options(origin, destination, count):
    """
    Up to `count` different routes between two (lat, lon) points.

    OSRM often returns only one or two alternatives, so the rest come from
    forcing the route through a point off to one side of the straight line.
    """
    near_detours, wide_detours = _detour_points(origin, destination)

    # Each OSRM request takes a second or so, so the first detours are requested
    # alongside the main route instead of waiting to see if they're needed.
    with ThreadPoolExecutor(max_workers=3) as pool:
        main = pool.submit(_request_routes, [origin, destination], True)
        detours = [pool.submit(_try_route, [origin, via, destination]) for via in near_detours]
        routes = main.result()
        _add_distinct_routes(routes, [job.result() for job in detours], count)

    if len(routes) < count:
        with ThreadPoolExecutor(max_workers=2) as pool:
            detours = pool.map(lambda via: _try_route([origin, via, destination]), wide_detours)
            _add_distinct_routes(routes, list(detours), count)

    return routes[:count]


def _add_distinct_routes(routes, candidates, count):
    for candidate in candidates:
        if len(routes) >= count:
            return
        # A detour that adds more than half the distance isn't a sensible option.
        if candidate is None or candidate.distance_miles > routes[0].distance_miles * 1.5:
            continue
        if not any(_mostly_overlaps(candidate, existing) for existing in routes):
            routes.append(candidate)


def _try_route(waypoints):
    try:
        return _request_routes(waypoints)[0]
    except RoutingError:
        return None


def _request_routes(waypoints, alternatives=False):
    coords = ';'.join(f'{lon},{lat}' for lat, lon in waypoints)
    params = {
        'overview': 'full',
        'geometries': 'geojson',
        'annotations': 'duration',
        'alternatives': 'true' if alternatives else 'false',
    }
    try:
        response = requests.get(
            f'{settings.OSRM_BASE_URL}/route/v1/driving/{coords}',
            params=params,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RoutingError('The routing service is unavailable, please try again shortly.') from exc

    if data.get('code') != 'Ok' or not data.get('routes'):
        raise RoutingError('No driving route found between these places.')
    return [_to_route_option(route) for route in data['routes']]


def _to_route_option(route):
    points = [(lat, lon) for lon, lat in route['geometry']['coordinates']]
    segment_miles = [haversine_miles(a, b) for a, b in zip(points, points[1:])]

    segment_seconds = [s for leg in route['legs'] for s in leg['annotation']['duration']]
    if len(segment_seconds) != len(segment_miles):
        # Shouldn't happen, but fall back to spreading the total time evenly by distance.
        total = sum(segment_miles) or 1
        segment_seconds = [route['duration'] * m / total for m in segment_miles]

    # OSRM times are for cars. Trucks can't go faster than the speed cap.
    min_seconds_per_mile = 3600 / settings.TRUCK_MAX_SPEED_MPH
    segment_seconds = [max(s, m * min_seconds_per_mile) for s, m in zip(segment_seconds, segment_miles)]

    return RouteOption(points=points, miles=cumulative(segment_miles), seconds=cumulative(segment_seconds))


def _detour_points(origin, destination):
    """
    Points to the left and right of the midpoint of the straight line.

    Returns two pairs: offsets of a quarter of the trip length, then half.
    """
    mid_lat = (origin[0] + destination[0]) / 2
    mid_lon = (origin[1] + destination[1]) / 2
    scale = math.cos(math.radians(mid_lat))

    # Work in a flat grid where one unit is about the same distance both ways.
    dx = (destination[1] - origin[1]) * scale
    dy = destination[0] - origin[0]
    length = math.hypot(dx, dy) or 1
    perp_x, perp_y = -dy / length, dx / length

    def offset_point(share):
        offset = share * length
        return (mid_lat + perp_y * offset, mid_lon + perp_x * offset / scale)

    return [offset_point(0.25), offset_point(-0.25)], [offset_point(0.5), offset_point(-0.5)]


def _mostly_overlaps(route, other, tolerance_miles=2.0, threshold=0.8):
    sample = thin_out(route.points, route.miles, every_miles=10)
    reference = thin_out(other.points, other.miles, every_miles=1)
    shared = sum(1 for p in sample if any(quick_distance_miles(p, q) <= tolerance_miles for q in reference))
    return shared / len(sample) >= threshold
