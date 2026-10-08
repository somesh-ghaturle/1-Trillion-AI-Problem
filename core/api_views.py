import io
import json
import logging

from rest_framework import viewsets, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from django.utils import timezone

from .models import (
    DataSource, ValidationResult, TrustScore, GovernanceMetric,
    SemanticDefinition, ReconciliationRun, DataLineage,
)
from .serializers import (
    DataSourceSerializer, ValidationResultSerializer,
    TrustScoreSerializer, GovernanceMetricSerializer,
    SemanticDefinitionSerializer, ReconciliationRunSerializer,
    DataLineageSerializer,
)
from .utils import DataQualityValidator, TrustScoringEngine, ReconciliationEngine
from .utils.osi_export import export_osi_spec, import_osi_spec

logger = logging.getLogger(__name__)


class DataSourceViewSet(viewsets.ModelViewSet):
    """API endpoint for managing data sources."""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    search_fields = ['name', 'description', 'connector']
    filterset_fields = ['source_type', 'is_active']
    ordering_fields = ['name', 'created_at']

    @action(detail=True, methods=['post'], url_path='validate')
    def run_validation(self, request, pk=None):
        """Run data quality validation on uploaded CSV for this source."""
        source = self.get_object()
        csv_file = request.FILES.get('csv_file') or request.FILES.get('csv')

        if not csv_file:
            return Response(
                {'error': 'CSV file is required. Upload as csv_file or csv.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import pandas as pd
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))

            validator = DataQualityValidator()
            config = {
                'required_columns': list(df.columns),
                'key_columns': [df.columns[0]] if len(df.columns) > 0 else [],
            }

            results, quality_score = validator.run_validation_suite(df, config)

            validation = ValidationResult.objects.create(
                source=source,
                passed=quality_score >= 70,
                quality_score=quality_score,
                total_rules=len(results),
                passed_rules=sum(1 for r in results if r.passed),
                failed_rules=sum(1 for r in results if not r.passed),
                details={'results': [r.to_dict() for r in results]}
            )

            return Response({
                'id': validation.id,
                'quality_score': quality_score,
                'passed': validation.passed,
                'total_rules': validation.total_rules,
                'passed_rules': validation.passed_rules,
                'failed_rules': validation.failed_rules,
                'results': [r.to_dict() for r in results]
            })

        except Exception as e:
            logger.error("Validation failed for source %s: %s", pk, str(e))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='trust')
    def calculate_trust(self, request, pk=None):
        """Calculate trust score on uploaded CSV for this source."""
        source = self.get_object()
        csv_file = request.FILES.get('csv_file') or request.FILES.get('csv')

        if not csv_file:
            return Response(
                {'error': 'CSV file is required. Upload as csv_file or csv.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import pandas as pd
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))

            trust_engine = TrustScoringEngine()
            trust_result = trust_engine.calculate_trust_score(df)

            trust_score = TrustScore.objects.create(
                source=source,
                overall_score=trust_result.overall_score,
                trust_level=trust_result.trust_level.value,
                completeness_score=trust_result.dimensions.get('completeness', 0),
                accuracy_score=trust_result.dimensions.get('accuracy', 0),
                consistency_score=trust_result.dimensions.get('consistency', 0),
                timeliness_score=trust_result.dimensions.get('timeliness', 0),
                validity_score=trust_result.dimensions.get('validity', 0),
                uniqueness_score=trust_result.dimensions.get('uniqueness', 0),
                issues=trust_result.issues,
                metadata=trust_result.metadata
            )

            return Response(TrustScoreSerializer(trust_score).data)

        except Exception as e:
            logger.error("Trust calculation failed for source %s: %s", pk, str(e))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ValidationResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ValidationResult.objects.select_related('source').all()
    serializer_class = ValidationResultSerializer
    search_fields = ['source__name']
    filterset_fields = ['source', 'passed']
    ordering_fields = ['timestamp', 'quality_score']


class TrustScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrustScore.objects.select_related('source').all()
    serializer_class = TrustScoreSerializer
    search_fields = ['source__name']
    filterset_fields = ['source', 'trust_level']
    ordering_fields = ['calculated_at', 'overall_score']


