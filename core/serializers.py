from rest_framework import serializers
from .models import (
    DataSource, ValidationResult, TrustScore, GovernanceMetric,
    SemanticDefinition, ReconciliationRun, DataLineage,
)


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = '__all__'


class ValidationResultSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = ValidationResult
        fields = [
            'id', 'source', 'source_name', 'timestamp', 'passed',
            'quality_score', 'total_rules', 'passed_rules', 'failed_rules', 'details'
        ]
        read_only_fields = ['timestamp']


class TrustScoreSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = TrustScore
        fields = [
            'id', 'source', 'source_name', 'overall_score', 'trust_level',
            'completeness_score', 'accuracy_score', 'consistency_score',
            'timeliness_score', 'validity_score', 'uniqueness_score',
            'issues', 'metadata', 'calculated_at'
        ]
        read_only_fields = ['calculated_at']


class GovernanceMetricSerializer(serializers.ModelSerializer):
    source_count = serializers.SerializerMethodField()

    class Meta:
        model = GovernanceMetric
        fields = '__all__'

    def get_source_count(self, obj):
        return obj.semantic_definitions.count()


class SemanticDefinitionSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='governance_metric.name', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = SemanticDefinition
        fields = '__all__'


class ReconciliationRunSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='governance_metric.name', read_only=True)

    class Meta:
        model = ReconciliationRun
        fields = '__all__'


class DataLineageSerializer(serializers.ModelSerializer):
    from_name = serializers.CharField(source='source_from.name', read_only=True)
    to_name = serializers.CharField(source='source_to.name', read_only=True)

    class Meta:
        model = DataLineage
        fields = '__all__'
