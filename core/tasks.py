"""Background tasks (Celery). With no broker configured they run inline, so callers behave the same."""
from celery import shared_task
from django.utils import timezone

from .models import DataSource, GovernanceMetric, ReconciliationRun, SemanticDefinition
from .utils.reconciliation import ReconciliationEngine


def reconcile_and_save(metric_ids=None):
    """Reconcile the given metrics (default: all active), save a run per metric, and refresh each
    mapping's consistency flag. Returns the new run ids. Shared by the UI, the API, and seed_data."""
    metrics = GovernanceMetric.objects.filter(is_active=True)
    if metric_ids:
        metrics = GovernanceMetric.objects.filter(pk__in=metric_ids)
    definitions = SemanticDefinition.objects.select_related('governance_metric', 'source')
    run_ids = []
    for result in ReconciliationEngine().reconcile_all(metrics, definitions):
        metric = GovernanceMetric.objects.get(name=result.metric_name)
        run = ReconciliationRun.objects.create(
            governance_metric=metric, status=result.status, total_sources=result.total_sources,
            consistent_sources=result.consistent_sources, divergent_sources=result.divergent_sources,
            consistency_score=result.consistency_score, divergences=[d.to_dict() for d in result.divergences],
            recommendations=result.recommendations,
        )
        names = {d.source_a for d in result.divergences} | {d.source_b for d in result.divergences}
        run.sources_compared.set(DataSource.objects.filter(name__in=names))
        divergent = {d.source_b for d in result.divergences}
        now = timezone.now()
        for defn in SemanticDefinition.objects.filter(governance_metric=metric).select_related('source'):
            defn.is_consistent = defn.source.name not in divergent
            defn.last_verified = now
            defn.save(update_fields=['is_consistent', 'last_verified'])
        run_ids.append(run.id)
    return run_ids


@shared_task
def run_reconciliation_task(metric_ids=None):
    return reconcile_and_save(metric_ids)


@shared_task
def deliver_alert_task(kind, title, details):
    from .alerts import deliver
    deliver(kind, title, details)
