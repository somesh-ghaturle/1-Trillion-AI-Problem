from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

# DRF Router
router = DefaultRouter()
router.register(r'sources', api_views.DataSourceViewSet)
router.register(r'validations', api_views.ValidationResultViewSet)
router.register(r'trust-scores', api_views.TrustScoreViewSet)
router.register(r'governance-metrics', api_views.GovernanceMetricViewSet)
router.register(r'semantic-definitions', api_views.SemanticDefinitionViewSet)
router.register(r'reconciliations', api_views.ReconciliationRunViewSet)
router.register(r'lineage', api_views.DataLineageViewSet)

urlpatterns = [
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('sources/', views.data_sources_list, name='data_sources'),
    path('sources/<int:pk>/', views.data_source_detail, name='data_source_detail'),
    path('sources/<int:pk>/validate/', views.validate_data, name='validate_data'),
    path('sources/<int:pk>/trust/', views.calculate_trust, name='calculate_trust'),
    path('governance/', views.governance_metrics, name='governance_metrics'),

    # Semantic definitions (OSI mappings)
    path('semantic/', views.semantic_definitions, name='semantic_definitions'),

    # Reconciliation
    path('reconciliation/', views.reconciliation_dashboard, name='reconciliation_dashboard'),
    path('reconciliation/run/', views.run_reconciliation, name='run_reconciliation'),

    # Data Lineage
    path('lineage/', views.lineage_view, name='lineage'),

    # OSI Export/Import
    path('osi/', views.osi_export_view, name='osi_export'),
    path('osi/import/', views.osi_import_view, name='osi_import'),

    # API endpoints (DRF)
    path('api/', api_views.api_health, name='index'),
    path('api/v1/', include(router.urls)),
    path('api/docs/', include('rest_framework.urls', namespace='rest_framework')),
]
