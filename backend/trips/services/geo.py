import math
from bisect import bisect_left

EARTH_RADIUS_MILES = 3958.8


def haversine_miles(a, b):
    """Distance between two (lat, lon) points in miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def quick_distance_miles(a, b):
    """Flat-earth approximation. Plenty accurate for 'is this within a few miles' checks, and much faster."""
    mean_lat = math.radians((a[0] + b[0]) / 2)
    dx = (b[1] - a[1]) * math.cos(mean_lat) * 69.17
    dy = (b[0] - a[0]) * 69.17
    return math.hypot(dx, dy)


def cumulative(values):
    totals = [0.0]
    for value in values:
        totals.append(totals[-1] + value)
    return totals


def interpolate(position, positions, values):
    """Linear interpolation of `values` at `position`, where `positions` is sorted (e.g. mile markers)."""
    if position <= positions[0]:
        return values[0]
    if position >= positions[-1]:
        return values[-1]
    i = bisect_left(positions, position)
    start, end = positions[i - 1], positions[i]
    fraction = (position - start) / (end - start) if end > start else 0.0
    before, after = values[i - 1], values[i]
    if isinstance(before, tuple):
        return tuple(b + (a - b) * fraction for b, a in zip(before, after))
    return before + (after - before) * fraction


def thin_out(points, miles, every_miles):
    """Keep roughly one point per `every_miles`, always keeping the first and last."""
    kept = [points[0]]
    next_mark = every_miles
    for point, mile in zip(points[1:-1], miles[1:-1]):
        if mile >= next_mark:
            kept.append(point)
            next_mark = mile + every_miles
    kept.append(points[-1])
    return kept
