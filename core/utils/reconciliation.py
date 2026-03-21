"""
Cross-Source Metric Reconciliation Engine

Compares how the same metric is defined and calculated across multiple
data sources to detect inconsistencies — the core of the $1T AI problem.

Inspired by the Open Semantic Interchange (OSI) initiative led by
Snowflake, Salesforce, dbt Labs, BlackRock, and others.
"""
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class Divergence:
    """Represents a specific inconsistency found between sources."""
    metric_name: str
    source_a: str
    source_b: str
    divergence_type: str  # formula, naming, filter, column_mapping, description
    severity: str  # critical, high, medium, low
    detail: str
    recommendation: str

    def to_dict(self):
        return {
            'metric_name': self.metric_name,
            'source_a': self.source_a,
            'source_b': self.source_b,
            'divergence_type': self.divergence_type,
            'severity': self.severity,
            'detail': self.detail,
            'recommendation': self.recommendation,
        }


@dataclass
class ReconciliationResult:
    """Result of reconciling a metric across sources."""
    metric_name: str
    total_sources: int
    consistent_sources: int
    divergent_sources: int
    consistency_score: float
    status: str  # consistent, divergent, partial
    divergences: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)

    def to_dict(self):
        return {
            'metric_name': self.metric_name,
            'total_sources': self.total_sources,
            'consistent_sources': self.consistent_sources,
            'divergent_sources': self.divergent_sources,
            'consistency_score': self.consistency_score,
            'status': self.status,
            'divergences': [d.to_dict() for d in self.divergences],
            'recommendations': self.recommendations,
        }


def _normalize_formula(formula):
    """Normalize a formula for comparison by removing whitespace and lowering case."""
    if not formula:
        return ''
    normalized = re.sub(r'\s+', ' ', formula.strip().lower())
    # Normalize common SQL variations
    normalized = normalized.replace('sum (', 'sum(')
    normalized = normalized.replace('count (', 'count(')
    normalized = normalized.replace('avg (', 'avg(')
    normalized = normalized.replace(' = ', '=')
    normalized = normalized.replace("'", '"')
    return normalized


def _formula_similarity(formula_a, formula_b):
    """Calculate similarity between two formulas (0.0 to 1.0)."""
    norm_a = _normalize_formula(formula_a)
    norm_b = _normalize_formula(formula_b)
    if not norm_a and not norm_b:
        return 1.0
    if not norm_a or not norm_b:
        return 0.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()


