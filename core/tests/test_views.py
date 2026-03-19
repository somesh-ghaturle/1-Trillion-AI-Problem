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
