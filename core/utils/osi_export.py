"""
OSI (Open Semantic Interchange) Compatible Export/Import

Generates a vendor-neutral semantic model specification that standardizes
how semantic metadata is defined and shared — ensuring consistent business
logic across AI and BI applications.

Based on the OSI initiative by Snowflake, Salesforce, dbt Labs, BlackRock, etc.
"""
import json
from datetime import datetime


def export_osi_spec(governance_metrics, semantic_definitions, data_sources, lineage_flows=None):
    """
    Export the semantic model in an OSI-compatible JSON format.

    Returns a dict representing the full semantic interchange specification.
    """
    spec = {
        'osi_version': '1.0',
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'organization': 'Trust Control Center',
        'description': 'Semantic model specification for cross-system metric consistency',
        'data_sources': [],
        'metrics': [],
        'semantic_mappings': [],
        'lineage': [],
    }

    # Data sources
    for source in data_sources:
        spec['data_sources'].append({
            'id': f'source_{source.pk}',
            'name': source.name,
            'type': source.source_type,
            'description': source.description,
            'is_active': source.is_active,
        })

    # Canonical metric definitions
    for metric in governance_metrics:
        metric_entry = {
            'id': metric.name,
            'display_name': metric.display_name,
            'description': metric.description,
            'data_type': metric.data_type,
            'canonical_formula': metric.formula,
            'category': metric.category,
            'owner': metric.owner,
            'tags': metric.tags,
        }
        spec['metrics'].append(metric_entry)

    # Semantic mappings (how each metric is implemented per source)
    for defn in semantic_definitions:
        mapping = {
            'metric_id': defn.governance_metric.name,
            'source_id': f'source_{defn.source.pk}',
            'source_name': defn.source.name,
            'definition_type': defn.definition_type,
            'local_name': defn.local_name,
            'local_formula': defn.local_formula,
            'local_description': defn.local_description,
            'column_mapping': defn.column_mapping,
            'filters': defn.filters,
            'is_consistent': defn.is_consistent,
            'consistency_notes': defn.consistency_notes,
        }
        spec['semantic_mappings'].append(mapping)

    # Data lineage
    if lineage_flows:
        for flow in lineage_flows:
            lineage_entry = {
                'from_source': f'source_{flow.source_from.pk}',
                'to_source': f'source_{flow.source_to.pk}',
                'from_name': flow.source_from.name,
                'to_name': flow.source_to.name,
                'flow_type': flow.flow_type,
                'description': flow.description,
                'schedule': flow.schedule,
                'is_active': flow.is_active,
            }
            spec['lineage'].append(lineage_entry)

    return spec


def import_osi_spec(spec_data, create_sources=False):
    """
    Import an OSI-compatible JSON specification.

    Returns a dict with counts of created/updated objects.

    Note: This function requires Django model imports and must be called
    within a Django context.
    """
    from core.models import GovernanceMetric, DataSource, SemanticDefinition

    stats = {
        'metrics_created': 0,
        'metrics_updated': 0,
        'sources_created': 0,
        'mappings_created': 0,
        'errors': [],
    }

    # Import sources if requested
    source_map = {}
    if create_sources and 'data_sources' in spec_data:
        for src in spec_data['data_sources']:
            obj, created = DataSource.objects.get_or_create(
                name=src['name'],
                defaults={
                    'source_type': src.get('type', 'other'),
                    'description': src.get('description', ''),
                }
            )
            source_map[src['id']] = obj
            if created:
                stats['sources_created'] += 1
    else:
        # Map existing sources by name
        for source in DataSource.objects.all():
            for src in spec_data.get('data_sources', []):
                if src['name'] == source.name:
                    source_map[src['id']] = source

    # Import metrics
    for metric_data in spec_data.get('metrics', []):
        obj, created = GovernanceMetric.objects.update_or_create(
            name=metric_data['id'],
            defaults={
                'display_name': metric_data.get('display_name', metric_data['id']),
                'description': metric_data.get('description', ''),
                'data_type': metric_data.get('data_type', 'numeric'),
                'formula': metric_data.get('canonical_formula', ''),
                'category': metric_data.get('category', ''),
                'owner': metric_data.get('owner', ''),
                'tags': metric_data.get('tags', []),
            }
        )
        if created:
            stats['metrics_created'] += 1
        else:
            stats['metrics_updated'] += 1

    # Import semantic mappings
    for mapping in spec_data.get('semantic_mappings', []):
        source_id = mapping.get('source_id')
        source = source_map.get(source_id)
        if not source:
            stats['errors'].append(f'Source not found for mapping: {source_id}')
            continue

        try:
            metric = GovernanceMetric.objects.get(name=mapping['metric_id'])
        except GovernanceMetric.DoesNotExist:
            stats['errors'].append(f'Metric not found: {mapping["metric_id"]}')
            continue

        SemanticDefinition.objects.update_or_create(
            governance_metric=metric,
            source=source,
            defaults={
                'definition_type': mapping.get('definition_type', 'metric'),
                'local_name': mapping.get('local_name', ''),
                'local_formula': mapping.get('local_formula', ''),
                'local_description': mapping.get('local_description', ''),
                'column_mapping': mapping.get('column_mapping', {}),
                'filters': mapping.get('filters', []),
                'is_consistent': mapping.get('is_consistent', True),
                'consistency_notes': mapping.get('consistency_notes', ''),
            }
        )
        stats['mappings_created'] += 1

    return stats
