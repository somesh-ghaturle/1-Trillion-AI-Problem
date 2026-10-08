from unittest import mock

from django.db import DatabaseError
from django.test import TestCase, override_settings

from core.models import DataSource, GovernanceMetric, ReconciliationRun, TrustScore


class HealthzTest(TestCase):
    def test_ok(self):
        resp = self.client.get('/healthz')
        self.assertEqual((resp.status_code, resp.json()['database']), (200, 'ok'))

    def test_database_down_is_503(self):
        with mock.patch('core.monitoring.connection.cursor', side_effect=DatabaseError('down')):
            self.assertEqual(self.client.get('/healthz').status_code, 503)


class MetricsTest(TestCase):
    def test_disabled_without_token(self):
        with override_settings(METRICS_TOKEN=''):
            self.assertEqual(self.client.get('/metrics').status_code, 404)

    @override_settings(METRICS_TOKEN='s3cret')
    def test_requires_bearer_token(self):
        self.assertEqual(self.client.get('/metrics').status_code, 401)
        self.assertEqual(self.client.get('/metrics', HTTP_AUTHORIZATION='Bearer wrong').status_code, 401)

    @override_settings(METRICS_TOKEN='s3cret')
    def test_exports_request_and_app_metrics(self):
        source = DataSource.objects.create(name='Snowflake')
        TrustScore.objects.create(source=source, overall_score=87.5)
        metric = GovernanceMetric.objects.create(name='rev', display_name='Rev', description='', data_type='n')
        ReconciliationRun.objects.create(governance_metric=metric, consistency_score=40, divergences=[
            {'severity': 'critical'}, {'severity': 'high'}, {'severity': 'high'}])
        self.client.get('/')
        body = self.client.get('/metrics', HTTP_AUTHORIZATION='Bearer s3cret').content.decode()
        self.assertIn('tcc_trust_score{source="Snowflake"} 87.5', body)
        self.assertIn('tcc_reconciliation_consistency{metric="rev"} 40.0', body)
        self.assertIn('tcc_open_divergences{severity="high"} 2.0', body)
        self.assertIn('django_http_requests_total_by_view_transport_method_total', body)
