from rest_framework import serializers
from .models import DataSource, ValidationResult, TrustScore, GovernanceMetric


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
    class Meta:
        model = GovernanceMetric
        fields = '__all__'


class TrustScoreSummarySerializer(serializers.Serializer):
    overall_score = serializers.FloatField()
    trust_level = serializers.CharField()
    dimensions = serializers.DictField()
    issues = serializers.ListField()
    metadata = serializers.DictField()
