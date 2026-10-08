from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import DataSource, GovernanceMetric, ReconciliationRun, SemanticDefinition
from core.tests import make_editor


class ReconciliationTaskTest(TestCase):
    def setUp(self):
        metric = GovernanceMetric.objects.create(name='rev', display_name='Rev', description='', data_type='n',
                                                 formula="SUM(amount) WHERE status = 'completed'")
        for name, formula in [('Snowflake', "SUM(amount) WHERE status = 'completed'"),
                              ('Tableau', "SUM(amount) WHERE status IN ('completed', 'pending')")]:
            SemanticDefinition.objects.create(governance_metric=metric, local_name='rev', local_formula=formula,
                                              source=DataSource.objects.create(name=name))
        self.api = APIClient()
        self.api.force_authenticate(make_editor())

    def test_api_run_updates_consistency_flags(self):
        # The API used to save runs without refreshing each mapping's is_consistent flag
        resp = self.api.post('/api/v1/reconciliations/run/')
        self.assertEqual((resp.status_code, resp.data['count']), (200, 1))
        flags = dict(SemanticDefinition.objects.values_list('source__name', 'is_consistent'))
        self.assertEqual(flags, {'Snowflake': True, 'Tableau': False})
        self.assertEqual(set(ReconciliationRun.objects.get().sources_compared.values_list('name', flat=True)),
                         {'Snowflake', 'Tableau'})  # 'Governance Standard' isn't a DataSource row

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_queued_mode_returns_202_and_ui_message(self):
        with mock.patch('core.tasks.run_reconciliation_task.delay', return_value=mock.Mock(id='abc123')) as delay:
            resp = self.api.post('/api/v1/reconciliations/run/')
            self.assertEqual((resp.status_code, resp.data), (202, {'status': 'queued', 'task_id': 'abc123'}))
            self.client.force_login(make_editor('ui'))
            page = self.client.post('/reconciliation/run/', follow=True)
        self.assertContains(page, 'started in the background')
        self.assertEqual(delay.call_count, 2)
        self.assertFalse(ReconciliationRun.objects.exists())
