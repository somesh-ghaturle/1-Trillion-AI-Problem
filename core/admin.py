from django.contrib import admin
from .models import DataSource, ValidationResult, TrustScore, GovernanceMetric


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
    list_display = ('name', 'display_name', 'data_type', 'category', 'is_active')
    list_filter = ('data_type', 'category', 'is_active')
    search_fields = ('name', 'display_name', 'description')
    ordering = ('name',)
