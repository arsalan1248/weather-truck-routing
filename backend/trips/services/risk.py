from dataclasses import dataclass
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self):
        return self.name.replace('_', ' ').title()


# Where a value sits on two rows of the table (e.g. 0.25 in/hr of rain), it
# gets the higher level. Values marked ">" in the table are strict.

def wind_risk(mph):
    if mph >= 55:
        return Risk.NO_TRAVEL
    if mph >= 45:
        return Risk.SEVERE
    if mph >= 35:
        return Risk.HIGH
    if mph >= 25:
        return Risk.MODERATE
    return Risk.LOW


def rain_risk(inches_per_hour):
    if inches_per_hour > 1.0:
        return Risk.NO_TRAVEL
    if inches_per_hour >= 0.5:
        return Risk.SEVERE
    if inches_per_hour >= 0.25:
        return Risk.HIGH
    if inches_per_hour >= 0.1:
        return Risk.MODERATE
    return Risk.LOW


def snow_risk(inches_per_hour):
    if inches_per_hour > 3.0:
        return Risk.NO_TRAVEL
    if inches_per_hour >= 2.0:
        return Risk.SEVERE
    if inches_per_hour >= 1.0:
        return Risk.HIGH
    if inches_per_hour >= 0.5:
        return Risk.MODERATE
    return Risk.LOW


def apply_load_rules(wind_level, load_lb):
    """Heavier loads make strong wind more dangerous. Wind of 55+ mph is already No Travel."""
    if wind_level == Risk.SEVERE and load_lb > 30_000:
        return Risk.NO_TRAVEL
    if wind_level == Risk.HIGH and load_lb > 40_000:
        return Risk.SEVERE
    return wind_level


@dataclass(frozen=True)
class Assessment:
    level: Risk
    reasons: list


def assess_weather(wind_mph, rain_in, snow_in, load_lb):
    """Overall risk at one checkpoint: the worst of wind (after load rules), rain and snow."""
    wind_level = apply_load_rules(wind_risk(wind_mph), load_lb)
    rain_level = rain_risk(rain_in)
    snow_level = snow_risk(snow_in)

    reasons = []
    if wind_level > Risk.LOW:
        reason = f'Wind {wind_mph:.0f} mph'
        if wind_level != wind_risk(wind_mph):
            reason += f' with a {load_lb:,} lb load'
        reasons.append(f'{reason}: {wind_level.label}')
    if rain_level > Risk.LOW:
        reasons.append(f'Rain {rain_in:.2f} in/hr: {rain_level.label}')
    if snow_level > Risk.LOW:
        reasons.append(f'Snow {snow_in:.2f} in/hr: {snow_level.label}')

    return Assessment(level=max(wind_level, rain_level, snow_level), reasons=reasons)


# Breakpoints where each risk level starts, used to give the heatmap a smooth scale.
WIND_STEPS = [0, 25, 35, 45, 55]
RAIN_STEPS = [0, 0.1, 0.25, 0.5, 1.0]
SNOW_STEPS = [0, 0.5, 1.0, 2.0, 3.0]


def risk_score(wind_mph, rain_in, snow_in, load_lb):
    """
    A 0-4 score for the heatmap that changes gradually instead of in steps.

    The whole number part always matches assess_weather(), e.g. 2.6 is High.
    """
    level = assess_weather(wind_mph, rain_in, snow_in, load_lb).level
    smooth = max(
        _position(wind_mph, WIND_STEPS),
        _position(rain_in, RAIN_STEPS),
        _position(snow_in, SNOW_STEPS),
    )
    return min(max(smooth, level), level + 0.99)


def _position(value, steps):
    if value >= steps[-1]:
        return len(steps) - 1
    for i in range(1, len(steps)):
        if value < steps[i]:
            return i - 1 + (value - steps[i - 1]) / (steps[i] - steps[i - 1])
    return 0.0
