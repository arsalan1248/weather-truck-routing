import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache

from .geo import interpolate, thin_out
from .recommendation import RouteSummary, explain_choice, rank_routes
from .risk import Risk, assess_weather
from .routing import fetch_route_options
from .weather import fetch_forecasts

ROUTE_IDS = 'ABC'


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    point: tuple  # (lat, lon)
    eta: object  # datetime
    covers_miles: float  # half the gap to each neighbour, so a route's checkpoints add up to its length


def place_checkpoints(route, interval_miles, departure):
    """A checkpoint every `interval_miles`, plus one at the destination."""
    total = route.distance_miles
    marks = [float(m) for m in range(0, int(total), interval_miles)] + [total]

    checkpoints = []
    for i, mile in enumerate(marks):
        before = mile - marks[i - 1] if i > 0 else 0
        after = marks[i + 1] - mile if i < len(marks) - 1 else 0
        seconds = interpolate(mile, route.miles, route.seconds)
        checkpoints.append(Checkpoint(
            mile=mile,
            point=interpolate(mile, route.miles, route.points),
            eta=departure + timedelta(seconds=round(seconds)),
            covers_miles=(before + after) / 2,
        ))
    return checkpoints


def plan_trip(origin, destination, departure, load_lb, interval_miles):
    routes = fetch_route_options(origin['point'], destination['point'], count=settings.ROUTE_OPTIONS)
    checkpoints_per_route = [place_checkpoints(route, interval_miles, departure) for route in routes]

    # One batched weather request covers every checkpoint on every route.
    all_checkpoints = [cp for checkpoints in checkpoints_per_route for cp in checkpoints]
    latest_eta = max(cp.eta for cp in all_checkpoints)
    forecasts = iter(fetch_forecasts([cp.point for cp in all_checkpoints], departure, latest_eta))

    route_results = {}
    summaries = []
    for route_id, route, checkpoints in zip(ROUTE_IDS, routes, checkpoints_per_route):
        assessed = [_assess_checkpoint(cp, next(forecasts), load_lb) for cp in checkpoints]
        summary = _summarise(route_id, route, assessed)
        route_results[route_id] = _route_result(route_id, route, departure, assessed, summary)
        summaries.append(summary)

    ranked = rank_routes(summaries)
    for position, summary in enumerate(ranked, start=1):
        route_results[summary.route_id]['rank'] = position
        route_results[summary.route_id]['is_recommended'] = position == 1

    trip_id = uuid.uuid4().hex
    cache.set(f'trip:{trip_id}', {
        'departure': departure,
        'load_lb': load_lb,
        'route_samples': [thin_out(route.points, route.miles, every_miles=5) for route in routes],
    }, settings.TRIP_CACHE_SECONDS)

    return {
        'trip_id': trip_id,
        'origin': origin['name'],
        'destination': destination['name'],
        'departure_time': departure,
        'load_weight_lb': load_lb,
        'checkpoint_interval_miles': interval_miles,
        'recommended_route_id': ranked[0].route_id,
        'recommendation_reason': explain_choice(ranked),
        'routes': sorted(route_results.values(), key=lambda r: r['rank']),
    }


def _assess_checkpoint(checkpoint, forecast, load_lb):
    wind, rain, snow = forecast.at(checkpoint.eta)
    assessment = assess_weather(wind, rain, snow, load_lb)
    return checkpoint, assessment, (wind, rain, snow)


def summarise_risk(route_id, distance_miles, duration_seconds, levels_and_miles):
    """Totals per risk level, where each checkpoint counts for the miles it covers."""
    miles_at = {level: 0.0 for level in Risk}
    for level, miles in levels_and_miles:
        miles_at[level] += miles

    average_risk = sum(level * miles for level, miles in miles_at.items()) / distance_miles if distance_miles else 0.0
    return RouteSummary(
        route_id=route_id,
        severe_miles=miles_at[Risk.SEVERE],
        high_miles=miles_at[Risk.HIGH],
        no_travel_miles=miles_at[Risk.NO_TRAVEL],
        average_risk=average_risk,
        duration_seconds=duration_seconds,
    )


def _summarise(route_id, route, assessed):
    levels_and_miles = [(assessment.level, checkpoint.covers_miles) for checkpoint, assessment, _ in assessed]
    return summarise_risk(route_id, route.distance_miles, route.duration_seconds, levels_and_miles)


def _route_result(route_id, route, departure, assessed, summary):
    return {
        'id': route_id,
        'name': f'Route {route_id}',
        'distance_miles': round(route.distance_miles, 1),
        'duration_minutes': round(route.duration_seconds / 60),
        'arrival_time': departure + timedelta(seconds=round(route.duration_seconds)),
        'summary': {
            'severe_miles': round(summary.severe_miles, 1),
            'high_miles': round(summary.high_miles, 1),
            'no_travel_miles': round(summary.no_travel_miles, 1),
            'average_risk': round(summary.average_risk, 2),
            'worst_risk': max(a.level for _, a, _ in assessed).label,
        },
        'geometry': [[round(lon, 5), round(lat, 5)] for lat, lon in thin_out(route.points, route.miles, 0.5)],
        'checkpoints': [
            {
                'mile': round(checkpoint.mile, 1),
                'lat': round(checkpoint.point[0], 5),
                'lon': round(checkpoint.point[1], 5),
                'eta': checkpoint.eta,
                'wind_mph': round(wind, 1),
                'rain_in_per_hr': round(rain, 2),
                'snow_in_per_hr': round(snow, 2),
                'risk': assessment.level.label,
                'risk_level': int(assessment.level),
                'reasons': assessment.reasons,
            }
            for checkpoint, assessment, (wind, rain, snow) in assessed
        ],
    }
