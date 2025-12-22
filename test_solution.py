"""
Unit tests for the $1 Trillion AI Problem solution

Tests the core functionality of data quality validation,
governance, and trust scoring.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data_quality_validator import (
    DataQualityValidator,
    ValidationSeverity,
    ValidationResult
)
from data_governance import (
    GovernanceFramework,
    MetricDefinition,
    DataAsset
)
from trust_scoring import (
    TrustScoringEngine,
    TrustLevel
)


class TestDataQualityValidator(unittest.TestCase):
    """Test cases for DataQualityValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = DataQualityValidator()
        self.sample_df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'value': [100, 200, 300, 400, 500],
            'category': ['A', 'B', 'A', 'C', 'B']
        })
    
    def test_completeness_validation_pass(self):
        """Test completeness validation with complete data"""
        result = self.validator.validate_completeness(
            self.sample_df,
            ['id', 'value', 'category'],
            threshold=0.95
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.rule_name, 'completeness')
    
    def test_completeness_validation_fail_missing_columns(self):
        """Test completeness validation with missing columns"""
        result = self.validator.validate_completeness(
            self.sample_df,
            ['id', 'value', 'missing_column'],
            threshold=0.95
        )
        self.assertFalse(result.passed)
        self.assertIn('missing_column', result.details['missing_columns'])
    
    def test_uniqueness_validation_pass(self):
        """Test uniqueness validation with unique data"""
        result = self.validator.validate_uniqueness(
            self.sample_df,
            ['id']
        )
        self.assertTrue(result.passed)
    
    def test_uniqueness_validation_fail(self):
        """Test uniqueness validation with duplicates"""
        df_with_dupes = pd.DataFrame({
            'id': [1, 1, 2, 3, 4],
            'value': [100, 100, 200, 300, 400]
        })
        result = self.validator.validate_uniqueness(df_with_dupes, ['id'])
        self.assertFalse(result.passed)
        self.assertEqual(result.details['duplicate_count'], 2)
    
    def test_value_ranges_validation_pass(self):
        """Test value ranges validation with valid data"""
        result = self.validator.validate_value_ranges(
            self.sample_df,
            {'value': (0, 1000)}
        )
        self.assertTrue(result.passed)
    
    def test_value_ranges_validation_fail(self):
        """Test value ranges validation with out-of-range data"""
        df_invalid = pd.DataFrame({
            'value': [100, 200, 1500, 400, 500]  # 1500 is out of range
        })
        result = self.validator.validate_value_ranges(
            df_invalid,
            {'value': (0, 1000)}
        )
        self.assertFalse(result.passed)
        self.assertIn('value', result.details['violations'])
    
    def test_cross_system_consistency_pass(self):
        """Test cross-system consistency with identical data"""
        df1 = pd.DataFrame({
            'id': [1, 2, 3],
            'revenue': [1000, 2000, 3000]
        })
        df2 = pd.DataFrame({
            'id': [1, 2, 3],
            'revenue': [1000, 2000, 3000]
        })
        
        result = self.validator.validate_cross_system_consistency(
            df1, df2, 'id', ['revenue']
        )
        self.assertTrue(result.passed)
    
    def test_cross_system_consistency_fail(self):
        """Test cross-system consistency with inconsistent data"""
        df1 = pd.DataFrame({
            'id': [1, 2, 3],
            'revenue': [1000, 2000, 3000]
        })
        df2 = pd.DataFrame({
            'id': [1, 2, 3],
            'revenue': [1100, 2000, 3000]  # Different value for id=1
        })
        
        result = self.validator.validate_cross_system_consistency(
            df1, df2, 'id', ['revenue'], tolerance=0.01
        )
        self.assertFalse(result.passed)
        self.assertIn('revenue', result.details['inconsistencies'])
    
    def test_data_quality_score_all_pass(self):
        """Test quality score with all validations passing"""
        results = [
            ValidationResult('test1', True, ValidationSeverity.INFO, 'Pass'),
            ValidationResult('test2', True, ValidationSeverity.INFO, 'Pass')
        ]
        score = self.validator.compute_data_quality_score(results)
        self.assertEqual(score, 100.0)
    
    def test_data_quality_score_with_failures(self):
        """Test quality score with some failures"""
        results = [
            ValidationResult('test1', False, ValidationSeverity.CRITICAL, 'Fail'),
            ValidationResult('test2', True, ValidationSeverity.INFO, 'Pass')
        ]
        score = self.validator.compute_data_quality_score(results)
        self.assertLess(score, 100.0)


