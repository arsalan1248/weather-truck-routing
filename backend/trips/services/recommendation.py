from dataclasses import dataclass


@dataclass(frozen=True)
class RouteSummary:
    route_id: str
    severe_miles: float
    high_miles: float
    no_travel_miles: float
    average_risk: float
    duration_seconds: float


def ranking_key(summary):
    """
    The order from the brief: fewest Severe miles, fewest High miles, lowest
    average risk, shortest time. The brief doesn't rank No Travel, so any route
    that has it goes to the bottom.
    """
    return (
        summary.no_travel_miles > 0,
        round(summary.severe_miles, 1),
        round(summary.high_miles, 1),
        round(summary.average_risk, 2),
        summary.duration_seconds,
    )


def rank_routes(summaries):
    return sorted(summaries, key=ranking_key)


def explain_choice(ranked):
    """One sentence on why the first route in `ranked` won."""
    best = ranked[0]
    if best.no_travel_miles > 0:
        return 'Every route has No Travel conditions. Consider a different departure time.'
    if len(ranked) == 1:
        return 'This is the only route available.'

    runner_up = ranked[1]
    name = f'Route {runner_up.route_id}'

    # Routes with No Travel are sorted last, so this means every other route has it.
    if runner_up.no_travel_miles > 0:
        return 'The only route without No Travel conditions.'
    if round(best.severe_miles, 1) < round(runner_up.severe_miles, 1):
        return f'Fewest Severe miles: {best.severe_miles:.0f} vs {runner_up.severe_miles:.0f} on {name}.'
    if round(best.high_miles, 1) < round(runner_up.high_miles, 1):
        return f'Same Severe miles, but fewest High miles: {best.high_miles:.0f} vs {runner_up.high_miles:.0f} on {name}.'
    if round(best.average_risk, 2) < round(runner_up.average_risk, 2):
        return f'Lowest average risk: {best.average_risk:.2f} vs {runner_up.average_risk:.2f} on {name}.'
    minutes_faster = round((runner_up.duration_seconds - best.duration_seconds) / 60)
    return f'Same weather risk as {name}, and {minutes_faster} min faster.'
