import io
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.utils import timezone

from .models import DataSource, ValidationResult, TrustScore, GovernanceMetric
from .serializers import (
    DataSourceSerializer, ValidationResultSerializer,
    TrustScoreSerializer, GovernanceMetricSerializer
)
from .utils import DataQualityValidator, TrustScoringEngine

logger = logging.getLogger(__name__)


class DataSourceViewSet(viewsets.ModelViewSet):
    """API endpoint for managing data sources."""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer

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
    """API endpoint for viewing validation results."""
    queryset = ValidationResult.objects.select_related('source').all()
    serializer_class = ValidationResultSerializer
    filterset_fields = ['source', 'passed']


class TrustScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing trust scores."""
    queryset = TrustScore.objects.select_related('source').all()
    serializer_class = TrustScoreSerializer
    filterset_fields = ['source', 'trust_level']


class GovernanceMetricViewSet(viewsets.ModelViewSet):
    """API endpoint for managing governance metrics."""
    queryset = GovernanceMetric.objects.all()
    serializer_class = GovernanceMetricSerializer


@api_view(['GET'])
def api_health(request):
    """API health check endpoint."""
    latest = TrustScore.objects.order_by('-calculated_at').first()
    return Response({
        'status': 'running',
        'total_sources': DataSource.objects.filter(is_active=True).count(),
        'latest_trust_score': latest.overall_score if latest else None,
        'timestamp': timezone.now().isoformat(),
    })
