"""
Example: Solving the $1 Trillion AI Problem

This example demonstrates how to use the data quality validation,
governance, and trust scoring frameworks to address data inconsistency
across enterprise systems (Snowflake, Tableau, etc.).
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data_quality_validator import (
    DataQualityValidator,
    ValidationSeverity,
    generate_validation_report
)
from data_governance import (
    GovernanceFramework,
    MetricDefinition,
    DataAsset
)
from trust_scoring import TrustScoringEngine


def create_sample_data():
    """
    Create sample datasets simulating Snowflake and Tableau data
    
    Returns:
        Tuple of (snowflake_df, tableau_df)
    """
    # Simulate Snowflake data warehouse data
    np.random.seed(42)
    n_records = 1000
    
    snowflake_data = {
        'customer_id': range(1, n_records + 1),
        'revenue': np.random.uniform(100, 10000, n_records),
        'order_count': np.random.randint(1, 50, n_records),
        'last_purchase_date': [
            datetime.now() - timedelta(days=np.random.randint(0, 365))
            for _ in range(n_records)
        ],
        'customer_segment': np.random.choice(
            ['Enterprise', 'SMB', 'Startup'],
            n_records
        ),
        'status': np.random.choice(['Active', 'Inactive'], n_records)
    }
    
    snowflake_df = pd.DataFrame(snowflake_data)
    
    # Simulate Tableau data with some inconsistencies
    # (This represents the $1T problem - same data, different values!)
    
    # Create Tableau DataFrame first
    tableau_df = snowflake_df.copy()
    
    # Introduce inconsistencies
    # 1. Different revenue values for 5% of customers
    inconsistent_indices = np.random.choice(
        n_records,
        size=int(n_records * 0.05),
        replace=False
    )
    for idx in inconsistent_indices:
        # Different calculation or data freshness
        tableau_df.loc[idx, 'revenue'] *= 1.1
    
    # 2. Missing data in Tableau (completeness issue)
    tableau_df.loc[tableau_df.index[::20], 'order_count'] = np.nan
    
    return snowflake_df, tableau_df


def example_data_quality_validation():
    """
    Example 1: Data Quality Validation
    
    Demonstrates validating data quality across multiple dimensions
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: DATA QUALITY VALIDATION")
    print("="*70)
    
    snowflake_df, tableau_df = create_sample_data()
    
    validator = DataQualityValidator()
    
    # Define validation configuration
    config = {
        'required_columns': [
            'customer_id',
            'revenue',
            'order_count',
            'customer_segment'
        ],
        'key_columns': ['customer_id'],
        'value_ranges': {
            'revenue': (0, 100000),
            'order_count': (0, 1000)
        },
        'expected_types': {
            'customer_id': 'int',
            'revenue': 'float',
            'order_count': 'int'
        }
    }
    
    # Validate Snowflake data
    print("\n--- Validating Snowflake Data ---")
    results, quality_score = validator.run_validation_suite(snowflake_df, config)
    
    report = generate_validation_report(results, quality_score)
    print(report)
    
    # Validate cross-system consistency
    print("\n--- Cross-System Consistency Check ---")
    consistency_result = validator.validate_cross_system_consistency(
        snowflake_df,
        tableau_df,
        key_column='customer_id',
        value_columns=['revenue', 'order_count'],
        tolerance=0.01
    )
    
    if not consistency_result.passed:
        print(f"⚠ WARNING: {consistency_result.message}")
        print(f"This is the $1T AI problem in action!")
        print(f"Details: {consistency_result.details}")
    else:
        print("✓ Data is consistent across systems")


