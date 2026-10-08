"""
Health check and Prometheus metrics.

/healthz  - public; 200 when the database answers, 503 otherwise (for load balancers / uptime checks)
/metrics  - Prometheus text format, only with `Authorization: Bearer $METRICS_TOKEN`; 404 when the token
            isn't configured, so nothing is exposed by default
"""
import hmac
import os

from django.conf import settings
from django.db import connection
from django.db.models import Max
from django.http import Http404, HttpResponse, JsonResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.core import GaugeMetricFamily


def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:  # any DB failure means unhealthy
        return JsonResponse({'status': 'error', 'database': 'unreachable'}, status=503)
    return JsonResponse({'status': 'ok', 'database': 'ok'})


class AppMetricsCollector:
    """Business metrics read from the database at scrape time."""

    def collect(self):
        from core.models import DataSource, GovernanceMetric, ReconciliationRun

        trust = GaugeMetricFamily('tcc_trust_score', 'Latest overall trust score (0-100)', labels=['source'])
        quality = GaugeMetricFamily('tcc_data_quality_score', 'Latest validation quality score (0-100)', labels=['source'])
        for source in DataSource.objects.filter(is_active=True):
            latest_trust = source.trust_scores.order_by('-calculated_at').first()
            latest_validation = source.validations.order_by('-timestamp').first()
            if latest_trust:
                trust.add_metric([source.name], latest_trust.overall_score)
            if latest_validation:
                quality.add_metric([source.name], latest_validation.quality_score)
        yield trust
        yield quality

        consistency = GaugeMetricFamily('tcc_reconciliation_consistency',
                                        'Latest reconciliation consistency score per metric (0-100)', labels=['metric'])
        divergences = GaugeMetricFamily('tcc_open_divergences',
                                        'Divergences in the latest reconciliation run of each metric', labels=['severity'])
        by_severity = {}
        for metric in GovernanceMetric.objects.filter(is_active=True):
            run = metric.reconciliations.order_by('-run_at', '-pk').first()
            if run:
                consistency.add_metric([metric.name], run.consistency_score)
                for d in run.divergences:
                    severity = d.get('severity', 'unknown')
                    by_severity[severity] = by_severity.get(severity, 0) + 1
        for severity, count in sorted(by_severity.items()):
            divergences.add_metric([severity], count)
        yield consistency
        yield divergences

        last = ReconciliationRun.objects.aggregate(last=Max('run_at'))['last']
        yield GaugeMetricFamily('tcc_last_reconciliation_timestamp_seconds',
                                'Unix time of the most recent reconciliation run', value=last.timestamp() if last else 0)


_app_registry = CollectorRegistry()  # no auto_describe: it would query the DB at import, before migrate
_app_registry.register(AppMetricsCollector())


def _request_metrics():
    """django-prometheus request/DB metrics; merged across gunicorn workers in multiprocess mode."""
    from prometheus_client import REGISTRY, multiprocess
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    return generate_latest(REGISTRY)


def metrics(request):
    token = settings.METRICS_TOKEN
    if not token:
        raise Http404
    supplied = request.headers.get('Authorization', '')
    if not hmac.compare_digest(supplied.encode(), f'Bearer {token}'.encode()):
        return HttpResponse('Unauthorized', status=401, headers={'WWW-Authenticate': 'Bearer'})
    return HttpResponse(_request_metrics() + generate_latest(_app_registry), content_type=CONTENT_TYPE_LATEST)
