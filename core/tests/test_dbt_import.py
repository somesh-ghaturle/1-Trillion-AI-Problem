import io
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.models import DataSource, GovernanceMetric, SemanticDefinition
from core.tests import make_editor
from core.utils.dbt_import import import_metrics, load_project, load_texts
from core.utils.reconciliation import ReconciliationEngine

EXAMPLE = Path(__file__).resolve().parents[2] / 'examples' / 'dbt_project'

LEGACY = """
semantic_models:
  - name: orders
    dimensions:
      - {name: order_status, type: categorical, expr: status}
      - {name: is_big, type: categorical, expr: "case when amount > 100 then true else false end"}
      - {name: region, type: categorical}
    measures:
      - {name: revenue, agg: sum, expr: amount}
      - {name: buyers, agg: count_distinct, expr: customer_id}
      - {name: p90, agg: percentile, expr: amount, agg_params: {percentile: 0.9}}
      - {name: refunds, agg: sum_boolean, expr: is_refund}
metrics:
  - name: revenue
    type: simple
    type_params:
      measure: {name: revenue, filter: "{{ Dimension('order__region') }} = 'EU'"}
    filter:
      - "{{ Dimension('order__order_status') }} = 'completed'"
      - "{{ Dimension('order__is_big') }}"
  - name: buyers
    type: simple
    type_params: {measure: buyers}
    filter: "{{ Dimension('order__region') }} = 'EU' or {{ Dimension('order__region') }} = 'UK'"
  - name: p90
    type: simple
    type_params: {measure: p90}
  - name: refunds
    type: simple
    type_params: {measure: refunds}
  - name: revenue_per_buyer
    type: ratio
    type_params:
      numerator: {name: revenue, filter: "{{ TimeDimension('metric_time', 'day') }} >= '2026-01-01'"}
      denominator: buyers
  - name: net
    type: derived
    type_params:
      expr: revenue - refunds
      metrics: [revenue, refunds]
"""

MODERN = """
models:
  - name: dim_customers
    columns:
      - name: subscription_status
        dimension: {type: categorical, name: customer_status}
    metrics:
      - name: customers
        type: simple
        agg: count_distinct
        expr: customer_id
        filter: "{{ Dimension('customer__customer_status') }} = 'active'"
"""


class ParseTest(SimpleTestCase):
    def render(self, *texts):
        project = load_texts([(f'f{i}.yml', t) for i, t in enumerate(texts)])
        return {m.name: m for m in project.rendered_metrics()}, project.errors

    def test_legacy_layout(self):
        metrics, errors = self.render(LEGACY)
        self.assertEqual(errors, [])
        self.assertEqual(
            metrics['revenue'].formula,
            "SUM(amount) WHERE status = 'completed' AND (case when amount > 100 then true else false end) AND region = 'EU'",
        )
        self.assertEqual(metrics['buyers'].formula, "COUNT(DISTINCT customer_id) WHERE (region = 'EU' or region = 'UK')")
        self.assertEqual(metrics['p90'].formula, 'PERCENTILE(amount, 0.9)')
        self.assertEqual(metrics['refunds'].formula, 'SUM(CAST(is_refund AS INT))')

    def test_ratio_and_derived(self):
        metrics, _ = self.render(LEGACY)
        self.assertEqual(
            metrics['revenue_per_buyer'].formula,
            "(SUM(amount) WHERE status = 'completed' AND (case when amount > 100 then true else false end) "
            "AND region = 'EU' AND metric_time >= '2026-01-01') / (COUNT(DISTINCT customer_id) WHERE (region = 'EU' or region = 'UK'))",
        )
        self.assertEqual(metrics['net'].formula, 'revenue - refunds')
        self.assertIn('revenue, refunds', metrics['net'].notes[0])

    def test_modern_layout_resolves_column_dimension(self):
        metrics, errors = self.render(MODERN)
        self.assertEqual(errors, [])
        self.assertEqual(metrics['customers'].formula, "COUNT(DISTINCT customer_id) WHERE subscription_status = 'active'")

    def test_measures_and_metrics_across_files(self):
        legacy_measures = LEGACY.split('metrics:')[0]
        metric = "metrics:\n  - {name: total, type: simple, type_params: {measure: revenue}}\n"
        metrics, errors = self.render(legacy_measures, metric)
        self.assertEqual((metrics['total'].formula, errors), ('SUM(amount)', []))

    def test_errors_are_reported_not_raised(self):
        bad = """
metrics:
  - {name: ghost, type: simple, type_params: {measure: nope}}
  - {name: a, type: ratio, type_params: {numerator: b, denominator: b}}
  - {name: b, type: ratio, type_params: {numerator: a, denominator: a}}
  - {name: odd, type: weird}
"""
        metrics, errors = self.render(bad)
        self.assertEqual(metrics, {})
        joined = ' | '.join(errors)
        for expected in ('measure "nope" is not defined', 'circular metric reference', 'unsupported metric type "weird"'):
            self.assertIn(expected, joined)

    def test_unquoted_jinja_gets_a_hint(self):
        _, errors = self.render("metrics:\n  - name: x\n    filter: {{ Dimension('a__b') }} = 1\n")
        self.assertIn('must be quoted', errors[0])

    def test_load_project_skips_build_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'models').mkdir()
            (Path(tmp) / 'target').mkdir()
            (Path(tmp) / 'models' / 'm.yml').write_text(MODERN)
            (Path(tmp) / 'target' / 'junk.yml').write_text('metrics: [')
            project = load_project(tmp)
            self.assertEqual([m.name for m in project.rendered_metrics()], ['customers'])
            self.assertEqual(project.errors, [])