def example_data_governance():
    """
    Example 2: Data Governance Framework
    
    Demonstrates establishing standardized metrics and policies
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: DATA GOVERNANCE FRAMEWORK")
    print("="*70)
    
    # Initialize governance framework
    framework = GovernanceFramework()
    
    # Register standard metrics
    framework.register_standard_metrics()
    
    # Add custom metric for our use case
    churn_risk_metric = MetricDefinition(
        name="churn_risk_score",
        description="Predictive score for customer churn risk (0-100)",
        calculation="ML_MODEL(customer_features) using XGBoost classifier",
        data_type="numeric",
        business_owner="Customer Success Team",
        technical_owner="Data Science Team",
        source_systems=["Snowflake", "ML Platform"],
        update_frequency="daily",
        tags=["ml", "customer", "predictive"]
    )
    framework.data_dictionary.register_metric(churn_risk_metric)
    
    # Register data assets
    snowflake_asset = DataAsset(
        name="customers_fact_table",
        asset_type="table",
        description="Customer transaction and demographic data",
        source_system="Snowflake",
        schema={
            "customer_id": "INTEGER",
            "revenue": "NUMERIC(10,2)",
            "order_count": "INTEGER",
            "last_purchase_date": "DATE",
            "customer_segment": "VARCHAR(50)",
            "status": "VARCHAR(20)"
        },
        owner="Data Engineering Team",
        classification="internal",
        retention_period="7 years"
    )
    framework.data_dictionary.register_asset(snowflake_asset)
    
    # Add data lineage
    framework.lineage_tracker.add_lineage(
        source="customers_fact_table",
        target="customer_analytics_dashboard",
        transformation="Aggregation by segment and time period"
    )
    
    framework.lineage_tracker.add_lineage(
        source="customer_analytics_dashboard",
        target="churn_prediction_model",
        transformation="Feature engineering and ML model training"
    )
    
    # Generate governance report
    report = framework.generate_governance_report()
    print(report)
    
    # Show metric definitions
    print("\n--- Registered Metrics ---")
    for name, metric in framework.data_dictionary.metrics.items():
        print(f"\n{name}:")
        print(f"  Description: {metric.description}")
        print(f"  Calculation: {metric.calculation}")
        print(f"  Source Systems: {', '.join(metric.source_systems)}")
    
    # Show lineage
    print("\n--- Data Lineage ---")
    lineage = framework.lineage_tracker.get_full_lineage("customer_analytics_dashboard")
    print(f"Asset: {lineage['asset']}")
    print(f"Upstream: {lineage['upstream']}")
    print(f"Downstream: {lineage['downstream']}")


def example_trust_scoring():
    """
    Example 3: Trust Scoring Engine
    
    Demonstrates calculating trust scores for AI/ML consumption
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: TRUST SCORING ENGINE")
    print("="*70)
    
    snowflake_df, tableau_df = create_sample_data()
    
    engine = TrustScoringEngine()
    
    # Configure trust scoring
    config = {
        'critical_columns': ['customer_id', 'revenue', 'order_count'],
        'value_ranges': {
            'revenue': (0, 100000),
            'order_count': (0, 1000)
        },
        'timestamp_column': 'last_purchase_date',
        'max_age_days': 90,
        'key_columns': ['customer_id'],
        'business_rules': {
            'revenue_positive': {
                'type': 'range',
                'column': 'revenue',
                'min': 0,
                'max': 1000000
            },
            'valid_segment': {
                'type': 'allowed_values',
                'column': 'customer_segment',
                'values': ['Enterprise', 'SMB', 'Startup']
            }
        }
    }
    
    # Calculate trust score for Snowflake data
    print("\n--- Trust Score: Snowflake Data ---")
    snowflake_trust = engine.calculate_trust_score(snowflake_df, config)
    report = engine.generate_trust_report(snowflake_trust)
    print(report)
    
    # Calculate trust score for Tableau data
    print("\n--- Trust Score: Tableau Data ---")
    tableau_trust = engine.calculate_trust_score(tableau_df, config)
    report = engine.generate_trust_report(tableau_trust)
    print(report)
    
    # Compare scores
    print("\n--- Trust Score Comparison ---")
    print(f"Snowflake Score: {snowflake_trust.overall_score:.2f}/100 ({snowflake_trust.trust_level.value})")
    print(f"Tableau Score: {tableau_trust.overall_score:.2f}/100 ({tableau_trust.trust_level.value})")
    
    score_diff = abs(snowflake_trust.overall_score - tableau_trust.overall_score)
    if score_diff > 5:
        print(f"\n⚠ WARNING: Significant trust score difference ({score_diff:.2f} points)")
        print("This indicates data quality issues that could impact AI model reliability!")
    
    # Show dimension comparison
    print("\n--- Dimension Comparison ---")
    print(f"{'Dimension':<15} {'Snowflake':<12} {'Tableau':<12} {'Difference'}")
    print("-" * 55)
    for dim in snowflake_trust.dimensions.keys():
        sf_score = snowflake_trust.dimensions[dim]
        tb_score = tableau_trust.dimensions[dim]
        diff = sf_score - tb_score
        print(f"{dim:<15} {sf_score:>6.2f}%     {tb_score:>6.2f}%     {diff:>+6.2f}%")


