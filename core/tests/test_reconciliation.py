from django.test import TestCase, Client
from django.urls import reverse
from core.models import (
    DataSource, GovernanceMetric, SemanticDefinition,
    ReconciliationRun, DataLineage,
)
from core.utils.reconciliation import ReconciliationEngine


class ReconciliationEngineTest(TestCase):
    def setUp(self):
        self.engine = ReconciliationEngine()
        self.metric = GovernanceMetric.objects.create(
            name='total_revenue',
            display_name='Total Revenue',
            description='Sum of all revenue',
            formula="SUM(amount) WHERE status = 'completed'",
            data_type='numeric',
        )
        self.snowflake = DataSource.objects.create(name='Snowflake', source_type='snowflake')
        self.tableau = DataSource.objects.create(name='Tableau', source_type='tableau')
        self.db = DataSource.objects.create(name='PostgresDB', source_type='database')

    def test_no_definitions(self):
        result = self.engine.reconcile_metric(self.metric, SemanticDefinition.objects.none())
        self.assertEqual(result.total_sources, 0)
        self.assertEqual(result.status, 'consistent')

    def test_single_definition(self):
        SemanticDefinition.objects.create(
            governance_metric=self.metric,
            source=self.snowflake,
            local_name='total_revenue',
            local_formula="SUM(amount) WHERE status = 'completed'",
        )
        defs = SemanticDefinition.objects.filter(governance_metric=self.metric)
        result = self.engine.reconcile_metric(self.metric, defs)
        self.assertEqual(result.total_sources, 1)
        self.assertEqual(result.status, 'consistent')

    def test_consistent_definitions(self):
        SemanticDefinition.objects.create(
            governance_metric=self.metric,
            source=self.snowflake,
            local_name='total_revenue',
            local_formula="SUM(amount) WHERE status = 'completed'",
        )
        SemanticDefinition.objects.create(
            governance_metric=self.metric,
            source=self.tableau,
            local_name='total_revenue',
            local_formula="SUM(amount) WHERE status = 'completed'",
        )
        defs = SemanticDefinition.objects.filter(governance_metric=self.metric)
        result = self.engine.reconcile_metric(self.metric, defs)
        self.assertEqual(result.total_sources, 2)
        self.assertEqual(result.consistency_score, 100.0)
        self.assertEqual(result.status, 'consistent')

    def test_divergent_formulas(self):
        SemanticDefinition.objects.create(
            governance_metric=self.metric,
            source=self.snowflake,
            local_name='total_revenue',
            local_formula="SUM(amount) WHERE status = 'completed'",
        )
        SemanticDefinition.objects.create(
            governance_metric=self.metric,
            source=self.tableau,
            local_name='rev_total',
            local_formula="COUNT(transactions) * avg_price",
        )
        defs = SemanticDefinition.objects.filter(governance_metric=self.metric)
        result = self.engine.reconcile_metric(self.metric, defs)
        self.assertGreater(len(result.divergences), 0)
        self.assertLess(result.consistency_score, 100)

    def test_naming_divergence(self):
        SemanticDefinition.objects.create(
            governance_metric=self.metric,
            source=self.snowflake,
            local_name='rev_total_usd',
            local_formula="SUM(amount) WHERE status = 'completed'",
        )
        defs = SemanticDefinition.objects.filter(governance_metric=self.metric)
        result = self.engine.reconcile_metric(self.metric, defs)
        naming_issues = [d for d in result.divergences if d.divergence_type == 'naming']
        self.assertGreater(len(naming_issues), 0)

    def test_reconcile_all(self):
        metric2 = GovernanceMetric.objects.create(
            name='customer_count', display_name='Customer Count',
            description='Total customers', data_type='numeric',
        )
        SemanticDefinition.objects.create(
            governance_metric=self.metric,
            source=self.snowflake,
            local_name='total_revenue',
        )
        results = self.engine.reconcile_all(
            GovernanceMetric.objects.all(),
            SemanticDefinition.objects.all(),
        )
        self.assertEqual(len(results), 2)


