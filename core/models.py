from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class DataSource(models.Model):
    """Represents a data source being monitored"""
    SOURCE_TYPES = [
        ('snowflake', 'Snowflake'),
        ('tableau', 'Tableau'),
        ('database', 'Database'),
        ('api', 'API'),
        ('file', 'File'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES, default='other')
    connector = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.source_type})"

    class Meta:
        ordering = ['-created_at']


class ValidationResult(models.Model):
    """Stores data quality validation results"""
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='validations')
    timestamp = models.DateTimeField(auto_now_add=True)
    passed = models.BooleanField(default=False)
    quality_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        null=True,
        blank=True
    )
    total_rules = models.IntegerField(default=0)
    passed_rules = models.IntegerField(default=0)
    failed_rules = models.IntegerField(default=0)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Validation for {self.source.name} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']


class TrustScore(models.Model):
    """Stores trust scores for data sources"""
    TRUST_LEVELS = [
        ('verified', 'Verified (90-100%)'),
        ('high', 'High (75-89%)'),
        ('medium', 'Medium (60-74%)'),
        ('low', 'Low (40-59%)'),
        ('untrusted', 'Untrusted (0-39%)'),
    ]

    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='trust_scores')
    overall_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    trust_level = models.CharField(max_length=20, choices=TRUST_LEVELS)

    # Dimension scores
    completeness_score = models.FloatField(default=0.0)
    accuracy_score = models.FloatField(default=0.0)
    consistency_score = models.FloatField(default=0.0)
    timeliness_score = models.FloatField(default=0.0)
    validity_score = models.FloatField(default=0.0)
    uniqueness_score = models.FloatField(default=0.0)

    issues = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source.name}: {self.overall_score:.1f} ({self.trust_level})"

    class Meta:
        ordering = ['-calculated_at']


class GovernanceMetric(models.Model):
    """Stores standardized metric definitions for governance — the single source of truth.
    Inspired by the OSI (Open Semantic Interchange) initiative."""
    name = models.CharField(max_length=200, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField()
    formula = models.TextField(blank=True, help_text='Canonical calculation formula (e.g. SUM(amount) WHERE status=completed)')
    data_type = models.CharField(max_length=50)
    category = models.CharField(max_length=100, blank=True)
    owner = models.CharField(max_length=200, blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    class Meta:
        ordering = ['name']


class SemanticDefinition(models.Model):
    """OSI-inspired semantic model definition.
    Maps how a GovernanceMetric is implemented in a specific DataSource.
    Enables cross-source comparison to detect inconsistencies."""

    DIMENSION_TYPES = [
        ('metric', 'Metric'),
        ('dimension', 'Dimension'),
        ('relationship', 'Relationship'),
    ]

    governance_metric = models.ForeignKey(
        GovernanceMetric, on_delete=models.CASCADE, related_name='semantic_definitions'
    )
    source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='semantic_definitions'
    )
    definition_type = models.CharField(max_length=20, choices=DIMENSION_TYPES, default='metric')
    local_name = models.CharField(
        max_length=200,
        help_text='Name of this metric/field in the source system (e.g. "total_rev" in Snowflake)'
    )
    local_formula = models.TextField(
        blank=True,
        help_text='How this metric is calculated in this specific source'
    )
    local_description = models.TextField(
        blank=True,
        help_text='How this source describes/defines the metric'
    )
    column_mapping = models.JSONField(
        default=dict, blank=True,
        help_text='Maps canonical column names to source-specific column names'
    )
    filters = models.JSONField(
        default=list, blank=True,
        help_text='Filters applied in this source (e.g. WHERE status=active)'
    )
    is_consistent = models.BooleanField(
        default=True,
        help_text='Whether this definition is consistent with the canonical governance metric'
    )
    consistency_notes = models.TextField(
        blank=True,
        help_text='Notes on any inconsistencies found'
    )
    last_verified = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.governance_metric.name} @ {self.source.name}"

    class Meta:
        ordering = ['governance_metric__name', 'source__name']
        unique_together = ['governance_metric', 'source']


class ReconciliationRun(models.Model):
    """Records a cross-source metric reconciliation run.
    Compares how the same GovernanceMetric is defined/calculated across multiple DataSources."""

    STATUS_CHOICES = [
        ('consistent', 'Consistent'),
        ('divergent', 'Divergent'),
        ('partial', 'Partially Consistent'),
    ]

    governance_metric = models.ForeignKey(
        GovernanceMetric, on_delete=models.CASCADE, related_name='reconciliations'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='consistent')
    sources_compared = models.ManyToManyField(DataSource, related_name='reconciliations')
    total_sources = models.IntegerField(default=0)
    consistent_sources = models.IntegerField(default=0)
    divergent_sources = models.IntegerField(default=0)
    consistency_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Percentage of sources with consistent definitions'
    )
    divergences = models.JSONField(
        default=list, blank=True,
        help_text='List of specific divergences found'
    )
    recommendations = models.JSONField(
        default=list, blank=True,
        help_text='Suggested actions to resolve divergences'
    )
    run_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reconciliation: {self.governance_metric.name} ({self.status})"

    class Meta:
        ordering = ['-run_at']


class DataLineage(models.Model):
    """Tracks data flow between sources — which source feeds into which."""
    FLOW_TYPES = [
        ('etl', 'ETL Pipeline'),
        ('replication', 'Replication'),
        ('api_sync', 'API Sync'),
        ('manual', 'Manual'),
        ('streaming', 'Streaming'),
    ]

    source_from = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='lineage_outgoing'
    )
    source_to = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='lineage_incoming'
    )
    flow_type = models.CharField(max_length=20, choices=FLOW_TYPES, default='etl')
    description = models.TextField(blank=True)
    metrics_transferred = models.ManyToManyField(
        GovernanceMetric, blank=True, related_name='lineage_flows'
    )
    is_active = models.BooleanField(default=True)
    schedule = models.CharField(max_length=100, blank=True, help_text='e.g. hourly, daily, real-time')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source_from.name} -> {self.source_to.name} ({self.flow_type})"

    class Meta:
        ordering = ['source_from__name']
        unique_together = ['source_from', 'source_to', 'flow_type']
