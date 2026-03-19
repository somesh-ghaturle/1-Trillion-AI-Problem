from django.test import TestCase
from core.models import DataSource, ValidationResult, TrustScore, GovernanceMetric


class DataSourceModelTest(TestCase):
    def test_create_data_source(self):
        source = DataSource.objects.create(
            name='Test Snowflake',
            source_type='snowflake',
            description='Test warehouse'
        )
        self.assertEqual(str(source), 'Test Snowflake (snowflake)')
        self.assertTrue(source.is_active)
        self.assertIsNotNone(source.created_at)

    def test_source_types(self):
        for code, _ in DataSource.SOURCE_TYPES:
            source = DataSource.objects.create(name=f'Source {code}', source_type=code)
            self.assertEqual(source.source_type, code)


class ValidationResultModelTest(TestCase):
    def setUp(self):
        self.source = DataSource.objects.create(name='Test Source')

    def test_create_validation(self):
        v = ValidationResult.objects.create(
            source=self.source,
            passed=True,
            quality_score=85.5,
            total_rules=10,
            passed_rules=9,
            failed_rules=1
        )
        self.assertTrue(v.passed)
        self.assertEqual(v.quality_score, 85.5)
        self.assertIn('Test Source', str(v))

    def test_ordering(self):
        v1 = ValidationResult.objects.create(source=self.source, quality_score=80)
        v2 = ValidationResult.objects.create(source=self.source, quality_score=90)
        results = list(ValidationResult.objects.all())
        self.assertEqual(results[0].pk, v2.pk)


class TrustScoreModelTest(TestCase):
    def setUp(self):
        self.source = DataSource.objects.create(name='Test Source')

    def test_create_trust_score(self):
        ts = TrustScore.objects.create(
            source=self.source,
            overall_score=82.5,
            trust_level='high',
            completeness_score=90,
            accuracy_score=85,
            consistency_score=78,
            timeliness_score=80,
            validity_score=75,
            uniqueness_score=95
        )
        self.assertEqual(ts.trust_level, 'high')
        self.assertIn('82.5', str(ts))


class GovernanceMetricModelTest(TestCase):
    def test_create_metric(self):
        m = GovernanceMetric.objects.create(
            name='total_revenue',
            display_name='Total Revenue',
            description='Sum of all revenue',
            data_type='numeric'
        )
        self.assertEqual(str(m), 'Total Revenue')
        self.assertTrue(m.is_active)