class GovernanceMetricViewSet(viewsets.ModelViewSet):
    queryset = GovernanceMetric.objects.all()
    serializer_class = GovernanceMetricSerializer
    search_fields = ['name', 'display_name', 'description', 'formula', 'owner']
    filterset_fields = ['category', 'data_type', 'is_active']
    ordering_fields = ['name', 'created_at']

    @action(detail=False, methods=['get'], url_path='osi-export')
    def osi_export(self, request):
        """Export all governance metrics as OSI-compatible JSON."""
        metrics = GovernanceMetric.objects.filter(is_active=True)
        definitions = SemanticDefinition.objects.select_related('governance_metric', 'source').all()
        sources = DataSource.objects.filter(is_active=True)
        lineage = DataLineage.objects.select_related('source_from', 'source_to').all()
        spec = export_osi_spec(metrics, definitions, sources, lineage)
        return Response(spec)

    @action(detail=False, methods=['post'], url_path='osi-import')
    def osi_import(self, request):
        """Import an OSI-compatible JSON specification."""
        try:
            spec_data = request.data
            create_sources = request.query_params.get('create_sources', 'false').lower() == 'true'
            stats = import_osi_spec(spec_data, create_sources=create_sources)
            return Response(stats)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SemanticDefinitionViewSet(viewsets.ModelViewSet):
    queryset = SemanticDefinition.objects.select_related('governance_metric', 'source').all()
    serializer_class = SemanticDefinitionSerializer
    search_fields = ['local_name', 'local_formula', 'local_description', 'governance_metric__name', 'source__name']
    filterset_fields = ['governance_metric', 'source', 'is_consistent']
    ordering_fields = ['local_name', 'updated_at']


class ReconciliationRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationRun.objects.select_related('governance_metric').all()
    serializer_class = ReconciliationRunSerializer
    search_fields = ['governance_metric__name']
    filterset_fields = ['governance_metric', 'status']
    ordering_fields = ['run_at', 'consistency_score']

    @action(detail=False, methods=['post'], url_path='run')
    def run_reconciliation(self, request):
        """Run reconciliation for all metrics or a specific one."""
        metric_id = request.data.get('metric_id')
        engine = ReconciliationEngine()

        if metric_id:
            metrics_qs = GovernanceMetric.objects.filter(pk=metric_id, is_active=True)
        else:
            metrics_qs = GovernanceMetric.objects.filter(is_active=True)

        definitions_qs = SemanticDefinition.objects.select_related('governance_metric', 'source')
        results = engine.reconcile_all(metrics_qs, definitions_qs)

        saved = []
        for result in results:
            metric = GovernanceMetric.objects.get(name=result.metric_name)
            run = ReconciliationRun.objects.create(
                governance_metric=metric,
                status=result.status,
                total_sources=result.total_sources,
                consistent_sources=result.consistent_sources,
                divergent_sources=result.divergent_sources,
                consistency_score=result.consistency_score,
                divergences=[d.to_dict() for d in result.divergences],
                recommendations=result.recommendations,
            )
            saved.append(ReconciliationRunSerializer(run).data)

        return Response({'reconciliations': saved, 'count': len(saved)})


class DataLineageViewSet(viewsets.ModelViewSet):
    queryset = DataLineage.objects.select_related('source_from', 'source_to').all()
    serializer_class = DataLineageSerializer
    search_fields = ['description', 'source_from__name', 'source_to__name']
    filterset_fields = ['flow_type', 'source_from', 'source_to']


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_health(request):
    """API health check endpoint."""
    latest = TrustScore.objects.order_by('-calculated_at').first()
    return Response({
        'status': 'running',
        'total_sources': DataSource.objects.filter(is_active=True).count(),
        'total_metrics': GovernanceMetric.objects.filter(is_active=True).count(),
        'total_semantic_definitions': SemanticDefinition.objects.count(),
        'latest_trust_score': latest.overall_score if latest else None,
        'timestamp': timezone.now().isoformat(),
    })


class ThrottledObtainAuthToken(ObtainAuthToken):
    """POST username/password -> {"token": ...}. Throttled: DRF applies none by default."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'token'


def client_ip(request):
    """Client IP honouring REST_FRAMEWORK['NUM_PROXIES'], so a spoofed X-Forwarded-For is ignored."""
    return BaseThrottle().get_ident(request)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([AllowAny])  # read-only; no model queryset for model permissions
def insights(request):
    """Anomalous score drops per source, and a 7-day linear outlook for the daily health series."""
    from .utils.insights import detect_anomalies
    from .views import health_trend
    trend = health_trend()
    return Response({
        'anomalies': [a.to_dict() for a in detect_anomalies()],
        'outlook': {s['name']: s['forecast'] for s in trend['series']},
    })
