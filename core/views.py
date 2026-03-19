from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import DataSource, ValidationResult, TrustScore, GovernanceMetric
from .utils import DataQualityValidator, TrustScoringEngine, GovernanceFramework
import pandas as pd
import io


def dashboard(request):
    """Main dashboard showing overall health and recent activity"""
    # Get statistics
    total_sources = DataSource.objects.filter(is_active=True).count()
    recent_validations = ValidationResult.objects.order_by('-timestamp')[:10]
    recent_trust_scores = TrustScore.objects.order_by('-calculated_at')[:10]

    # Calculate averages
    avg_trust_score = TrustScore.objects.filter(
        calculated_at__gte=timezone.now() - timedelta(days=7)
    ).aggregate(Avg('overall_score'))['overall_score__avg'] or 0

    avg_quality_score = ValidationResult.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).aggregate(Avg('quality_score'))['quality_score__avg'] or 0

    # Trust level distribution
    trust_distribution = TrustScore.objects.values('trust_level').annotate(
        count=Count('id')
    ).order_by('-count')

    context = {
        'total_sources': total_sources,
        'avg_trust_score': round(avg_trust_score, 1),
        'avg_quality_score': round(avg_quality_score, 1),
        'recent_validations': recent_validations,
        'recent_trust_scores': recent_trust_scores,
        'trust_distribution': trust_distribution,
    }

    return render(request, 'dashboard.html', context)


def data_sources_list(request):
    """List all data sources"""
    sources = DataSource.objects.all().prefetch_related('validations', 'trust_scores')

    # Annotate with latest scores
    for source in sources:
        source.latest_trust = source.trust_scores.first()
        source.latest_validation = source.validations.first()

    context = {'sources': sources}
    return render(request, 'data_sources.html', context)


def data_source_detail(request, pk):
    """Detail view for a specific data source"""
    source = get_object_or_404(DataSource, pk=pk)
    validations = source.validations.order_by('-timestamp')[:20]
    trust_scores = source.trust_scores.order_by('-calculated_at')[:20]

    context = {
        'source': source,
        'validations': validations,
        'trust_scores': trust_scores,
    }
    return render(request, 'data_source_detail.html', context)


def validate_data(request, pk):
    """Run data validation for a source"""
    source = get_object_or_404(DataSource, pk=pk)

    if request.method == 'POST' and request.FILES.get('csv_file'):
        try:
            # Read CSV file
            csv_file = request.FILES['csv_file']
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))

            # Run validation
            validator = DataQualityValidator()
            config = {
                'required_columns': list(df.columns),
                'key_columns': [df.columns[0]] if len(df.columns) > 0 else [],
            }

            results, quality_score = validator.run_validation_suite(df, config)

            # Save results
            validation = ValidationResult.objects.create(
                source=source,
                passed=quality_score >= 70,
                quality_score=quality_score,
                total_rules=len(results),
                passed_rules=sum(1 for r in results if r.passed),
                failed_rules=sum(1 for r in results if not r.passed),
                details={'results': [r.to_dict() for r in results]}
            )

            messages.success(request, f'Validation completed! Quality Score: {quality_score:.1f}')
            return redirect('data_source_detail', pk=pk)

        except Exception as e:
            messages.error(request, f'Validation failed: {str(e)}')

    return render(request, 'validate_data.html', {'source': source})


def calculate_trust(request, pk):
    """Calculate trust score for a source"""
    source = get_object_or_404(DataSource, pk=pk)

    if request.method == 'POST' and request.FILES.get('csv_file'):
        try:
            # Read CSV file
            csv_file = request.FILES['csv_file']
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))

            # Calculate trust score
            trust_engine = TrustScoringEngine()
            trust_result = trust_engine.calculate_trust_score(df)

            # Save results
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

            messages.success(
                request,
                f'Trust score calculated! Overall: {trust_result.overall_score:.1f} ({trust_result.trust_level.value.upper()})'
            )
            return redirect('data_source_detail', pk=pk)

        except Exception as e:
            messages.error(request, f'Trust calculation failed: {str(e)}')

    return render(request, 'calculate_trust.html', {'source': source})


def governance_metrics(request):
    """View and manage governance metrics"""
    metrics = GovernanceMetric.objects.filter(is_active=True)

    if request.method == 'POST':
        # Add new metric
        name = request.POST.get('name')
        display_name = request.POST.get('display_name')
        description = request.POST.get('description')
        data_type = request.POST.get('data_type')

        if name and display_name:
            GovernanceMetric.objects.create(
                name=name,
                display_name=display_name,
                description=description,
                data_type=data_type
            )
            messages.success(request, f'Metric "{display_name}" created successfully!')
            return redirect('governance_metrics')

    context = {'metrics': metrics}
    return render(request, 'governance_metrics.html', context)


def ui(request):
    """Render the simple demo UI"""
    return render(request, 'ui.html')


def index(request):
    """API health check / index"""
    latest = TrustScore.objects.order_by('-calculated_at').first()
    data = {
        'status': 'running',
        'total_sources': DataSource.objects.filter(is_active=True).count(),
        'latest_trust_score': latest.overall_score if latest else None,
        'timestamp': timezone.now().isoformat()
    }
    return JsonResponse(data)
