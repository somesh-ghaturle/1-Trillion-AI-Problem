"""
Trust Scoring Engine

Quantifies data reliability for AI/ML model consumption.
Addresses the core issue of the $1T AI problem by providing
confidence scores for data used in AI models.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class TrustLevel(Enum):
    """Trust level categories"""
    VERIFIED = "verified"  # 90-100%
    HIGH = "high"  # 75-89%
    MEDIUM = "medium"  # 60-74%
    LOW = "low"  # 40-59%
    UNTRUSTED = "untrusted"  # 0-39%


@dataclass
class TrustScore:
    """
    Multi-dimensional trust score for a dataset
    """
    overall_score: float  # 0-100
    dimensions: Dict[str, float]  # Individual dimension scores
    trust_level: TrustLevel
    issues: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "trust_level": self.trust_level.value,
            "issues": self.issues,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class TrustScoringEngine:
    """
    Calculate trust scores for datasets used in AI/ML
    
    Trust dimensions:
    1. Completeness - How complete is the data?
    2. Accuracy - How accurate are the values?
    3. Consistency - Is data consistent internally and across systems?
    4. Timeliness - How fresh is the data?
    5. Validity - Do values conform to business rules?
    6. Uniqueness - Are there duplicate records?
    """
    
    def __init__(self):
        self.dimension_weights = {
            "completeness": 0.20,
            "accuracy": 0.25,
            "consistency": 0.25,
            "timeliness": 0.15,
            "validity": 0.10,
            "uniqueness": 0.05
        }
    
    def set_weights(self, weights: Dict[str, float]) -> None:
        """
        Set custom weights for trust dimensions
        
        Args:
            weights: Dictionary of dimension weights (must sum to 1.0)
        """
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        self.dimension_weights = weights
    
    def score_completeness(
        self,
        df: pd.DataFrame,
        critical_columns: Optional[List[str]] = None
    ) -> float:
        """
        Score data completeness
        
        Args:
            df: DataFrame to score
            critical_columns: Optional list of critical columns
        
        Returns:
            Completeness score (0-100)
        """
        if len(df) == 0:
            return 0.0
        
        columns_to_check = critical_columns or df.columns.tolist()
        
        completeness_scores = []
        for col in columns_to_check:
            if col in df.columns:
                non_null_ratio = df[col].notna().sum() / len(df)
                completeness_scores.append(non_null_ratio * 100)
        
        if not completeness_scores:
            return 0.0
        
        return np.mean(completeness_scores)
    
    def score_accuracy(
        self,
        df: pd.DataFrame,
        value_ranges: Optional[Dict[str, tuple]] = None,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Score data accuracy
        
        Args:
            df: DataFrame to score
            value_ranges: Expected value ranges for columns
            validation_results: Results from data quality validation
        
        Returns:
            Accuracy score (0-100)
        """
        if validation_results:
            # Use validation results if available
            passed_checks = validation_results.get('passed_checks', 0)
            total_checks = validation_results.get('total_checks', 1)
            return (passed_checks / total_checks) * 100
        
        if not value_ranges or len(df) == 0:
            return 75.0  # Default moderate score if no validation data
        
        # Check values against expected ranges
        in_range_scores = []
        for col, (min_val, max_val) in value_ranges.items():
            if col in df.columns:
                in_range = df[col].between(min_val, max_val, inclusive='both')
                in_range_scores.append(in_range.sum() / len(df) * 100)
        
        if not in_range_scores:
            return 75.0
        
        return np.mean(in_range_scores)
    
    def score_consistency(
        self,
        df: pd.DataFrame,
        reference_df: Optional[pd.DataFrame] = None,
        key_column: Optional[str] = None,
        value_columns: Optional[List[str]] = None
    ) -> float:
        """
        Score data consistency
        
        Args:
            df: DataFrame to score
            reference_df: Reference DataFrame for cross-system comparison
            key_column: Column to join on
            value_columns: Columns to compare
        
        Returns:
            Consistency score (0-100)
        """
        if reference_df is None or key_column is None or value_columns is None:
            # Internal consistency only
            # Check for standard deviations and outliers
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return 80.0  # Default if no numeric columns
            
            consistency_scores = []
            for col in numeric_cols:
                values = df[col].dropna()
                if len(values) > 1:
                    # Calculate coefficient of variation
                    mean_val = values.mean()
                    std_val = values.std()
                    
                    if mean_val != 0:
                        cv = abs(std_val / mean_val)
                        # Lower CV = higher consistency
                        score = max(0, 100 - (cv * 100))
                        consistency_scores.append(min(100, score))
            
            return np.mean(consistency_scores) if consistency_scores else 80.0
        
        # Cross-system consistency check
        merged = pd.merge(
            df[[key_column] + value_columns],
            reference_df[[key_column] + value_columns],
            on=key_column,
            suffixes=('_1', '_2'),
            how='inner'
        )
        
        if len(merged) == 0:
            return 50.0  # No matching records
        
        match_scores = []
        for col in value_columns:
            col1 = f"{col}_1"
            col2 = f"{col}_2"
            
            if col1 in merged.columns and col2 in merged.columns:
                matches = (merged[col1] == merged[col2]).sum()
                match_scores.append((matches / len(merged)) * 100)
        
        return np.mean(match_scores) if match_scores else 50.0
    
    def score_timeliness(
        self,
        df: pd.DataFrame,
        timestamp_column: Optional[str] = None,
        max_age_days: int = 7
    ) -> float:
        """
        Score data timeliness
        
        Args:
            df: DataFrame to score
            timestamp_column: Column containing timestamps
            max_age_days: Maximum acceptable age in days
        
        Returns:
            Timeliness score (0-100)
        """
        if timestamp_column is None or timestamp_column not in df.columns:
            return 70.0  # Default moderate score
        
        try:
            timestamps = pd.to_datetime(df[timestamp_column])
            now = pd.Timestamp.now()
            
            ages = (now - timestamps).dt.days
            
            # Score based on age distribution
            fresh_records = (ages <= max_age_days).sum()
            timeliness_ratio = fresh_records / len(df)
            
            # Additional penalty for very old data
            avg_age = ages.mean()
            age_penalty = min(30, (avg_age - max_age_days) / max_age_days * 10) if avg_age > max_age_days else 0
            
            score = max(0, (timeliness_ratio * 100) - age_penalty)
            return min(100, score)
            
        except Exception:
            return 70.0  # Default on error
    
    def score_validity(
        self,
        df: pd.DataFrame,
        business_rules: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Score data validity against business rules
        
        Args:
            df: DataFrame to score
            business_rules: Dictionary of business rules to validate
        
        Returns:
            Validity score (0-100)
        """
        if not business_rules or len(df) == 0:
            return 75.0  # Default moderate score
        
        validity_scores = []
        
        for rule_name, rule_config in business_rules.items():
            if rule_config.get('type') == 'range':
                col = rule_config['column']
                min_val = rule_config['min']
                max_val = rule_config['max']
                
                if col in df.columns:
                    valid = df[col].between(min_val, max_val, inclusive='both')
                    validity_scores.append((valid.sum() / len(df)) * 100)
            
            elif rule_config.get('type') == 'allowed_values':
                col = rule_config['column']
                allowed = set(rule_config['values'])
                
                if col in df.columns:
                    valid = df[col].isin(allowed)
                    validity_scores.append((valid.sum() / len(df)) * 100)
            
            elif rule_config.get('type') == 'pattern':
                col = rule_config['column']
                pattern = rule_config['pattern']
                
                if col in df.columns:
                    valid = df[col].astype(str).str.match(pattern, na=False)
                    validity_scores.append((valid.sum() / len(df)) * 100)
        
        return np.mean(validity_scores) if validity_scores else 75.0
    
    def score_uniqueness(
        self,
        df: pd.DataFrame,
        key_columns: Optional[List[str]] = None
    ) -> float:
        """
        Score data uniqueness
        
        Args:
            df: DataFrame to score
            key_columns: Columns that should be unique
        
        Returns:
            Uniqueness score (0-100)
        """
        if len(df) == 0:
            return 100.0
        
        if key_columns is None:
            # Check all columns
            key_columns = df.columns.tolist()
        
        duplicates = df.duplicated(subset=key_columns, keep=False).sum()
        uniqueness_ratio = 1 - (duplicates / len(df))
        
        return uniqueness_ratio * 100
    
    def calculate_trust_score(
        self,
        df: pd.DataFrame,
        config: Optional[Dict[str, Any]] = None
    ) -> TrustScore:
        """
        Calculate comprehensive trust score
        
        Args:
            df: DataFrame to score
            config: Configuration with validation parameters
        
        Returns:
            TrustScore object
        """
        config = config or {}
        
        # Calculate individual dimension scores
        dimensions = {
            "completeness": self.score_completeness(
                df,
                config.get('critical_columns')
            ),
            "accuracy": self.score_accuracy(
                df,
                config.get('value_ranges'),
                config.get('validation_results')
            ),
            "consistency": self.score_consistency(
                df,
                config.get('reference_df'),
                config.get('key_column'),
                config.get('value_columns')
            ),
            "timeliness": self.score_timeliness(
                df,
                config.get('timestamp_column'),
                config.get('max_age_days', 7)
            ),
            "validity": self.score_validity(
                df,
                config.get('business_rules')
            ),
            "uniqueness": self.score_uniqueness(
                df,
                config.get('key_columns')
            )
        }
        
        # Calculate weighted overall score
        overall_score = sum(
            score * self.dimension_weights.get(dim, 0)
            for dim, score in dimensions.items()
        )
        
        # Determine trust level
        if overall_score >= 90:
            trust_level = TrustLevel.VERIFIED
        elif overall_score >= 75:
            trust_level = TrustLevel.HIGH
        elif overall_score >= 60:
            trust_level = TrustLevel.MEDIUM
        elif overall_score >= 40:
            trust_level = TrustLevel.LOW
        else:
            trust_level = TrustLevel.UNTRUSTED
        
        # Identify issues
        issues = []
        for dim, score in dimensions.items():
            if score < 70:
                issues.append(f"{dim.capitalize()} score is low ({score:.1f}%)")
        
        metadata = {
            "record_count": len(df),
            "column_count": len(df.columns),
            "dimension_weights": self.dimension_weights
        }
        
        return TrustScore(
            overall_score=round(overall_score, 2),
            dimensions={k: round(v, 2) for k, v in dimensions.items()},
            trust_level=trust_level,
            issues=issues,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
    
    def generate_trust_report(self, trust_score: TrustScore) -> str:
        """
        Generate human-readable trust report
        
        Args:
            trust_score: TrustScore object
        
        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 70,
            "DATA TRUST SCORE REPORT",
            "=" * 70,
            f"\nOverall Trust Score: {trust_score.overall_score}/100",
            f"Trust Level: {trust_score.trust_level.value.upper()}",
            f"Timestamp: {trust_score.timestamp.isoformat()}",
            f"\nDataset Metadata:",
            f"  Records: {trust_score.metadata['record_count']:,}",
            f"  Columns: {trust_score.metadata['column_count']}",
            "\n" + "-" * 70,
            "DIMENSION SCORES",
            "-" * 70,
        ]
        
        for dim, score in trust_score.dimensions.items():
            status = "✓" if score >= 75 else "⚠" if score >= 60 else "✗"
            report_lines.append(f"{status} {dim.capitalize():15} {score:6.2f}%")
        
        if trust_score.issues:
            report_lines.extend([
                "\n" + "-" * 70,
                "ISSUES IDENTIFIED",
                "-" * 70
            ])
            for issue in trust_score.issues:
                report_lines.append(f"• {issue}")
        
        # Recommendations
        report_lines.extend([
            "\n" + "-" * 70,
            "RECOMMENDATIONS",
            "-" * 70
        ])
        
        if trust_score.overall_score >= 90:
            report_lines.append("✓ Data is highly trustworthy and suitable for AI/ML models")
        elif trust_score.overall_score >= 75:
            report_lines.append("✓ Data is suitable for most AI/ML applications")
            report_lines.append("  Consider addressing minor issues for critical applications")
        elif trust_score.overall_score >= 60:
            report_lines.append("⚠ Data quality needs improvement before AI/ML use")
            report_lines.append("  Address identified issues before production deployment")
        else:
            report_lines.append("✗ Data quality is insufficient for AI/ML models")
            report_lines.append("  Significant remediation required before use")
        
        report_lines.append("\n" + "=" * 70)
        
        return "\n".join(report_lines)


class TrustScoreHistory:
    """
    Track trust scores over time
    """
    
    def __init__(self):
        self.history: List[TrustScore] = []
    
    def add_score(self, score: TrustScore) -> None:
        """Add a trust score to history"""
        self.history.append(score)
    
    def get_trend(self, dimension: Optional[str] = None) -> List[float]:
        """
        Get score trend over time
        
        Args:
            dimension: Specific dimension to track, or None for overall
        
        Returns:
            List of scores over time
        """
        if dimension:
            return [
                score.dimensions.get(dimension, 0)
                for score in self.history
            ]
        else:
            return [score.overall_score for score in self.history]
    
    def get_average_score(self, days: int = 30) -> float:
        """
        Get average score over time period
        
        Args:
            days: Number of days to look back
        
        Returns:
            Average score
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_scores = [
            score.overall_score
            for score in self.history
            if score.timestamp >= cutoff
        ]
        
        return np.mean(recent_scores) if recent_scores else 0.0
