from django.test import SimpleTestCase

from trips.services.risk import Risk, apply_load_rules, assess_weather, rain_risk, risk_score, snow_risk, wind_risk


class WindRiskTests(SimpleTestCase):
    def test_thresholds(self):
        cases = [(24.9, Risk.LOW), (25, Risk.MODERATE), (34.9, Risk.MODERATE), (35, Risk.HIGH),
                 (45, Risk.SEVERE), (54.9, Risk.SEVERE), (55, Risk.NO_TRAVEL)]
        for mph, expected in cases:
            with self.subTest(mph=mph):
                self.assertEqual(wind_risk(mph), expected)


class RainRiskTests(SimpleTestCase):
    def test_thresholds(self):
        cases = [(0.09, Risk.LOW), (0.10, Risk.MODERATE), (0.25, Risk.HIGH), (0.50, Risk.SEVERE),
                 (1.00, Risk.SEVERE), (1.01, Risk.NO_TRAVEL)]
        for inches, expected in cases:
            with self.subTest(inches=inches):
                self.assertEqual(rain_risk(inches), expected)


class SnowRiskTests(SimpleTestCase):
    def test_thresholds(self):
        cases = [(0.4, Risk.LOW), (0.5, Risk.MODERATE), (1.0, Risk.HIGH), (2.0, Risk.SEVERE),
                 (3.0, Risk.SEVERE), (3.1, Risk.NO_TRAVEL)]
        for inches, expected in cases:
            with self.subTest(inches=inches):
                self.assertEqual(snow_risk(inches), expected)


class LoadRuleTests(SimpleTestCase):
    def test_severe_wind_with_load_over_30000_is_no_travel(self):
        self.assertEqual(apply_load_rules(Risk.SEVERE, 30_001), Risk.NO_TRAVEL)
        self.assertEqual(apply_load_rules(Risk.SEVERE, 30_000), Risk.SEVERE)

    def test_high_wind_with_load_over_40000_is_severe(self):
        self.assertEqual(apply_load_rules(Risk.HIGH, 40_001), Risk.SEVERE)
        self.assertEqual(apply_load_rules(Risk.HIGH, 40_000), Risk.HIGH)

    def test_lighter_winds_are_not_affected(self):
        self.assertEqual(apply_load_rules(Risk.MODERATE, 80_000), Risk.MODERATE)

    def test_55_mph_is_no_travel_for_any_load(self):
        self.assertEqual(assess_weather(55, 0, 0, load_lb=0).level, Risk.NO_TRAVEL)


class AssessWeatherTests(SimpleTestCase):
    def test_worst_condition_wins(self):
        assessment = assess_weather(wind_mph=30, rain_in=0.6, snow_in=0.0, load_lb=10_000)
        self.assertEqual(assessment.level, Risk.SEVERE)
        self.assertEqual(assessment.reasons, ['Wind 30 mph: Moderate', 'Rain 0.60 in/hr: Severe'])

    def test_reason_mentions_load_when_it_raises_the_level(self):
        assessment = assess_weather(wind_mph=40, rain_in=0, snow_in=0, load_lb=45_000)
        self.assertEqual(assessment.level, Risk.SEVERE)
        self.assertEqual(assessment.reasons, ['Wind 40 mph with a 45,000 lb load: Severe'])

    def test_calm_weather_has_no_reasons(self):
        self.assertEqual(assess_weather(5, 0, 0, 20_000).reasons, [])


class RiskScoreTests(SimpleTestCase):
    def test_whole_number_matches_risk_level(self):
        samples = [(0, 0, 0), (30, 0, 0), (40, 0.3, 0), (50, 0, 1.5), (20, 1.0, 0), (60, 0, 0), (10, 0, 2.9)]
        for load in (0, 35_000, 45_000):
            for wind, rain, snow in samples:
                with self.subTest(wind=wind, rain=rain, snow=snow, load=load):
                    level = assess_weather(wind, rain, snow, load).level
                    self.assertEqual(int(risk_score(wind, rain, snow, load)), level)

    def test_score_rises_gradually(self):
        self.assertLess(risk_score(26, 0, 0, 0), risk_score(33, 0, 0, 0))
