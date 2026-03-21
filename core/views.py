import json
import io
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    DataSource, ValidationResult, TrustScore, GovernanceMetric,
    SemanticDefinition, ReconciliationRun, DataLineage,
)
from .utils import DataQualityValidator, TrustScoringEngine, ReconciliationEngine
from .utils.osi_export import export_osi_spec, import_osi_spec
import pandas as pd

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

def dashboard(request):
    """Main dashboard showing overall health, recent activity, and reconciliation status."""
    total_sources = DataSource.objects.filter(is_active=True).count()
    recent_validations = ValidationResult.objects.order_by('-timestamp')[:10]
    recent_trust_scores = TrustScore.objects.order_by('-calculated_at')[:10]

    avg_trust_score = TrustScore.objects.filter(
        calculated_at__gte=timezone.now() - timedelta(days=7)
    ).aggregate(Avg('overall_score'))['overall_score__avg'] or 0

    avg_quality_score = ValidationResult.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).aggregate(Avg('quality_score'))['quality_score__avg'] or 0

    trust_distribution = TrustScore.objects.values('trust_level').annotate(
        count=Count('id')
    ).order_by('-count')

    # Reconciliation stats
    total_metrics = GovernanceMetric.objects.filter(is_active=True).count()
    total_semantic_defs = SemanticDefinition.objects.count()
    recent_reconciliations = ReconciliationRun.objects.order_by('-run_at')[:5]
    inconsistent_count = SemanticDefinition.objects.filter(is_consistent=False).count()

    # Average trust dimensions across all latest scores
    dimension_avgs = TrustScore.objects.aggregate(
        avg_completeness=Avg('completeness_score'),
        avg_accuracy=Avg('accuracy_score'),
        avg_consistency=Avg('consistency_score'),
        avg_timeliness=Avg('timeliness_score'),
        avg_validity=Avg('validity_score'),
        avg_uniqueness=Avg('uniqueness_score'),
    )

    context = {
        'total_sources': total_sources,
        'avg_trust_score': round(avg_trust_score, 1),
        'avg_quality_score': round(avg_quality_score, 1),
        'recent_validations': recent_validations,
        'recent_trust_scores': recent_trust_scores,
        'trust_distribution': trust_distribution,
        'total_metrics': total_metrics,
        'total_semantic_defs': total_semantic_defs,
        'recent_reconciliations': recent_reconciliations,
        'inconsistent_count': inconsistent_count,
        'dim_completeness': round(dimension_avgs['avg_completeness'] or 0, 1),
        'dim_accuracy': round(dimension_avgs['avg_accuracy'] or 0, 1),
        'dim_consistency': round(dimension_avgs['avg_consistency'] or 0, 1),
        'dim_timeliness': round(dimension_avgs['avg_timeliness'] or 0, 1),
        'dim_validity': round(dimension_avgs['avg_validity'] or 0, 1),
        'dim_uniqueness': round(dimension_avgs['avg_uniqueness'] or 0, 1),
    }

    return render(request, 'dashboard.html', context)


# ──────────────────────────────────────────────
# Data Sources
# ──────────────────────────────────────────────

def data_sources_list(request):
    sources = DataSource.objects.all().prefetch_related('validations', 'trust_scores')
    for source in sources:
        source.latest_trust = source.trust_scores.first()
        source.latest_validation = source.validations.first()
    return render(request, 'data_sources.html', {'sources': sources})


def data_source_detail(request, pk):
    source = get_object_or_404(DataSource, pk=pk)
    validations = source.validations.order_by('-timestamp')[:20]
    trust_scores = source.trust_scores.order_by('-calculated_at')[:20]
    semantic_defs = source.semantic_definitions.select_related('governance_metric').all()
    lineage_in = source.lineage_incoming.select_related('source_from').all()
    lineage_out = source.lineage_outgoing.select_related('source_to').all()

    context = {
        'source': source,
        'validations': validations,
        'trust_scores': trust_scores,
        'semantic_defs': semantic_defs,
        'lineage_in': lineage_in,
        'lineage_out': lineage_out,
    }
    return render(request, 'data_source_detail.html', context)


