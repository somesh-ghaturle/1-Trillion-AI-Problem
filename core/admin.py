from django.contrib import admin
from .models import (
    DataSource, ValidationResult, TrustScore, GovernanceMetric,
    SemanticDefinition, ReconciliationRun, DataLineage,
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'is_active', 'created_at')
    list_filter = ('source_type', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)


@admin.register(ValidationResult)
class ValidationResultAdmin(admin.ModelAdmin):
    list_display = ('source', 'timestamp', 'passed', 'quality_score', 'passed_rules', 'total_rules')
    list_filter = ('passed', 'timestamp')
    search_fields = ('source__name',)
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)


@admin.register(TrustScore)
class TrustScoreAdmin(admin.ModelAdmin):
    list_display = ('source', 'overall_score', 'trust_level', 'calculated_at')
    list_filter = ('trust_level', 'calculated_at')
    search_fields = ('source__name',)
    readonly_fields = ('calculated_at',)
    ordering = ('-calculated_at',)


@admin.register(GovernanceMetric)
class GovernanceMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'data_type', 'category', 'owner', 'is_active')
    list_filter = ('data_type', 'category', 'is_active')
    search_fields = ('name', 'display_name', 'description')
    ordering = ('name',)


@admin.register(SemanticDefinition)
class SemanticDefinitionAdmin(admin.ModelAdmin):
    list_display = ('governance_metric', 'source', 'definition_type', 'local_name', 'is_consistent', 'last_verified')
    list_filter = ('definition_type', 'is_consistent', 'source')
    search_fields = ('governance_metric__name', 'local_name')
    ordering = ('governance_metric__name',)


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    list_display = ('governance_metric', 'status', 'total_sources', 'consistent_sources', 'divergent_sources', 'consistency_score', 'run_at')
    list_filter = ('status', 'run_at')
    search_fields = ('governance_metric__name',)
    ordering = ('-run_at',)


@admin.register(DataLineage)
class DataLineageAdmin(admin.ModelAdmin):
    list_display = ('source_from', 'source_to', 'flow_type', 'schedule', 'is_active')
    list_filter = ('flow_type', 'is_active')
    search_fields = ('source_from__name', 'source_to__name')
    ordering = ('source_from__name',)
