from django.test import TestCase
from rest_framework.test import APIClient
from core.models import DataSource, TrustScore, ValidationResult, GovernanceMetric


class DataSourceAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.source = DataSource.objects.create(
            name='API Test Source',
            source_type='database'
        )

    def test_list_sources(self):
        resp = self.client.get('/api/v1/sources/')
        self.assertEqual(resp.status_code, 200)

    def test_create_source(self):
        resp = self.client.post('/api/v1/sources/', {
            'name': 'New Source',
            'source_type': 'snowflake',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(DataSource.objects.count(), 2)

    def test_get_source_detail(self):
        resp = self.client.get(f'/api/v1/sources/{self.source.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['name'], 'API Test Source')

    def test_update_source(self):
        resp = self.client.patch(f'/api/v1/sources/{self.source.pk}/', {
            'name': 'Updated Source'
        })
        self.assertEqual(resp.status_code, 200)
        self.source.refresh_from_db()
        self.assertEqual(self.source.name, 'Updated Source')

    def test_delete_source(self):
        resp = self.client.delete(f'/api/v1/sources/{self.source.pk}/')
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(DataSource.objects.count(), 0)


class TrustScoreAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.source = DataSource.objects.create(name='Test', source_type='database')
        self.score = TrustScore.objects.create(
            source=self.source,
            overall_score=85,
            trust_level='high',
            completeness_score=90,
            accuracy_score=80,
        )

    def test_list_scores(self):
        resp = self.client.get('/api/v1/trust-scores/')
        self.assertEqual(resp.status_code, 200)

    def test_get_score_detail(self):
        resp = self.client.get(f'/api/v1/trust-scores/{self.score.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['overall_score'], 85)


class ValidationResultAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.source = DataSource.objects.create(name='Test', source_type='database')
        self.validation = ValidationResult.objects.create(
            source=self.source, passed=True, quality_score=90,
            total_rules=5, passed_rules=5, failed_rules=0
        )

    def test_list_validations(self):
        resp = self.client.get('/api/v1/validations/')
        self.assertEqual(resp.status_code, 200)

    def test_get_validation_detail(self):
        resp = self.client.get(f'/api/v1/validations/{self.validation.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['passed'])


class GovernanceMetricAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_metric(self):
        resp = self.client.post('/api/v1/governance-metrics/', {
            'name': 'api_revenue',
            'display_name': 'API Revenue',
            'description': 'Test metric',
            'data_type': 'numeric',
        })
        self.assertEqual(resp.status_code, 201)

    def test_list_metrics(self):
        GovernanceMetric.objects.create(
            name='test', display_name='Test', description='test', data_type='numeric'
        )
        resp = self.client.get('/api/v1/governance-metrics/')
        self.assertEqual(resp.status_code, 200)


class APIHealthTest(TestCase):
    def test_health(self):
        resp = self.client.get('/api/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'running')
        self.assertIn('total_sources', data)
