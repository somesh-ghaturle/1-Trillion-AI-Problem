"""
Download app data as CSV, Excel, or Parquet: /export/<dataset>.<csv|xlsx|parquet>

Read-only, so public like the rest of the read views. Text cells that a spreadsheet would run as a
formula (=, +, -, @ ...) are prefixed with an apostrophe in CSV and Excel; Parquet stores raw values.
"""
import io
import json

import pandas as pd
from django.http import Http404, HttpResponse

from .models import GovernanceMetric, SemanticDefinition, TrustScore, ValidationResult

FORMATS = {
    'csv': 'text/csv',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'parquet': 'application/vnd.apache.parquet',
}


def reconciliation_rows():
    """Latest run per active metric, one row per divergence (a clean run gets one summary row)."""
    rows = []
    # ponytail: one query per metric; fine for tens of metrics, use a Subquery if this grows to thousands
    for metric in GovernanceMetric.objects.filter(is_active=True).order_by('name'):
        run = metric.reconciliations.order_by('-run_at', '-pk').first()
        if not run:
            continue
        base = {'metric': metric.name, 'run_at': run.run_at, 'status': run.status,
                'consistency_score': run.consistency_score}
        keys = ['source_a', 'source_b', 'divergence_type', 'severity', 'detail', 'recommendation']
        for d in run.divergences or [{}]:
            rows.append({**base, **{k: d.get(k, '') for k in keys}})
    return rows


DATASETS = {
    'trust-scores': lambda: TrustScore.objects.order_by('-calculated_at').values(
        'source__name', 'calculated_at', 'overall_score', 'trust_level', 'completeness_score', 'accuracy_score',
        'consistency_score', 'timeliness_score', 'validity_score', 'uniqueness_score', 'issues'),
    'validations': lambda: ValidationResult.objects.order_by('-timestamp').values(
        'source__name', 'timestamp', 'passed', 'quality_score', 'total_rules', 'passed_rules', 'failed_rules'),
    'governance-metrics': lambda: GovernanceMetric.objects.order_by('name').values(
        'name', 'display_name', 'description', 'formula', 'data_type', 'category', 'owner', 'tags', 'is_active'),
    'semantic-definitions': lambda: SemanticDefinition.objects.order_by('governance_metric__name', 'source__name').values(
        'governance_metric__name', 'source__name', 'local_name', 'local_formula', 'local_description',
        'is_consistent', 'last_verified'),
    'reconciliation': reconciliation_rows,
}


def _spreadsheet_safe(value):
    if isinstance(value, str) and value[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


def build_frame(dataset):
    df = pd.DataFrame(list(DATASETS[dataset]()))
    df.columns = [c.replace('__', '_') for c in df.columns]
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_convert('UTC').dt.tz_localize(None)  # Excel/Parquet-friendly, UTC
        elif df[col].map(lambda v: isinstance(v, (list, dict))).any():
            df[col] = df[col].map(lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v)
    return df


def export_view(request, dataset, fmt):
    if dataset not in DATASETS or fmt not in FORMATS:
        raise Http404
    df = build_frame(dataset)
    buffer = io.BytesIO()
    if fmt == 'parquet':
        df.to_parquet(buffer, index=False)
    else:
        df = df.map(_spreadsheet_safe)
        if fmt == 'csv':
            buffer.write(df.to_csv(index=False).encode())
        else:
            df.to_excel(buffer, index=False, sheet_name=dataset[:31], engine='openpyxl')
    response = HttpResponse(buffer.getvalue(), content_type=FORMATS[fmt])
    response['Content-Disposition'] = f'attachment; filename="{dataset}.{fmt}"'
    return response