def validate_data(request, pk):
    source = get_object_or_404(DataSource, pk=pk)
    if request.method == 'POST' and request.FILES.get('csv_file'):
        try:
            csv_file = request.FILES['csv_file']
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))
            validator = DataQualityValidator()
            config = {
                'required_columns': list(df.columns),
                'key_columns': [df.columns[0]] if len(df.columns) > 0 else [],
            }
            results, quality_score = validator.run_validation_suite(df, config)
            ValidationResult.objects.create(
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
    source = get_object_or_404(DataSource, pk=pk)
    if request.method == 'POST' and request.FILES.get('csv_file'):
        try:
            csv_file = request.FILES['csv_file']
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))
            trust_engine = TrustScoringEngine()
            trust_result = trust_engine.calculate_trust_score(df)
            TrustScore.objects.create(
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


# ──────────────────────────────────────────────
# Governance
# ──────────────────────────────────────────────

def governance_metrics(request):
    metrics = GovernanceMetric.objects.filter(is_active=True).prefetch_related('semantic_definitions')

    if request.method == 'POST':
        name = request.POST.get('name')
        display_name = request.POST.get('display_name')
        description = request.POST.get('description')
        formula = request.POST.get('formula', '')
        data_type = request.POST.get('data_type')
        category = request.POST.get('category', '')
        owner = request.POST.get('owner', '')

        if name and display_name:
            GovernanceMetric.objects.create(
                name=name,
                display_name=display_name,
                description=description,
                formula=formula,
                data_type=data_type,
                category=category,
                owner=owner,
            )
            messages.success(request, f'Metric "{display_name}" created successfully!')
            return redirect('governance_metrics')

    # Count semantic definitions per metric
    for metric in metrics:
        metric.source_count = metric.semantic_definitions.count()

    context = {'metrics': metrics}
    return render(request, 'governance_metrics.html', context)


# ──────────────────────────────────────────────
# Semantic Definitions (OSI mappings)
# ──────────────────────────────────────────────

def semantic_definitions(request):
    """View all semantic definitions (how metrics are implemented per source)."""
    definitions = SemanticDefinition.objects.select_related(
        'governance_metric', 'source'
    ).all()

    metrics = GovernanceMetric.objects.filter(is_active=True)
    sources = DataSource.objects.filter(is_active=True)

    if request.method == 'POST':
        metric_id = request.POST.get('governance_metric')
        source_id = request.POST.get('source')
        local_name = request.POST.get('local_name')
        local_formula = request.POST.get('local_formula', '')
        local_description = request.POST.get('local_description', '')
        definition_type = request.POST.get('definition_type', 'metric')

        if metric_id and source_id and local_name:
            metric = get_object_or_404(GovernanceMetric, pk=metric_id)
            source = get_object_or_404(DataSource, pk=source_id)

            SemanticDefinition.objects.update_or_create(
                governance_metric=metric,
                source=source,
                defaults={
                    'local_name': local_name,
                    'local_formula': local_formula,
                    'local_description': local_description,
                    'definition_type': definition_type,
                }
            )
            messages.success(
                request,
                f'Semantic definition for "{metric.display_name}" in {source.name} saved!'
            )
            return redirect('semantic_definitions')

    context = {
        'definitions': definitions,
        'metrics': metrics,
        'sources': sources,
    }
    return render(request, 'semantic_definitions.html', context)


# ──────────────────────────────────────────────
# Reconciliation
# ──────────────────────────────────────────────

def reconciliation_dashboard(request):
    """Cross-source metric reconciliation dashboard."""
    metrics = GovernanceMetric.objects.filter(is_active=True).prefetch_related(
        'semantic_definitions__source'
    )
    recent_runs = ReconciliationRun.objects.order_by('-run_at')[:20]
    definitions = SemanticDefinition.objects.select_related('governance_metric', 'source')

    # Summary stats
    total_metrics = metrics.count()
    metrics_with_defs = metrics.filter(semantic_definitions__isnull=False).distinct().count()
    inconsistent = definitions.filter(is_consistent=False).count()

    context = {
        'metrics': metrics,
        'recent_runs': recent_runs,
        'total_metrics': total_metrics,
        'metrics_with_defs': metrics_with_defs,
        'inconsistent_count': inconsistent,
        'total_definitions': definitions.count(),
    }
    return render(request, 'reconciliation.html', context)


def run_reconciliation(request):
    """Run reconciliation for all metrics or a specific one."""
    if request.method != 'POST':
        return redirect('reconciliation_dashboard')

    metric_id = request.POST.get('metric_id')
    engine = ReconciliationEngine()

    if metric_id:
        # Reconcile a single metric
        metric = get_object_or_404(GovernanceMetric, pk=metric_id)
        metrics_qs = GovernanceMetric.objects.filter(pk=metric_id)
    else:
        # Reconcile all
        metrics_qs = GovernanceMetric.objects.filter(is_active=True)

    definitions_qs = SemanticDefinition.objects.select_related('governance_metric', 'source')
    results = engine.reconcile_all(metrics_qs, definitions_qs)

    # Save results
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
        # Link compared sources
        source_names = set()
        for d in result.divergences:
            source_names.add(d.source_a)
            source_names.add(d.source_b)
        sources = DataSource.objects.filter(name__in=source_names)
        run.sources_compared.set(sources)

        # Update consistency flags on semantic definitions
        for defn in SemanticDefinition.objects.filter(governance_metric=metric):
            is_consistent = defn.source.name not in {
                d.source_b for d in result.divergences
            }
            defn.is_consistent = is_consistent
            defn.last_verified = timezone.now()
            defn.save(update_fields=['is_consistent', 'last_verified'])

    count = len(results)
    divergent = sum(1 for r in results if r.status == 'divergent')
    messages.success(
        request,
        f'Reconciliation complete! {count} metrics analyzed, {divergent} divergent.'
    )
    return redirect('reconciliation_dashboard')


# ──────────────────────────────────────────────
# Data Lineage
# ──────────────────────────────────────────────

def lineage_view(request):
    """View data lineage flows between sources."""
    flows = DataLineage.objects.select_related('source_from', 'source_to').all()
    sources = DataSource.objects.filter(is_active=True)

    if request.method == 'POST':
        from_id = request.POST.get('source_from')
        to_id = request.POST.get('source_to')
        flow_type = request.POST.get('flow_type', 'etl')
        description = request.POST.get('description', '')
        schedule = request.POST.get('schedule', '')

        if from_id and to_id and from_id != to_id:
            source_from = get_object_or_404(DataSource, pk=from_id)
            source_to = get_object_or_404(DataSource, pk=to_id)
            DataLineage.objects.update_or_create(
                source_from=source_from,
                source_to=source_to,
                flow_type=flow_type,
                defaults={
                    'description': description,
                    'schedule': schedule,
                }
            )
            messages.success(request, f'Lineage flow {source_from.name} -> {source_to.name} saved!')
            return redirect('lineage')

    context = {
        'flows': flows,
        'sources': sources,
    }
    return render(request, 'lineage.html', context)


# ──────────────────────────────────────────────
# OSI Export / Import
# ──────────────────────────────────────────────

def osi_export_view(request):
    """Export the full semantic model as OSI-compatible JSON."""
    metrics = GovernanceMetric.objects.filter(is_active=True)
    definitions = SemanticDefinition.objects.select_related('governance_metric', 'source').all()
    sources = DataSource.objects.filter(is_active=True)
    lineage = DataLineage.objects.select_related('source_from', 'source_to').all()

    spec = export_osi_spec(metrics, definitions, sources, lineage)

    if request.GET.get('format') == 'download':
        response = JsonResponse(spec, json_dumps_params={'indent': 2})
        response['Content-Disposition'] = 'attachment; filename="osi_semantic_model.json"'
        return response

    context = {
        'spec_json': json.dumps(spec, indent=2),
        'metrics_count': metrics.count(),
        'sources_count': sources.count(),
        'mappings_count': definitions.count(),
        'lineage_count': lineage.count(),
    }
    return render(request, 'osi_export.html', context)


def osi_import_view(request):
    """Import an OSI-compatible JSON specification."""
    if request.method == 'POST':
        json_file = request.FILES.get('osi_file')
        if json_file:
            try:
                spec_data = json.loads(json_file.read().decode('utf-8'))
                create_sources = request.POST.get('create_sources') == 'on'
                stats = import_osi_spec(spec_data, create_sources=create_sources)
                messages.success(
                    request,
                    f'Import complete! Metrics: {stats["metrics_created"]} created, '
                    f'{stats["metrics_updated"]} updated. '
                    f'Sources: {stats["sources_created"]}. '
                    f'Mappings: {stats["mappings_created"]}.'
                )
                if stats['errors']:
                    messages.error(request, f'Errors: {"; ".join(stats["errors"])}')
                return redirect('osi_export')
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON file.')
            except Exception as e:
                messages.error(request, f'Import failed: {str(e)}')

    return redirect('osi_export')
