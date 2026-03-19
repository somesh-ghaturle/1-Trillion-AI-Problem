#!/usr/bin/env python3
"""
Generate dashboard data from the validation engine.
Outputs JSON that the Next.js dashboard can consume.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data_quality_validator import DataQualityValidator
from data_governance import DataGovernanceFramework
from trust_scoring import TrustScoringEngine
import pandas as pd
import numpy as np

def generate_sample_data():
    """Generate sample data mimicking Snowflake and Tableau sources."""
    np.random.seed(42)
    n_records = 1000

    # Snowflake data
    snowflake_data = pd.DataFrame({
        'customer_id': range(1, n_records + 1),
        'revenue': np.random.uniform(100, 10000, n_records).round(2),
        'order_count': np.random.randint(1, 50, n_records),
        'last_updated': pd.date_range(end=datetime.now(), periods=n_records, freq='h'),
        'region': np.random.choice(['North', 'South', 'East', 'West'], n_records),
        'status': np.random.choice(['active', 'inactive', 'pending'], n_records, p=[0.7, 0.2, 0.1])
    })

    # Tableau data - intentionally slightly different to show inconsistencies
    tableau_data = snowflake_data.copy()
    # Introduce 5% data inconsistencies
    inconsistent_idx = np.random.choice(n_records, size=int(n_records * 0.05), replace=False)
    tableau_data.loc[inconsistent_idx, 'revenue'] = tableau_data.loc[inconsistent_idx, 'revenue'] * np.random.uniform(0.95, 1.05, len(inconsistent_idx))
    # Add some missing values
    missing_idx = np.random.choice(n_records, size=int(n_records * 0.02), replace=False)
    tableau_data.loc[missing_idx, 'revenue'] = np.nan

    # Salesforce data - even more variation
    salesforce_data = snowflake_data.copy()
    inconsistent_idx = np.random.choice(n_records, size=int(n_records * 0.08), replace=False)
    salesforce_data.loc[inconsistent_idx, 'revenue'] = salesforce_data.loc[inconsistent_idx, 'revenue'] * np.random.uniform(0.9, 1.1, len(inconsistent_idx))

    return snowflake_data, tableau_data, salesforce_data

def main():
    print("🔄 Generating dashboard data...")

    # Initialize engines
    validator = DataQualityValidator()
    trust_engine = TrustScoringEngine()
    governance = DataGovernanceFramework()

    # Generate sample data
    snowflake_df, tableau_df, salesforce_df = generate_sample_data()

    # Validation config
    validation_config = {
        'required_columns': ['customer_id', 'revenue', 'order_count'],
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

    # Calculate trust scores for each system
    snowflake_trust = trust_engine.calculate_trust_score(snowflake_df)
    tableau_trust = trust_engine.calculate_trust_score(tableau_df)
    salesforce_trust = trust_engine.calculate_trust_score(salesforce_df)

    # Check cross-system consistency
    sf_tb_consistency = validator.validate_cross_system_consistency(
        snowflake_df, tableau_df,
        key_column='customer_id',
        value_columns=['revenue'],
        tolerance=0.01
    )

    sf_sales_consistency = validator.validate_cross_system_consistency(
        snowflake_df, salesforce_df,
        key_column='customer_id',
        value_columns=['revenue'],
        tolerance=0.01
    )

    # Calculate global AI readiness (average of all systems)
    global_score = round((snowflake_trust.overall_score + tableau_trust.overall_score + salesforce_trust.overall_score) / 3, 1)

    # Build dashboard data object
    dashboard_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "systemStatus": "PROTECTED" if global_score >= 60 else "AT_RISK",

        "trustScores": {
            "globalAIReadiness": {
                "score": global_score,
                "trend": round(np.random.uniform(-3, 3), 1),
                "status": get_status(global_score)
            },
            "snowflake": {
                "score": round(snowflake_trust.overall_score, 1),
                "trend": round(np.random.uniform(-2, 3), 1),
                "status": get_status(snowflake_trust.overall_score),
                "dimensions": {
                    "completeness": round(snowflake_trust.dimension_scores.get('completeness', 0) * 100, 1),
                    "accuracy": round(snowflake_trust.dimension_scores.get('accuracy', 0) * 100, 1),
                    "consistency": round(snowflake_trust.dimension_scores.get('consistency', 0) * 100, 1),
                    "timeliness": round(snowflake_trust.dimension_scores.get('timeliness', 0) * 100, 1)
                }
            },
            "tableau": {
                "score": round(tableau_trust.overall_score, 1),
                "trend": round(np.random.uniform(-6, 1), 1),
                "status": get_status(tableau_trust.overall_score),
                "dimensions": {
                    "completeness": round(tableau_trust.dimension_scores.get('completeness', 0) * 100, 1),
                    "accuracy": round(tableau_trust.dimension_scores.get('accuracy', 0) * 100, 1),
                    "consistency": round(tableau_trust.dimension_scores.get('consistency', 0) * 100, 1),
                    "timeliness": round(tableau_trust.dimension_scores.get('timeliness', 0) * 100, 1)
                }
            },
            "salesforce": {
                "score": round(salesforce_trust.overall_score, 1),
                "trend": round(np.random.uniform(-4, 2), 1),
                "status": get_status(salesforce_trust.overall_score),
                "dimensions": {
                    "completeness": round(salesforce_trust.dimension_scores.get('completeness', 0) * 100, 1),
                    "accuracy": round(salesforce_trust.dimension_scores.get('accuracy', 0) * 100, 1),
                    "consistency": round(salesforce_trust.dimension_scores.get('consistency', 0) * 100, 1),
                    "timeliness": round(salesforce_trust.dimension_scores.get('timeliness', 0) * 100, 1)
                }
            }
        },

        "dataSources": {
            "snowflake": {
                "revenue": round(snowflake_df['revenue'].sum(), 2),
                "records": len(snowflake_df),
                "status": "verified" if snowflake_trust.overall_score >= 80 else "unverified"
            },
            "tableau": {
                "revenue": round(tableau_df['revenue'].sum(), 2),
                "records": len(tableau_df),
                "status": "estimated" if tableau_trust.overall_score < 80 else "verified"
            },
            "salesforce": {
                "revenue": round(salesforce_df['revenue'].sum(), 2),
                "records": len(salesforce_df),
                "status": "closed_won" if salesforce_trust.overall_score >= 70 else "pending"
            }
        },

        "consistency": {
            "snowflake_tableau": {
                "passed": sf_tb_consistency.passed,
                "inconsistencies": sf_tb_consistency.details.get('inconsistencies', {}) if hasattr(sf_tb_consistency, 'details') and sf_tb_consistency.details else {}
            },
            "snowflake_salesforce": {
                "passed": sf_sales_consistency.passed,
                "inconsistencies": sf_sales_consistency.details.get('inconsistencies', {}) if hasattr(sf_sales_consistency, 'details') and sf_sales_consistency.details else {}
            }
        },

        "semanticLayer": {
            "sourceOfTruth": "Snowflake",
            "verifiedRevenue": round(snowflake_df['revenue'].sum(), 2),
            "definition": "SUM(transaction_amount) WHERE status = 'closed_won'"
        },

        "recommendations": [
            {
                "priority": "high" if not sf_tb_consistency.passed else "medium",
                "action": "Fix revenue inconsistencies between Snowflake and Tableau",
                "impact": "5% data mismatch affecting AI predictions"
            },
            {
                "priority": "high" if not sf_sales_consistency.passed else "medium",
                "action": "Resolve schema drift in Salesforce",
                "impact": "8% data variance detected"
            },
            {
                "priority": "medium",
                "action": "Approve new Metrics Dictionary",
                "impact": "Standardize definitions across systems"
            }
        ]
    }

    # Write to JSON file in dashboard/public
    output_path = Path(__file__).parent / "dashboard" / "public" / "dashboard-data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2, default=str)

    print(f"✅ Dashboard data written to: {output_path}")
    print(f"   Global AI Readiness: {global_score}/100")
    print(f"   Snowflake Trust: {round(snowflake_trust.overall_score, 1)}/100")
    print(f"   Tableau Trust: {round(tableau_trust.overall_score, 1)}/100")
    print(f"   Salesforce Trust: {round(salesforce_trust.overall_score, 1)}/100")

    return dashboard_data

def get_status(score):
    if score >= 90:
        return "trusted"
    elif score >= 70:
        return "warning"
    else:
        return "critical"

if __name__ == "__main__":
    main()
