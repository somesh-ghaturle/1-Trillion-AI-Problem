from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core.models import DataSource, TrustScore, ValidationResult
from core.utils.insights import check_drop, detect_anomalies, forecast


class CheckDropTest(SimpleTestCase):
    def test_two_sigma_drop_flagged(self):
        baseline, threshold = check_drop([90, 92, 89, 91, 90, 71])
        self.assertAlmostEqual(baseline, 90.4)
        self.assertLess(71, threshold)

    def test_normal_noise_and_rises_ignored(self):
        self.assertIsNone(check_drop([90, 92, 89, 91, 90, 87]))
        self.assertIsNone(check_drop([60, 62, 61, 95]))

    def test_minimum_drop_on_flat_history(self):
        # stdev is 0, so 2-sigma alone would flag a 1-point dip; MIN_DROP (5) prevents that
        self.assertIsNone(check_drop([80, 80, 80, 79]))
        self.assertIsNotNone(check_drop([80, 80, 80, 74]))

    def test_short_history_uses_fixed_drop(self):
        self.assertIsNone(check_drop([80]))
        self.assertIsNone(check_drop([80, 75]))
        self.assertIsNotNone(check_drop([80, 69]))


class ForecastTest(SimpleTestCase):
    def test_linear_projection_clamped(self):
        d0 = date(2026, 1, 1)
        result = forecast([d0, d0 + timedelta(days=1), d0 + timedelta(days=3)], [70, 72, 76])
        self.assertEqual((result['slope_per_day'], result['projected']), (2.0, 90.0))
        self.assertEqual(forecast([d0, d0 + timedelta(days=1), d0 + timedelta(days=2)], [90, 95, 100])['projected'], 100.0)

    def test_needs_three_points(self):
        self.assertIsNone(forecast([date(2026, 1, 1), date(2026, 1, 2)], [1, 2]))


class DetectAnomaliesTest(TestCase):
    def test_flags_latest_drop_and_shows_on_dashboard_and_api(self):
        source = DataSource.objects.create(name='BigQuery')
        now = timezone.now()
        for i, score in enumerate([90, 92, 89, 91, 71]):  # oldest -> newest
            ValidationResult.objects.create(source=source, quality_score=score, timestamp=now - timedelta(days=5 - i))
        TrustScore.objects.create(source=source, overall_score=85)
        anomalies = detect_anomalies()
        self.assertEqual([(a.source, a.measure, a.latest) for a in anomalies], [('BigQuery', 'data quality', 71)])
        self.assertContains(self.client.get('/'), 'BigQuery')
        data = self.client.get('/api/v1/insights/').json()
        self.assertEqual(data['anomalies'][0]['drop'], 19.5)
        self.assertIn('Trust score', data['outlook'])