class TestGovernanceFramework(unittest.TestCase):
    """Test cases for GovernanceFramework"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.framework = GovernanceFramework()
    
    def test_register_metric(self):
        """Test registering a metric definition"""
        metric = MetricDefinition(
            name='test_metric',
            description='Test metric',
            calculation='SUM(test)',
            data_type='numeric',
            business_owner='Test Owner',
            technical_owner='Test Tech',
            source_systems=['System1'],
            update_frequency='daily'
        )
        
        self.framework.data_dictionary.register_metric(metric)
        retrieved = self.framework.data_dictionary.get_metric('test_metric')
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, 'test_metric')
        self.assertEqual(retrieved.description, 'Test metric')
    
    def test_register_asset(self):
        """Test registering a data asset"""
        asset = DataAsset(
            name='test_table',
            asset_type='table',
            description='Test table',
            source_system='TestDB',
            schema={'col1': 'INT', 'col2': 'VARCHAR'},
            owner='Test Owner',
            classification='internal',
            retention_period='1 year'
        )
        
        self.framework.data_dictionary.register_asset(asset)
        retrieved = self.framework.data_dictionary.get_asset('test_table')
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, 'test_table')
    
    def test_data_lineage(self):
        """Test data lineage tracking"""
        self.framework.lineage_tracker.add_lineage(
            source='source_table',
            target='target_table',
            transformation='Test transformation'
        )
        
        downstream = self.framework.lineage_tracker.get_downstream('source_table')
        upstream = self.framework.lineage_tracker.get_upstream('target_table')
        
        self.assertIn('target_table', downstream)
        self.assertIn('source_table', upstream)
    
    def test_default_policies(self):
        """Test that default policies are initialized"""
        policies = self.framework.policy_engine.list_policies()
        self.assertGreater(len(policies), 0)
        
        # Check for specific default policies
        policy_names = [p['name'] for p in policies]
        self.assertIn('data_quality_standards', policy_names)
        self.assertIn('data_security', policy_names)
    
    def test_register_standard_metrics(self):
        """Test registering standard metrics"""
        self.framework.register_standard_metrics()
        
        # Check that standard metrics are registered
        revenue = self.framework.data_dictionary.get_metric('revenue')
        self.assertIsNotNone(revenue)
        self.assertEqual(revenue.name, 'revenue')


class TestTrustScoringEngine(unittest.TestCase):
    """Test cases for TrustScoringEngine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = TrustScoringEngine()
        self.sample_df = pd.DataFrame({
            'id': range(1, 101),
            'value': np.random.uniform(100, 1000, 100),
            'category': np.random.choice(['A', 'B', 'C'], 100),
            'timestamp': [
                datetime.now() - timedelta(days=i)
                for i in range(100)
            ]
        })
    
    def test_score_completeness_full(self):
        """Test completeness scoring with complete data"""
        score = self.engine.score_completeness(self.sample_df)
        self.assertEqual(score, 100.0)
    
    def test_score_completeness_partial(self):
        """Test completeness scoring with missing data"""
        df_partial = self.sample_df.copy()
        df_partial.loc[0:9, 'value'] = np.nan
        
        score = self.engine.score_completeness(df_partial)
        self.assertLess(score, 100.0)
        self.assertGreater(score, 0.0)
    
    def test_score_uniqueness_full(self):
        """Test uniqueness scoring with unique data"""
        score = self.engine.score_uniqueness(self.sample_df, ['id'])
        self.assertEqual(score, 100.0)
    
    def test_score_uniqueness_with_dupes(self):
        """Test uniqueness scoring with duplicates"""
        df_dupes = pd.DataFrame({
            'id': [1, 1, 2, 3, 4],
            'value': [100, 100, 200, 300, 400]
        })
        score = self.engine.score_uniqueness(df_dupes, ['id'])
        self.assertLess(score, 100.0)
    
    def test_calculate_trust_score(self):
        """Test calculating comprehensive trust score"""
        config = {
            'critical_columns': ['id', 'value'],
            'key_columns': ['id'],
            'timestamp_column': 'timestamp',
            'max_age_days': 7
        }
        
        trust_score = self.engine.calculate_trust_score(self.sample_df, config)
        
        self.assertIsNotNone(trust_score)
        self.assertGreaterEqual(trust_score.overall_score, 0)
        self.assertLessEqual(trust_score.overall_score, 100)
        self.assertIn(trust_score.trust_level, list(TrustLevel))
    
    def test_trust_level_assignment(self):
        """Test trust level assignment based on score"""
        # Create perfect data
        df_perfect = pd.DataFrame({
            'id': range(1, 11),
            'value': range(100, 110),
            'timestamp': [datetime.now() for _ in range(10)]
        })
        
        config = {
            'critical_columns': ['id', 'value'],
            'key_columns': ['id'],
            'timestamp_column': 'timestamp'
        }
        
        trust_score = self.engine.calculate_trust_score(df_perfect, config)
        
        # Should get high trust score for perfect data
        self.assertGreaterEqual(trust_score.overall_score, 60)
    
    def test_set_custom_weights(self):
        """Test setting custom dimension weights"""
        custom_weights = {
            "completeness": 0.30,
            "accuracy": 0.30,
            "consistency": 0.20,
            "timeliness": 0.10,
            "validity": 0.05,
            "uniqueness": 0.05
        }
        
        self.engine.set_weights(custom_weights)
        self.assertEqual(self.engine.dimension_weights, custom_weights)
    
    def test_set_invalid_weights(self):
        """Test that invalid weights raise an error"""
        invalid_weights = {
            "completeness": 0.50,
            "accuracy": 0.30,
            # Total doesn't sum to 1.0
        }
        
        with self.assertRaises(ValueError):
            self.engine.set_weights(invalid_weights)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete solution"""
    
    def test_complete_workflow(self):
        """Test the complete workflow from validation to trust scoring"""
        # Create test data
        df = pd.DataFrame({
            'customer_id': range(1, 51),
            'revenue': np.random.uniform(100, 1000, 50),
            'order_count': np.random.randint(1, 20, 50),
            'last_purchase': [
                datetime.now() - timedelta(days=i)
                for i in range(50)
            ]
        })
        
        # Step 1: Initialize components
        validator = DataQualityValidator()
        governance = GovernanceFramework()
        trust_engine = TrustScoringEngine()
        
        # Step 2: Validate data quality
        validation_config = {
            'required_columns': ['customer_id', 'revenue'],
            'key_columns': ['customer_id'],
            'value_ranges': {'revenue': (0, 10000)}
        }
        
        results, quality_score = validator.run_validation_suite(df, validation_config)
        self.assertGreaterEqual(quality_score, 0)
        self.assertLessEqual(quality_score, 100)
        
        # Step 3: Register governance metadata
        governance.register_standard_metrics()
        self.assertGreater(len(governance.data_dictionary.metrics), 0)
        
        # Step 4: Calculate trust score
        trust_config = {
            'critical_columns': ['customer_id', 'revenue'],
            'key_columns': ['customer_id'],
            'timestamp_column': 'last_purchase'
        }
        
        trust_score = trust_engine.calculate_trust_score(df, trust_config)
        self.assertIsNotNone(trust_score)
        self.assertGreaterEqual(trust_score.overall_score, 0)
        
        # Step 5: Verify trust level is assigned
        self.assertIn(trust_score.trust_level, list(TrustLevel))


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDataQualityValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestGovernanceFramework))
    suite.addTests(loader.loadTestsFromTestCase(TestTrustScoringEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
