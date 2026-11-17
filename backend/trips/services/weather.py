import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings
from django.core.cache import cache

# Open-Meteo accepts many locations per request, but very long URLs get rejected.
LOCATIONS_PER_REQUEST = 100


class WeatherError(Exception):
    pass


@dataclass(frozen=True)
class Forecast:
    """Hourly forecast for one location. Rain and snow are totals for the hour, so they read as in/hr."""

    start: datetime  # time of the first hour, UTC
    wind_mph: list
    rain_in: list
    snow_in: list

    def at(self, moment):
        """Values for the hour closest to `moment`."""
        hour = round((moment - self.start).total_seconds() / 3600)
        hour = min(max(hour, 0), len(self.wind_mph) - 1)
        return self.wind_mph[hour], self.rain_in[hour], self.snow_in[hour]


def hour_floor(moment):
    return moment.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def fetch_forecasts(points, start, end):
    """Hourly forecasts from `start` to `end` for each (lat, lon), in the same order as `points`."""
    start, end = hour_floor(start), hour_floor(end) + timedelta(hours=1)
    batches = [points[i:i + LOCATIONS_PER_REQUEST] for i in range(0, len(points), LOCATIONS_PER_REQUEST)]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = pool.map(lambda batch: _fetch_batch(batch, start, end), batches)
        return [forecast for batch_result in results for forecast in batch_result]


def _fetch_batch(points, start, end):
    params = {
        'latitude': ','.join(f'{lat:.3f}' for lat, _ in points),
        'longitude': ','.join(f'{lon:.3f}' for _, lon in points),
        'hourly': 'wind_speed_10m,rain,snowfall',
        'wind_speed_unit': 'mph',
        'precipitation_unit': 'inch',
        'timezone': 'GMT',
        'start_hour': start.strftime('%Y-%m-%dT%H:%M'),
        'end_hour': end.strftime('%Y-%m-%dT%H:%M'),
    }
    cache_key = 'forecast:' + hashlib.sha1(repr(sorted(params.items())).encode()).hexdigest()
    data = cache.get(cache_key)

    if data is None:
        try:
            response = requests.get(settings.OPEN_METEO_URL, params=params, timeout=settings.HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise WeatherError('The weather service is unavailable, please try again shortly.') from exc
        cache.set(cache_key, data, settings.FORECAST_CACHE_SECONDS)

    # A single location comes back as an object, several as a list.
    locations = data if isinstance(data, list) else [data]
    return [_to_forecast(location['hourly']) for location in locations]


def _to_forecast(hourly):
    def values(name):
        return [value or 0.0 for value in hourly[name]]  # missing hours come back as null

    return Forecast(
        start=datetime.fromisoformat(hourly['time'][0]).replace(tzinfo=timezone.utc),
        wind_mph=values('wind_speed_10m'),
        rain_in=values('rain'),
        snow_in=values('snowfall'),
    )
