from django.test import SimpleTestCase

from trips.services.recommendation import RouteSummary, explain_choice, rank_routes


def summary(route_id, severe=0, high=0, no_travel=0, average=0.0, hours=10):
    return RouteSummary(route_id, severe, high, no_travel, average, hours * 3600)


def ranked_ids(*summaries):
    return [s.route_id for s in rank_routes(summaries)]


class RankRoutesTests(SimpleTestCase):
    def test_fewest_severe_miles_comes_first(self):
        self.assertEqual(ranked_ids(summary('A', severe=30, hours=8), summary('B', severe=10, hours=12)), ['B', 'A'])

    def test_high_miles_break_a_severe_tie(self):
        self.assertEqual(ranked_ids(summary('A', severe=10, high=50), summary('B', severe=10, high=20)), ['B', 'A'])

    def test_average_risk_breaks_a_high_tie(self):
        self.assertEqual(ranked_ids(summary('A', average=0.8), summary('B', average=0.3)), ['B', 'A'])

    def test_travel_time_is_the_last_tie_breaker(self):
        self.assertEqual(ranked_ids(summary('A', hours=11), summary('B', hours=9)), ['B', 'A'])

    def test_no_travel_goes_last_even_with_fewer_severe_miles(self):
        self.assertEqual(ranked_ids(summary('A', no_travel=5), summary('B', severe=80)), ['B', 'A'])


class ExplainChoiceTests(SimpleTestCase):
    def explain(self, *summaries):
        return explain_choice(rank_routes(summaries))

    def test_explains_severe_miles(self):
        reason = self.explain(summary('A', severe=40), summary('B', severe=5))
        self.assertEqual(reason, 'Fewest Severe miles: 5 vs 40 on Route A.')

    def test_explains_travel_time_when_risk_is_equal(self):
        reason = self.explain(summary('A', hours=11), summary('B', hours=9))
        self.assertIn('fastest', reason)

    def test_warns_when_every_route_has_no_travel(self):
        reason = self.explain(summary('A', no_travel=5), summary('B', no_travel=10))
        self.assertIn('Every route has No Travel', reason)

    def test_only_safe_route(self):
        reason = self.explain(summary('A', no_travel=5), summary('B', severe=50))
        self.assertEqual(reason, 'The only route without No Travel conditions.')
