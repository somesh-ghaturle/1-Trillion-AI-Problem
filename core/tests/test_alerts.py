import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from core import alerts
from core.models import DataSource, GovernanceMetric, ReconciliationRun, ValidationResult


class _Hook(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        _Hook.received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


class AlertsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = HTTPServer(('127.0.0.1', 0), _Hook)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/hook'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        super().tearDownClass()

    def setUp(self):
        _Hook.received.clear()
        self.source = DataSource.objects.create(name='BigQuery')

    def save_validation(self, score, passed, days_ago=0):
        with self.captureOnCommitCallbacks(execute=True):
            ValidationResult.objects.create(source=self.source, quality_score=score, passed=passed,
                                            timestamp=timezone.now() - timedelta(days=days_ago))

    @override_settings(ALERT_EMAILS=['oncall@example.com'])
    def test_failed_validation_webhook_and_email(self):
        with override_settings(ALERT_WEBHOOK_URL=self.url):
            self.save_validation(55, passed=False)
        self.assertEqual(_Hook.received[0]['kind'], 'validation_failed')
        self.assertIn('BigQuery', _Hook.received[0]['text'])  # Slack-compatible field
        self.assertEqual(mail.outbox[0].to, ['oncall@example.com'])
        self.assertIn('Validation failed for BigQuery', mail.outbox[0].subject)

    @override_settings(ALERT_EMAILS=['oncall@example.com'])
    def test_score_drop_alert(self):
        with alerts.suppressed():
            for i, score in enumerate([90, 92, 89, 91]):
                ValidationResult.objects.create(source=self.source, quality_score=score, passed=True,
                                                timestamp=timezone.now() - timedelta(days=5 - i))
        self.save_validation(71, passed=True)
        self.assertEqual([m.subject for m in mail.outbox],
                         ['[Trust Control Center] BigQuery data quality dropped to 71.0% (19.5 below usual)'])

    @override_settings(ALERT_EMAILS=['oncall@example.com'])
    def test_critical_reconciliation_only(self):
        metric = GovernanceMetric.objects.create(name='rev', display_name='Rev', description='', data_type='n')
        with self.captureOnCommitCallbacks(execute=True):
            ReconciliationRun.objects.create(governance_metric=metric, divergences=[{'severity': 'high'}])
            ReconciliationRun.objects.create(governance_metric=metric, divergences=[
                {'severity': 'critical', 'detail': 'Measure differs'}])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('1 critical divergence(s) in "rev"', mail.outbox[0].subject)

    @override_settings(ALERT_EMAILS=['oncall@example.com'])
    def test_suppressed_and_passing_runs_send_nothing(self):
        with alerts.suppressed():
            self.save_validation(10, passed=False)
        self.save_validation(95, passed=True)
        self.assertEqual(mail.outbox, [])

    @override_settings(ALERT_WEBHOOK_URL='http://127.0.0.1:9/unreachable', ALERT_EMAILS=[])
    def test_webhook_failure_never_breaks_the_save(self):
        with self.assertLogs('core.alerts', level='ERROR'):
            self.save_validation(10, passed=False)
        self.assertEqual(ValidationResult.objects.count(), 1)

    @override_settings(ALERT_WEBHOOK_URL='file:///etc/passwd', ALERT_EMAILS=[])
    def test_non_http_webhook_refused(self):
        with self.assertLogs('core.alerts', level='ERROR'):
            self.save_validation(10, passed=False)
