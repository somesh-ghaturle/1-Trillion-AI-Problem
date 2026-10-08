from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import DataSource, GovernanceMetric, SemanticDefinition
from core.tests import make_editor
from core.utils.bulk_import import import_semantic_csv

HEADER = 'governance_metric_name,source_name,local_name,local_formula,local_description\n'


class BulkImportTest(TestCase):
    def setUp(self):
        self.metric = GovernanceMetric.objects.create(name='revenue', display_name='Revenue', description='', data_type='n')
        self.source = DataSource.objects.create(name='Snowflake')
        DataSource.objects.create(name='Tableau')

    def test_creates_and_updates_case_insensitively(self):
        SemanticDefinition.objects.create(governance_metric=self.metric, source=self.source, local_name='old')
        stats = import_semantic_csv(HEADER + 'Revenue,snowflake,rev,SUM(a),\nrevenue,Tableau,rev_t,SUM(b),desc\n\n')
        self.assertEqual(stats, {'created': 1, 'updated': 1, 'errors': []})
        self.assertEqual(SemanticDefinition.objects.get(source=self.source).local_formula, 'SUM(a)')

    def test_all_or_nothing_with_row_numbers(self):
        stats = import_semantic_csv(HEADER + 'revenue,Snowflake,ok,SUM(a),\nnope,Redshift,,x,\n')
        self.assertEqual(stats['created'], 0)
        self.assertEqual(stats['errors'], ['row 3: unknown governance metric "nope"; unknown source "Redshift"; local_name is empty'])
        self.assertFalse(SemanticDefinition.objects.exists())

    def test_missing_columns(self):
        self.assertIn('missing column(s): source_name', import_semantic_csv('governance_metric_name,local_name\n')['errors'][0])

    def test_export_round_trip_restores_formula_text(self):
        SemanticDefinition.objects.create(governance_metric=self.metric, source=self.source,
                                          local_name='rev', local_formula='-SUM(refunds)')
        exported = self.client.get('/export/semantic-definitions.csv').content.decode()
        self.assertIn("'-SUM(refunds)", exported)
        SemanticDefinition.objects.all().delete()
        self.assertEqual(import_semantic_csv(exported)['created'], 1)
        self.assertEqual(SemanticDefinition.objects.get().local_formula, '-SUM(refunds)')

    def test_view_permissions_and_excel_bom(self):
        upload = lambda: {'csv_file': SimpleUploadedFile('m.csv', ('﻿' + HEADER + 'revenue,Snowflake,rev,SUM(a),\n').encode())}
        self.assertEqual(self.client.post(reverse('bulk_import'), upload()).status_code, 302)  # anonymous -> login
        self.client.force_login(User.objects.create_user('viewer'))
        self.assertEqual(self.client.post(reverse('bulk_import'), upload()).status_code, 403)
        self.client.force_login(make_editor())
        resp = self.client.post(reverse('bulk_import'), upload(), follow=True)
        self.assertContains(resp, 'Imported 1 new')
