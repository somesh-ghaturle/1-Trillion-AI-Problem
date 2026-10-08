from django.contrib.auth.models import User
from core.tests import make_editor
from django.test import TestCase, Client
from django.urls import reverse
from core.models import DataSource, ValidationResult, TrustScore, GovernanceMetric


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_loads(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Trust Control Center')

    def test_dashboard_with_data(self):
        source = DataSource.objects.create(name='Test', source_type='database')
        TrustScore.objects.create(source=source, overall_score=80, trust_level='high')
        ValidationResult.objects.create(source=source, passed=True, quality_score=85)
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)


class DataSourcesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.source = DataSource.objects.create(
            name='Test Warehouse',
            source_type='snowflake',
            description='A test source'
        )

    def test_list_view(self):
        resp = self.client.get(reverse('data_sources'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Warehouse')

    def test_detail_view(self):
        resp = self.client.get(reverse('data_source_detail', args=[self.source.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Warehouse')

    def test_detail_404(self):
        resp = self.client.get(reverse('data_source_detail', args=[9999]))
        self.assertEqual(resp.status_code, 404)


class ValidateDataViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.force_login(make_editor())
        self.source = DataSource.objects.create(name='Test')

    def test_get_form(self):
        resp = self.client.get(reverse('validate_data', args=[self.source.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Validate Data Quality')

    def test_post_without_file(self):
        resp = self.client.post(reverse('validate_data', args=[self.source.pk]))
        self.assertEqual(resp.status_code, 200)


class CalculateTrustViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.source = DataSource.objects.create(name='Test')

    def test_get_form(self):
        resp = self.client.get(reverse('calculate_trust', args=[self.source.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Calculate Trust Score')


class GovernanceViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.force_login(make_editor())

    def test_governance_page(self):
        resp = self.client.get(reverse('governance_metrics'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Governance')

    def test_add_metric(self):
        resp = self.client.post(reverse('governance_metrics'), {
            'name': 'test_metric',
            'display_name': 'Test Metric',
            'description': 'A test metric',
            'data_type': 'numeric',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(GovernanceMetric.objects.filter(name='test_metric').exists())


class APIHealthViewTest(TestCase):
    def test_health_endpoint(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'running')


class HealthTrendTest(TestCase):
    def test_daily_averages_with_gaps(self):
        from datetime import timedelta
        from django.utils import timezone
        from core.views import health_trend
        source = DataSource.objects.create(name='S')
        now = timezone.now()
        TrustScore.objects.create(source=source, overall_score=80, calculated_at=now)
        TrustScore.objects.create(source=source, overall_score=60, calculated_at=now)
        TrustScore.objects.create(source=source, overall_score=50, calculated_at=now - timedelta(days=3))
        TrustScore.objects.create(source=source, overall_score=10, calculated_at=now - timedelta(days=40))  # outside window
        ValidationResult.objects.create(source=source, quality_score=90, timestamp=now - timedelta(days=3))

        trend = health_trend()
        self.assertEqual(len(trend['labels']), 4)  # every day from first to last
        self.assertEqual(len(trend['rows']), 2)  # table lists only days with data
        values = {s['name']: s['values'] for s in trend['series']}
        self.assertEqual(values['Trust score'], [50.0, None, None, 70.0])
        self.assertEqual(values['Data quality'], [90.0, None, None, None])
        self.assertEqual(values['Reconciliation consistency'], [None] * 4)

    def test_backdated_timestamp_is_kept(self):
        from datetime import timedelta
        from django.utils import timezone
        source = DataSource.objects.create(name='S')
        past = timezone.now() - timedelta(days=5)
        score = TrustScore.objects.create(source=source, overall_score=1, calculated_at=past)
        score.overall_score = 2
        score.save()
        score.refresh_from_db()
        self.assertEqual(score.calculated_at, past)

    def test_dashboard_embeds_trend(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertContains(resp, 'id="health-trend-data"')
        self.assertContains(resp, 'Health Over Time')
