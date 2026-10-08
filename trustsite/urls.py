from django.contrib import admin
from django.urls import path, include

from core import monitoring

urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz', monitoring.healthz, name='healthz'),
    path('metrics', monitoring.metrics, name='metrics'),
    path('', include('core.urls')),
]
