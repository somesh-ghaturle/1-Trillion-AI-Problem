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
    """Stores standardized metric definitions for governance"""
    name = models.CharField(max_length=200, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField()
    formula = models.TextField(blank=True)
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
