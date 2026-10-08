from django.test import TestCase
from rest_framework.test import APIClient

from core.models import DataSource, GovernanceMetric, ReconciliationRun, SemanticDefinition, TrustScore


class SearchFilterTest(TestCase):
    def setUp(self):
        self.snow = DataSource.objects.create(name='Snowflake DWH', source_type='snowflake', description='warehouse')
        self.tab = DataSource.objects.create(name='Tableau Cloud', source_type='tableau')
        TrustScore.objects.create(source=self.snow, overall_score=95, trust_level='verified')
        TrustScore.objects.create(source=self.tab, overall_score=50, trust_level='low')
        self.rev = GovernanceMetric.objects.create(name='total_revenue', display_name='Total Revenue', description='',
                                                   data_type='n', category='Finance', formula='SUM(amount)')
        self.nps = GovernanceMetric.objects.create(name='nps', display_name='NPS', description='', data_type='n',
                                                   category='Customer')
        SemanticDefinition.objects.create(governance_metric=self.rev, source=self.snow, local_name='rev', is_consistent=True)
        SemanticDefinition.objects.create(governance_metric=self.rev, source=self.tab, local_name='rev_t',
                                          local_formula='SUM(amount) pending', is_consistent=False)
        ReconciliationRun.objects.create(governance_metric=self.rev, status='divergent', divergences=[{'severity': 'critical'}])
        ReconciliationRun.objects.create(governance_metric=self.nps, status='consistent', divergences=[])

    def names(self, url, marker):
        html = self.client.get(url).content.decode()
        return [n for n in marker if n in html]

    def test_sources_search_type_and_latest_trust(self):
        names = ['Snowflake DWH', 'Tableau Cloud']
        self.assertEqual(self.names('/sources/?q=wareHOUSE', names), ['Snowflake DWH'])
        self.assertEqual(self.names('/sources/?type=tableau', names), ['Tableau Cloud'])
        self.assertEqual(self.names('/sources/?trust=verified', names), ['Snowflake DWH'])
        self.assertContains(self.client.get('/sources/?q=zzz'), 'No sources match these filters')

    def test_governance_search_and_category(self):
        names = ['Total Revenue', 'NPS']
        self.assertEqual(self.names('/governance/?q=amount', names), ['Total Revenue'])
        self.assertEqual(self.names('/governance/?category=Customer', names), ['NPS'])

    def test_semantic_filters(self):
        resp = self.client.get(f'/semantic/?consistency=inconsistent&metric={self.rev.id}')
        self.assertEqual(list(resp.context['definitions'].values_list('local_name', flat=True)), ['rev_t'])
        resp = self.client.get('/semantic/?q=pending')
        self.assertEqual(list(resp.context['definitions'].values_list('local_name', flat=True)), ['rev_t'])

    def test_reconciliation_status_and_severity(self):
        runs = lambda url: [r.governance_metric.name for r in self.client.get(url).context['recent_runs']]
        self.assertEqual(runs('/reconciliation/?status=consistent'), ['nps'])
        self.assertEqual(runs('/reconciliation/?severity=critical'), ['total_revenue'])

    def test_api_search_filter_ordering(self):
        api = APIClient()
        names = lambda url: [r['name'] for r in api.get(url).data['results']]
        self.assertEqual(names('/api/v1/sources/?search=tableau'), ['Tableau Cloud'])
        self.assertEqual(names('/api/v1/sources/?source_type=snowflake'), ['Snowflake DWH'])
        self.assertEqual(names('/api/v1/governance-metrics/?ordering=-name'), ['total_revenue', 'nps'])
        scores = [r['overall_score'] for r in api.get('/api/v1/trust-scores/?ordering=overall_score').data['results']]
        self.assertEqual(scores, [50, 95])
