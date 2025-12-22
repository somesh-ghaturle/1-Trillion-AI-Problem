"""
Data Quality Validation Framework

This module provides comprehensive data quality validation to address
the $1 trillion AI problem caused by inconsistent data across systems.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import hashlib


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationResult:
    """Container for validation results"""
    
    def __init__(
        self,
        rule_name: str,
        passed: bool,
        severity: ValidationSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.rule_name = rule_name
        self.passed = passed
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "rule_name": self.rule_name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class DataQualityValidator:
    """
    Main data quality validation engine
    
    Validates data quality across multiple dimensions:
    - Completeness
    - Consistency
    - Accuracy
    - Uniqueness
    - Timeliness
    """
    
    def __init__(self):
        self.validation_results: List[ValidationResult] = []
    
    def validate_completeness(
        self,
        df: pd.DataFrame,
        required_columns: List[str],
        threshold: float = 0.95
    ) -> ValidationResult:
        """
        Validate data completeness
        
        Args:
            df: DataFrame to validate
            required_columns: Columns that must be present
            threshold: Minimum completeness ratio (0-1)
        
        Returns:
            ValidationResult
        """
        missing_cols = set(required_columns) - set(df.columns)
        
        if missing_cols:
            return ValidationResult(
                rule_name="completeness_columns",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Missing required columns: {missing_cols}",
                details={"missing_columns": list(missing_cols)}
            )
        
        # Check null values
        completeness_scores = {}
        failed_columns = []
        
        for col in required_columns:
            non_null_ratio = df[col].notna().sum() / len(df)
            completeness_scores[col] = non_null_ratio
            
            if non_null_ratio < threshold:
                failed_columns.append(col)
        
        if failed_columns:
            return ValidationResult(
                rule_name="completeness_nulls",
                passed=False,
                severity=ValidationSeverity.HIGH,
                message=f"Columns below completeness threshold: {failed_columns}",
                details={
                    "completeness_scores": completeness_scores,
                    "failed_columns": failed_columns,
                    "threshold": threshold
                }
            )
        
        return ValidationResult(
            rule_name="completeness",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="All completeness checks passed",
            details={"completeness_scores": completeness_scores}
        )
    
    def validate_uniqueness(
        self,
        df: pd.DataFrame,
        key_columns: List[str]
    ) -> ValidationResult:
        """
        Validate uniqueness constraints
        
        Args:
            df: DataFrame to validate
            key_columns: Columns that should be unique together
        
        Returns:
            ValidationResult
        """
        duplicates = df.duplicated(subset=key_columns, keep=False)
        duplicate_count = duplicates.sum()
        
        if duplicate_count > 0:
            duplicate_rows = df[duplicates]
            
            return ValidationResult(
                rule_name="uniqueness",
                passed=False,
                severity=ValidationSeverity.HIGH,
                message=f"Found {duplicate_count} duplicate rows",
                details={
                    "duplicate_count": duplicate_count,
                    "duplicate_percentage": (duplicate_count / len(df)) * 100,
                    "key_columns": key_columns,
                    "sample_duplicates": duplicate_rows.head(5).to_dict('records')
                }
            )
        
        return ValidationResult(
            rule_name="uniqueness",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="No duplicates found",
            details={"key_columns": key_columns}
        )
    
    def validate_value_ranges(
        self,
        df: pd.DataFrame,
        column_ranges: Dict[str, Tuple[Any, Any]]
    ) -> ValidationResult:
        """
        Validate values are within expected ranges
        
        Args:
            df: DataFrame to validate
            column_ranges: Dict mapping column names to (min, max) tuples
        
        Returns:
            ValidationResult
        """
        violations = {}
        
        for col, (min_val, max_val) in column_ranges.items():
            if col not in df.columns:
                continue
            
            out_of_range = df[
                (df[col] < min_val) | (df[col] > max_val)
            ]
            
            if len(out_of_range) > 0:
                violations[col] = {
                    "count": len(out_of_range),
                    "percentage": (len(out_of_range) / len(df)) * 100,
                    "expected_range": (min_val, max_val),
                    "actual_min": df[col].min(),
                    "actual_max": df[col].max()
                }
        
        if violations:
            return ValidationResult(
                rule_name="value_ranges",
                passed=False,
                severity=ValidationSeverity.MEDIUM,
                message=f"Value range violations in {len(violations)} columns",
                details={"violations": violations}
            )
        
        return ValidationResult(
            rule_name="value_ranges",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="All values within expected ranges",
            details={"checked_columns": list(column_ranges.keys())}
        )
    
    def validate_data_types(
        self,
        df: pd.DataFrame,
        expected_types: Dict[str, str]
    ) -> ValidationResult:
        """
        Validate data types match expectations
        
        Args:
            df: DataFrame to validate
            expected_types: Dict mapping column names to expected types
        
        Returns:
            ValidationResult
        """
        type_mismatches = {}
        
        for col, expected_type in expected_types.items():
            if col not in df.columns:
                continue
            
            actual_type = str(df[col].dtype)
            
            # Flexible type matching
            if expected_type in ['int', 'integer'] and 'int' not in actual_type:
                type_mismatches[col] = {
                    "expected": expected_type,
                    "actual": actual_type
                }
            elif expected_type in ['float', 'numeric'] and 'float' not in actual_type:
                type_mismatches[col] = {
                    "expected": expected_type,
                    "actual": actual_type
                }
            elif expected_type in ['str', 'string', 'object'] and actual_type != 'object':
                type_mismatches[col] = {
                    "expected": expected_type,
                    "actual": actual_type
                }
        
        if type_mismatches:
            return ValidationResult(
                rule_name="data_types",
                passed=False,
                severity=ValidationSeverity.MEDIUM,
                message=f"Data type mismatches in {len(type_mismatches)} columns",
                details={"mismatches": type_mismatches}
            )
        
        return ValidationResult(
            rule_name="data_types",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="All data types match expectations",
            details={"checked_columns": list(expected_types.keys())}
        )
    
    def validate_cross_system_consistency(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        key_column: str,
        value_columns: List[str],
        tolerance: float = 0.01
    ) -> ValidationResult:
        """
        Validate consistency between two data sources
        
        This is critical for solving the $1T AI problem - ensuring
        data is consistent across systems like Snowflake and Tableau.
        
        Args:
            df1: First DataFrame (e.g., from Snowflake)
            df2: Second DataFrame (e.g., from Tableau)
            key_column: Column to join on
            value_columns: Columns to compare
            tolerance: Acceptable difference for numeric values
        
        Returns:
            ValidationResult
        """
        # Merge dataframes
        merged = pd.merge(
            df1[[key_column] + value_columns],
            df2[[key_column] + value_columns],
            on=key_column,
            suffixes=('_system1', '_system2'),
            how='inner'
        )
        
        inconsistencies = {}
        
        for col in value_columns:
            col1 = f"{col}_system1"
            col2 = f"{col}_system2"
            
            if col1 not in merged.columns or col2 not in merged.columns:
                continue
            
            # For numeric columns, check within tolerance
            if pd.api.types.is_numeric_dtype(merged[col1]):
                diff = abs(merged[col1] - merged[col2])
                inconsistent = diff > tolerance
            else:
                # For non-numeric, check exact match
                inconsistent = merged[col1] != merged[col2]
            
            inconsistent_count = inconsistent.sum()
            
            if inconsistent_count > 0:
                inconsistencies[col] = {
                    "count": inconsistent_count,
                    "percentage": (inconsistent_count / len(merged)) * 100,
                    "sample_differences": merged[inconsistent].head(5)[[
                        key_column, col1, col2
                    ]].to_dict('records')
                }
        
        if inconsistencies:
            return ValidationResult(
                rule_name="cross_system_consistency",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Found inconsistencies in {len(inconsistencies)} columns across systems",
                details={
                    "inconsistencies": {
                        k: {
                            "count": v["count"],
                            "percentage": v["percentage"]
                        } for k, v in inconsistencies.items()
                    },
                    "total_records_compared": len(merged)
                }
            )
        
        return ValidationResult(
            rule_name="cross_system_consistency",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="Data is consistent across systems",
            details={
                "records_compared": len(merged),
                "columns_checked": value_columns
            }
        )
    
    def compute_data_quality_score(
        self,
        results: Optional[List[ValidationResult]] = None
    ) -> float:
        """
        Compute overall data quality score (0-100)
        
        Args:
            results: List of validation results (uses self.validation_results if None)
        
        Returns:
            Quality score between 0 and 100
        """
        results = results or self.validation_results
        
        if not results:
            return 0.0
        
        # Weight by severity
        severity_weights = {
            ValidationSeverity.CRITICAL: 10,
            ValidationSeverity.HIGH: 5,
            ValidationSeverity.MEDIUM: 3,
            ValidationSeverity.LOW: 1,
            ValidationSeverity.INFO: 0
        }
        
        total_weight = 0
        penalty = 0
        
        for result in results:
            weight = severity_weights[result.severity]
            total_weight += weight
            
            if not result.passed:
                penalty += weight
        
        if total_weight == 0:
            return 100.0
        
        score = max(0, 100 * (1 - penalty / total_weight))
        return round(score, 2)
    
    def run_validation_suite(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Tuple[List[ValidationResult], float]:
        """
        Run complete validation suite
        
        Args:
            df: DataFrame to validate
            config: Validation configuration
        
        Returns:
            Tuple of (validation results, quality score)
        """
        results = []
        
        # Completeness check
        if 'required_columns' in config:
            result = self.validate_completeness(
                df,
                config['required_columns'],
                config.get('completeness_threshold', 0.95)
            )
            results.append(result)
        
        # Uniqueness check
        if 'key_columns' in config:
            result = self.validate_uniqueness(df, config['key_columns'])
            results.append(result)
        
        # Value ranges check
        if 'value_ranges' in config:
            result = self.validate_value_ranges(df, config['value_ranges'])
            results.append(result)
        
        # Data types check
        if 'expected_types' in config:
            result = self.validate_data_types(df, config['expected_types'])
            results.append(result)
        
        self.validation_results = results
        score = self.compute_data_quality_score(results)
        
        return results, score


def generate_validation_report(
    results: List[ValidationResult],
    quality_score: float
) -> str:
    """
    Generate human-readable validation report
    
    Args:
        results: List of validation results
        quality_score: Overall quality score
    
    Returns:
        Formatted report string
    """
    report_lines = [
        "=" * 70,
        "DATA QUALITY VALIDATION REPORT",
        "=" * 70,
        f"\nOverall Quality Score: {quality_score}/100",
        f"Timestamp: {datetime.utcnow().isoformat()}",
        f"\nTotal Checks: {len(results)}",
        f"Passed: {sum(1 for r in results if r.passed)}",
        f"Failed: {sum(1 for r in results if not r.passed)}",
        "\n" + "=" * 70,
        "DETAILED RESULTS",
        "=" * 70,
    ]
    
    for result in results:
        status = "✓ PASSED" if result.passed else "✗ FAILED"
        report_lines.extend([
            f"\n[{result.severity.value.upper()}] {result.rule_name}: {status}",
            f"Message: {result.message}"
        ])
        
        if result.details:
            report_lines.append("Details:")
            for key, value in result.details.items():
                if isinstance(value, (list, dict)) and len(str(value)) > 100:
                    report_lines.append(f"  {key}: <detailed data>")
                else:
                    report_lines.append(f"  {key}: {value}")
    
    report_lines.append("\n" + "=" * 70)
    
    return "\n".join(report_lines)
