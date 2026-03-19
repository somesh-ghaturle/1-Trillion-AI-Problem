from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('sources/', views.data_sources_list, name='data_sources'),
    path('sources/<int:pk>/', views.data_source_detail, name='data_source_detail'),
    path('sources/<int:pk>/validate/', views.validate_data, name='validate_data'),
    path('sources/<int:pk>/trust/', views.calculate_trust, name='calculate_trust'),
    path('governance/', views.governance_metrics, name='governance_metrics'),

    # Legacy/Demo UI
    path('ui/', views.ui, name='ui'),
    path('api/', views.index, name='index'),

    # API endpoints
    path('api/validate/', api_views.validate_endpoint, name='api-validate'),
    path('api/trust/', api_views.trust_endpoint, name='api-trust'),
    path('api/governance/', api_views.governance_endpoint, name='api-governance'),
]
