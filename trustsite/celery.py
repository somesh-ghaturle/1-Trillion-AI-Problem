"""Celery app. Workers run with: celery -A trustsite worker. Without REDIS_URL, tasks run inline (eager)."""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustsite.settings')

app = Celery('trustsite')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