class ReconciliationEngine:
    """Compares metric definitions across data sources to detect inconsistencies."""

    SIMILARITY_THRESHOLD = 0.85  # Below this, formulas are considered divergent

    def reconcile_metric(self, governance_metric, semantic_definitions):
        """
        Reconcile a single governance metric across all its semantic definitions.

        Args:
            governance_metric: GovernanceMetric model instance
            semantic_definitions: QuerySet of SemanticDefinition instances

        Returns:
            ReconciliationResult
        """
        definitions = list(semantic_definitions)
        total = len(definitions)

        if total == 0:
            return ReconciliationResult(
                metric_name=governance_metric.name,
                total_sources=0,
                consistent_sources=0,
                divergent_sources=0,
                consistency_score=0.0,
                status='consistent',
                recommendations=['No sources have defined this metric yet. Add semantic definitions to enable reconciliation.'],
            )

        if total == 1:
            # Still check single definition against canonical standard
            canonical_formula = governance_metric.formula
            single_issues = self._check_definition(governance_metric, definitions[0], canonical_formula)
            divergent_count = 1 if single_issues else 0
            consistent_count = 0 if single_issues else 1
            score = 0.0 if single_issues else 100.0
            status = 'divergent' if single_issues else 'consistent'
            recs = self._generate_recommendations(governance_metric, single_issues)
            recs.append('Only one source defines this metric. Add more sources for cross-system reconciliation.')
            return ReconciliationResult(
                metric_name=governance_metric.name,
                total_sources=1,
                consistent_sources=consistent_count,
                divergent_sources=divergent_count,
                consistency_score=score,
                status=status,
                divergences=single_issues,
                recommendations=recs,
            )

        canonical_formula = governance_metric.formula
        divergences = []
        divergent_set = set()

        # Compare each definition against the canonical formula
        for defn in definitions:
            issues = self._check_definition(governance_metric, defn, canonical_formula)
            if issues:
                divergent_set.add(defn.source.name)
                divergences.extend(issues)

        # Pairwise comparison between source definitions
        for i in range(len(definitions)):
            for j in range(i + 1, len(definitions)):
                pairwise = self._compare_definitions(governance_metric, definitions[i], definitions[j])
                for d in pairwise:
                    if d.source_a not in divergent_set and d.source_b not in divergent_set:
                        divergent_set.add(d.source_a)
                divergences.extend(pairwise)

        consistent = total - len(divergent_set)
        score = (consistent / total) * 100 if total > 0 else 0

        if score >= 100:
            status = 'consistent'
        elif score >= 50:
            status = 'partial'
        else:
            status = 'divergent'

        recommendations = self._generate_recommendations(governance_metric, divergences)

        return ReconciliationResult(
            metric_name=governance_metric.name,
            total_sources=total,
            consistent_sources=consistent,
            divergent_sources=len(divergent_set),
            consistency_score=round(score, 1),
            status=status,
            divergences=divergences,
            recommendations=recommendations,
        )

    def _check_definition(self, metric, defn, canonical_formula):
        """Check a single definition against the canonical governance metric."""
        issues = []

        # Formula comparison
        if canonical_formula and defn.local_formula:
            similarity = _formula_similarity(canonical_formula, defn.local_formula)
            if similarity < self.SIMILARITY_THRESHOLD:
                issues.append(Divergence(
                    metric_name=metric.name,
                    source_a='Governance Standard',
                    source_b=defn.source.name,
                    divergence_type='formula',
                    severity='critical' if similarity < 0.5 else 'high',
                    detail=f'Formula divergence (similarity: {similarity:.0%}). '
                           f'Standard: "{canonical_formula}" vs '
                           f'Source: "{defn.local_formula}"',
                    recommendation=f'Update {defn.source.name} to use the canonical formula: {canonical_formula}',
                ))

        # Naming inconsistency
        if defn.local_name.lower().replace('_', '') != metric.name.lower().replace('_', ''):
            issues.append(Divergence(
                metric_name=metric.name,
                source_a='Governance Standard',
                source_b=defn.source.name,
                divergence_type='naming',
                severity='medium',
                detail=f'Metric is named "{defn.local_name}" in {defn.source.name} '
                       f'but canonical name is "{metric.name}"',
                recommendation=f'Consider aliasing "{defn.local_name}" to "{metric.name}" '
                               f'or document the naming mapping.',
            ))

        return issues

    def _compare_definitions(self, metric, defn_a, defn_b):
        """Compare two source definitions against each other."""
        issues = []

        # Formula comparison between sources
        if defn_a.local_formula and defn_b.local_formula:
            similarity = _formula_similarity(defn_a.local_formula, defn_b.local_formula)
            if similarity < self.SIMILARITY_THRESHOLD:
                issues.append(Divergence(
                    metric_name=metric.name,
                    source_a=defn_a.source.name,
                    source_b=defn_b.source.name,
                    divergence_type='formula',
                    severity='critical' if similarity < 0.5 else 'high',
                    detail=f'Cross-source formula divergence (similarity: {similarity:.0%}). '
                           f'{defn_a.source.name}: "{defn_a.local_formula}" vs '
                           f'{defn_b.source.name}: "{defn_b.local_formula}"',
                    recommendation=f'Align formulas in {defn_a.source.name} and {defn_b.source.name} '
                                   f'to match the governance standard.',
                ))

        # Filter comparison
        filters_a = set(str(f) for f in (defn_a.filters or []))
        filters_b = set(str(f) for f in (defn_b.filters or []))
        if filters_a and filters_b and filters_a != filters_b:
            diff = filters_a.symmetric_difference(filters_b)
            issues.append(Divergence(
                metric_name=metric.name,
                source_a=defn_a.source.name,
                source_b=defn_b.source.name,
                divergence_type='filter',
                severity='high',
                detail=f'Different filters applied. Differences: {diff}',
                recommendation='Standardize filters across sources to ensure consistent results.',
            ))

        # Column mapping comparison
        if defn_a.column_mapping and defn_b.column_mapping:
            keys_a = set(defn_a.column_mapping.keys())
            keys_b = set(defn_b.column_mapping.keys())
            if keys_a != keys_b:
                missing_in_b = keys_a - keys_b
                missing_in_a = keys_b - keys_a
                if missing_in_b or missing_in_a:
                    issues.append(Divergence(
                        metric_name=metric.name,
                        source_a=defn_a.source.name,
                        source_b=defn_b.source.name,
                        divergence_type='column_mapping',
                        severity='medium',
                        detail=f'Column mapping mismatch. '
                               f'Only in {defn_a.source.name}: {missing_in_b or "none"}. '
                               f'Only in {defn_b.source.name}: {missing_in_a or "none"}.',
                        recommendation='Ensure all sources map the same set of canonical columns.',
                    ))

        return issues

    def _generate_recommendations(self, metric, divergences):
        """Generate high-level recommendations based on divergences found."""
        recs = []
        types = set(d.divergence_type for d in divergences)
        severities = set(d.severity for d in divergences)

        if not divergences:
            recs.append(f'All sources are consistent for "{metric.display_name}". No action needed.')
            return recs

        if 'critical' in severities:
            recs.append(
                f'CRITICAL: Major formula inconsistencies detected for "{metric.display_name}". '
                f'This means different systems are calculating this metric differently, '
                f'which will produce unreliable AI/ML predictions. Immediate remediation required.'
            )

        if 'formula' in types:
            recs.append(
                f'Standardize the formula for "{metric.display_name}" across all sources. '
                f'Use the canonical formula defined in governance: "{metric.formula or "not set"}".'
            )

        if 'naming' in types:
            recs.append(
                f'Create naming aliases or mappings so "{metric.name}" is consistently '
                f'referenced across all source systems.'
            )

        if 'filter' in types:
            recs.append(
                f'Align data filters for "{metric.display_name}" — different filters mean '
                f'different populations, leading to inconsistent metrics.'
            )

        if 'column_mapping' in types:
            recs.append(
                f'Ensure all sources map the same canonical columns for "{metric.display_name}".'
            )

        return recs

    def reconcile_all(self, governance_metrics_qs, semantic_definitions_qs):
        """Reconcile all governance metrics across all sources."""
        results = []
        for metric in governance_metrics_qs:
            defs = semantic_definitions_qs.filter(governance_metric=metric)
            result = self.reconcile_metric(metric, defs)
            results.append(result)
        return results