def example_integrated_solution():
    """
    Example 4: Integrated Solution
    
    Demonstrates the complete workflow combining all components
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: INTEGRATED SOLUTION")
    print("="*70)
    print("\nThis example shows the complete solution to the $1T AI problem:")
    print("1. Validate data quality")
    print("2. Check cross-system consistency")
    print("3. Apply governance policies")
    print("4. Calculate trust scores")
    print("5. Make AI/ML readiness decision")
    
    # Step 1: Load data
    print("\n[Step 1] Loading data from Snowflake and Tableau...")
    snowflake_df, tableau_df = create_sample_data()
    print(f"✓ Loaded {len(snowflake_df)} records from each system")
    
    # Step 2: Initialize components
    print("\n[Step 2] Initializing governance and validation frameworks...")
    framework = GovernanceFramework()
    framework.register_standard_metrics()
    validator = DataQualityValidator()
    trust_engine = TrustScoringEngine()
    print("✓ Frameworks initialized")
    
    # Step 3: Validate data quality
    print("\n[Step 3] Validating data quality...")
    config = {
        'required_columns': ['customer_id', 'revenue', 'order_count'],
        'key_columns': ['customer_id'],
        'value_ranges': {'revenue': (0, 100000)},
        'expected_types': {'customer_id': 'int', 'revenue': 'float'}
    }
    
    results, quality_score = validator.run_validation_suite(snowflake_df, config)
    print(f"✓ Quality Score: {quality_score}/100")
    
    # Step 4: Check cross-system consistency
    print("\n[Step 4] Checking cross-system consistency...")
    consistency = validator.validate_cross_system_consistency(
        snowflake_df,
        tableau_df,
        key_column='customer_id',
        value_columns=['revenue', 'order_count'],
        tolerance=0.01
    )
    
    if consistency.passed:
        print("✓ Data is consistent across systems")
    else:
        print(f"⚠ Inconsistencies detected: {consistency.message}")
    
    # Step 5: Calculate trust scores
    print("\n[Step 5] Calculating trust scores...")
    trust_config = {
        'critical_columns': ['customer_id', 'revenue'],
        'key_columns': ['customer_id'],
        'timestamp_column': 'last_purchase_date'
    }
    
    trust_score = trust_engine.calculate_trust_score(snowflake_df, trust_config)
    print(f"✓ Trust Score: {trust_score.overall_score}/100 ({trust_score.trust_level.value})")
    
    # Step 6: Make decision
    print("\n[Step 6] AI/ML Readiness Decision...")
    print("-" * 70)
    
    if trust_score.overall_score >= 90 and consistency.passed:
        print("✓ APPROVED: Data is ready for AI/ML model training")
        print("  - High trust score")
        print("  - Cross-system consistency verified")
        print("  - Proceed with model development")
    elif trust_score.overall_score >= 75:
        print("⚠ CONDITIONAL: Data quality is acceptable with caveats")
        print("  - Monitor model performance closely")
        print("  - Address identified issues")
        print("  - Consider additional validation")
    else:
        print("✗ REJECTED: Data quality insufficient for AI/ML")
        print("  - Remediate data quality issues")
        print("  - Improve cross-system consistency")
        print("  - Re-validate before proceeding")
    
    print("\n" + "="*70)
    print("SOLUTION SUMMARY")
    print("="*70)
    print("\nThe integrated solution addresses the $1T AI problem by:")
    print("• Validating data quality across multiple dimensions")
    print("• Ensuring consistency between systems (Snowflake, Tableau, etc.)")
    print("• Enforcing governance policies and standardized metrics")
    print("• Providing trust scores to quantify data reliability")
    print("• Enabling confident AI/ML model development")
    print("\nResult: Reliable AI predictions, restored trust in insights")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SOLVING THE $1 TRILLION AI PROBLEM")
    print("="*70)
    print("\nProblem: AI models trained on inconsistent data from multiple")
    print("systems (Snowflake, Tableau, etc.) produce unreliable predictions")
    print("and destroy trust in AI-generated insights.")
    print("\nSolution: Comprehensive data quality, governance, and trust")
    print("scoring framework to ensure data reliability.")
    
    try:
        # Run all examples
        example_data_quality_validation()
        example_data_governance()
        example_trust_scoring()
        example_integrated_solution()
        
        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*70)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