class ImportTest(TestCase):
    def setUp(self):
        self.metric = GovernanceMetric.objects.create(
            name='Customers', display_name='Customers', description='', data_type='numeric',
            formula="COUNT(DISTINCT customer_id) WHERE subscription_status = 'active'")

    def test_import_matches_by_name_and_is_idempotent(self):
        stats = import_metrics(load_texts([('m.yml', MODERN)]))
        self.assertEqual([g.name for g, _ in stats['imported']], ['Customers'])
        source = DataSource.objects.get(name='dbt Semantic Layer')
        self.assertEqual(source.source_type, 'dbt')
        import_metrics(load_texts([('m.yml', MODERN.replace("'active'", "'trialing'"))]))
        defs = SemanticDefinition.objects.filter(source=source)
        self.assertEqual(defs.count(), 1)
        self.assertIn("'trialing'", defs.get().local_formula)

    def test_unmatched_and_dry_run_write_nothing(self):
        stats = import_metrics(load_texts([('l.yml', LEGACY)]), dry_run=True)
        self.assertEqual(stats['imported'], [])
        self.assertEqual(len(stats['unmatched']), 6)
        self.assertFalse(DataSource.objects.filter(name='dbt Semantic Layer').exists())
        import_metrics(load_texts([('m.yml', MODERN)]), dry_run=True)
        self.assertFalse(SemanticDefinition.objects.exists())

    def test_example_project_reconciles(self):
        call_command('seed_data', stdout=io.StringIO())
        call_command('import_dbt', str(EXAMPLE), stdout=io.StringIO(), stderr=io.StringIO())
        engine = ReconciliationEngine()

        def dbt_vs_standard(name):
            metric = GovernanceMetric.objects.get(name=name)
            result = engine.reconcile_metric(metric, metric.semantic_definitions.select_related('source'))
            return [d for d in result.divergences
                    if d.source_a == 'Governance Standard' and d.source_b == 'dbt Semantic Layer']

        self.assertEqual(dbt_vs_standard('monthly_recurring_revenue'), [])
        self.assertEqual(dbt_vs_standard('average_deal_size'), [])
        revenue = dbt_vs_standard('total_revenue')
        self.assertEqual([(d.divergence_type, d.severity) for d in revenue], [('filter', 'high')])
        self.assertIn("also includes 'refunded'", revenue[0].detail)
        self.assertIn('last_login', dbt_vs_standard('customer_count')[0].detail)
        self.assertEqual(dbt_vs_standard('churn_rate')[0].severity, 'critical')


class UploadViewTest(TestCase):
    def setUp(self):
        GovernanceMetric.objects.create(name='customers', display_name='Customers', description='', data_type='numeric')

    def upload(self, *files, **extra):
        return self.client.post(reverse('dbt_import'), {'dbt_files': list(files), **extra})

    def yml(self, text=MODERN, name='m.yml'):
        return SimpleUploadedFile(name, text.encode(), content_type='application/x-yaml')

    def test_anonymous_redirected_and_viewer_forbidden(self):
        self.assertEqual(self.upload(self.yml()).status_code, 302)
        self.client.force_login(User.objects.create_user('viewer'))
        self.assertEqual(self.upload(self.yml()).status_code, 403)
        self.assertFalse(SemanticDefinition.objects.exists())

    def test_editor_upload_imports(self):
        self.client.force_login(make_editor())
        resp = self.client.post(reverse('dbt_import'), {'dbt_files': [self.yml()], 'source_name': 'Prod dbt'}, follow=True)
        self.assertContains(resp, 'Imported 1 dbt metric')
        self.assertEqual(SemanticDefinition.objects.get().source.name, 'Prod dbt')

    def test_rejects_wrong_type_and_oversized(self):
        self.client.force_login(make_editor())
        resp = self.client.post(reverse('dbt_import'), {'dbt_files': [self.yml(name='m.txt')]}, follow=True)
        self.assertContains(resp, 'not a .yml/.yaml file')
        big = self.yml(text='# ' + 'x' * (1024 * 1024))
        resp = self.client.post(reverse('dbt_import'), {'dbt_files': [big]}, follow=True)
        self.assertContains(resp, 'larger than 1 MB')
        self.assertFalse(SemanticDefinition.objects.exists())
