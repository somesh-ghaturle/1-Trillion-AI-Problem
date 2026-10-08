"""
Alerts for data-trust events, sent to a webhook (JSON, Slack-compatible `text`) and/or email.

Configured by environment (both optional; with neither set, alerts are only logged):
  ALERT_WEBHOOK_URL   http(s) URL that receives a JSON POST
  ALERT_EMAILS        comma-separated recipients (uses Django's EMAIL_* settings)

Events (from post_save signals, sent after the transaction commits):
  validation_failed         a validation run did not pass
  score_drop                a source's latest trust/quality score is an anomaly (see utils.insights)
  reconciliation_critical   a reconciliation run found critical divergences
"""
import json
import logging
import threading
import urllib.request
from contextlib import contextmanager

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)
_state = threading.local()


@contextmanager
def suppressed():
    """Silence alerts for bulk work such as seeding sample data."""
    previous = getattr(_state, 'suppressed', False)
    _state.suppressed = True
    try:
        yield
    finally:
        _state.suppressed = previous


def deliver(kind, title, details):
    """Send one alert to every configured channel. Never raises: alerts must not break the save that caused them."""
    payload = {'kind': kind, 'title': title, 'details': details, 'text': f'[Trust Control Center] {title}'}
    logger.warning('ALERT %s: %s', kind, title)
    url = settings.ALERT_WEBHOOK_URL
    if url:
        try:
            if not url.startswith(('https://', 'http://')):
                raise ValueError('ALERT_WEBHOOK_URL must be http(s)')
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), method='POST',
                                             headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(request, timeout=5).close()
        except Exception:
            logger.exception('alert webhook failed')
    if settings.ALERT_EMAILS:
        try:
            body = title + '\n\n' + '\n'.join(f'{k}: {v}' for k, v in details.items())
            send_mail(f'[Trust Control Center] {title}', body, None, settings.ALERT_EMAILS)
        except Exception:
            logger.exception('alert email failed')


def notify(kind, title, details):
    if getattr(_state, 'suppressed', False):
        return
    transaction.on_commit(lambda: dispatch(kind, title, details))


def dispatch(kind, title, details):
    deliver(kind, title, details)  # replaced by a background task when Celery is configured


def _check_score_drop(source, measure):
    from .utils.insights import detect_anomalies
    for a in detect_anomalies():
        if a.source == source.name and a.measure == measure:
            notify('score_drop', f'{a.source} {a.measure} dropped to {a.latest:.1f}% ({a.drop} below usual)', a.to_dict())


@receiver(post_save, sender='core.ValidationResult')
def on_validation(sender, instance, created, **kwargs):
    if not created or getattr(_state, 'suppressed', False):
        return
    if not instance.passed:
        notify('validation_failed', f'Validation failed for {instance.source.name} (quality {instance.quality_score:.1f}%)',
               {'source': instance.source.name, 'quality_score': round(instance.quality_score, 1),
                'failed_rules': instance.failed_rules, 'total_rules': instance.total_rules})
    _check_score_drop(instance.source, 'data quality')


@receiver(post_save, sender='core.TrustScore')
def on_trust_score(sender, instance, created, **kwargs):
    if created and not getattr(_state, 'suppressed', False):
        _check_score_drop(instance.source, 'trust score')


@receiver(post_save, sender='core.ReconciliationRun')
def on_reconciliation(sender, instance, created, **kwargs):
    if not created or getattr(_state, 'suppressed', False):
        return
    critical = [d for d in instance.divergences or [] if d.get('severity') == 'critical']
    if critical:
        name = instance.governance_metric.name
        notify('reconciliation_critical', f'{len(critical)} critical divergence(s) in "{name}"',
               {'metric': name, 'consistency_score': instance.consistency_score,
                'examples': '; '.join(d.get('detail', '') for d in critical[:3])})