class SemanticDefinitionModelTest(TestCase):
    def test_create(self):
        metric = GovernanceMetric.objects.create(
            name='test', display_name='Test', description='test', data_type='numeric'
        )
        source = DataSource.objects.create(name='Source A')
        defn = SemanticDefinition.objects.create(
            governance_metric=metric,
            source=source,
            local_name='test_local',
            local_formula='COUNT(*)',
        )
        self.assertEqual(str(defn), 'test @ Source A')
        self.assertTrue(defn.is_consistent)

    def test_unique_together(self):
        metric = GovernanceMetric.objects.create(
            name='unique_test', display_name='Unique Test',
            description='test', data_type='numeric'
        )
        source = DataSource.objects.create(name='Source B')
        SemanticDefinition.objects.create(
            governance_metric=metric, source=source, local_name='a'
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SemanticDefinition.objects.create(
                governance_metric=metric, source=source, local_name='b'
            )


class DataLineageModelTest(TestCase):
    def test_create(self):
        s1 = DataSource.objects.create(name='Source A')
        s2 = DataSource.objects.create(name='Source B')
        flow = DataLineage.objects.create(
            source_from=s1, source_to=s2, flow_type='etl', schedule='daily'
        )
        self.assertEqual(str(flow), 'Source A -> Source B (etl)')


class ReconciliationViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_reconciliation_page(self):
        resp = self.client.get(reverse('reconciliation_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Reconciliation')

    def test_semantic_definitions_page(self):
        resp = self.client.get(reverse('semantic_definitions'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Semantic')

    def test_lineage_page(self):
        resp = self.client.get(reverse('lineage'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Lineage')

    def test_osi_export_page(self):
        resp = self.client.get(reverse('osi_export'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'OSI')

    def test_osi_export_download(self):
        resp = self.client.get(reverse('osi_export') + '?format=download')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')

    def test_run_reconciliation(self):
        metric = GovernanceMetric.objects.create(
            name='test_recon', display_name='Test Recon',
            description='test', data_type='numeric',
        )
        resp = self.client.post(reverse('run_reconciliation'))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ReconciliationRun.objects.exists())

    def test_add_semantic_definition(self):
        metric = GovernanceMetric.objects.create(
            name='sem_test', display_name='Sem Test',
            description='test', data_type='numeric',
        )
        source = DataSource.objects.create(name='Test Source')
        resp = self.client.post(reverse('semantic_definitions'), {
            'governance_metric': metric.pk,
            'source': source.pk,
            'local_name': 'local_test',
            'local_formula': 'COUNT(*)',
            'definition_type': 'metric',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SemanticDefinition.objects.filter(local_name='local_test').exists())

    def test_add_lineage_flow(self):
        s1 = DataSource.objects.create(name='From')
        s2 = DataSource.objects.create(name='To')
        resp = self.client.post(reverse('lineage'), {
            'source_from': s1.pk,
            'source_to': s2.pk,
            'flow_type': 'etl',
            'description': 'Daily sync',
            'schedule': 'daily',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(DataLineage.objects.exists())


class OSIExportImportTest(TestCase):
    def test_export_spec(self):
        from core.utils.osi_export import export_osi_spec
        metric = GovernanceMetric.objects.create(
            name='export_test', display_name='Export Test',
            description='test', data_type='numeric', formula='SUM(x)',
        )
        source = DataSource.objects.create(name='Source X', source_type='snowflake')
        SemanticDefinition.objects.create(
            governance_metric=metric, source=source,
            local_name='x_total', local_formula='SUM(x)',
        )
        spec = export_osi_spec(
            GovernanceMetric.objects.all(),
            SemanticDefinition.objects.all(),
            DataSource.objects.all(),
        )
        self.assertEqual(spec['osi_version'], '1.0')
        self.assertEqual(len(spec['metrics']), 1)
        self.assertEqual(len(spec['semantic_mappings']), 1)

    def test_import_spec(self):
        from core.utils.osi_export import import_osi_spec
        spec = {
            'metrics': [
                {
                    'id': 'imported_metric',
                    'display_name': 'Imported Metric',
                    'description': 'From import',
                    'data_type': 'numeric',
                    'canonical_formula': 'SUM(y)',
                }
            ],
            'data_sources': [],
            'semantic_mappings': [],
        }
        stats = import_osi_spec(spec)
        self.assertEqual(stats['metrics_created'], 1)
        self.assertTrue(GovernanceMetric.objects.filter(name='imported_metric').exists())


class NewAPIEndpointsTest(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.metric = GovernanceMetric.objects.create(
            name='api_test', display_name='API Test',
            description='test', data_type='numeric',
        )
        self.source = DataSource.objects.create(name='API Source')

    def test_semantic_definitions_api(self):
        resp = self.client.get('/api/v1/semantic-definitions/')
        self.assertEqual(resp.status_code, 200)

    def test_create_semantic_definition_api(self):
        resp = self.client.post('/api/v1/semantic-definitions/', {
            'governance_metric': self.metric.pk,
            'source': self.source.pk,
            'local_name': 'api_local',
            'definition_type': 'metric',
        })
        self.assertEqual(resp.status_code, 201)

    def test_reconciliations_api(self):
        resp = self.client.get('/api/v1/reconciliations/')
        self.assertEqual(resp.status_code, 200)

    def test_run_reconciliation_api(self):
        resp = self.client.post('/api/v1/reconciliations/run/')
        self.assertEqual(resp.status_code, 200)

    def test_lineage_api(self):
        resp = self.client.get('/api/v1/lineage/')
        self.assertEqual(resp.status_code, 200)

    def test_osi_export_api(self):
        resp = self.client.get('/api/v1/governance-metrics/osi-export/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['osi_version'], '1.0')
