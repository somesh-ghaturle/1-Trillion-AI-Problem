"""
Bulk-import semantic mappings from CSV. Columns match /export/semantic-definitions.csv, so an export
can be edited in a spreadsheet and uploaded back:

    governance_metric_name, source_name, local_name, local_formula, local_description

All-or-nothing: if any row is invalid nothing is saved and every problem is reported by row number.
"""
import csv
import io

from django.db import transaction

from core.models import DataSource, GovernanceMetric, SemanticDefinition

REQUIRED = ('governance_metric_name', 'source_name', 'local_name')
MAX_ROWS = 5000
FORMULA_CHARS = ('=', '+', '-', '@', '\t', '\r')


def _unescape(value):
    """Undo the export's spreadsheet-safety prefix ("'=..." -> "=...")."""
    value = (value or '').strip()
    if len(value) > 1 and value[0] == "'" and value[1] in FORMULA_CHARS:
        return value[1:]
    return value


def import_semantic_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        return {'created': 0, 'updated': 0, 'errors': [f'missing column(s): {", ".join(missing)}']}

    metrics = {m.name.lower(): m for m in GovernanceMetric.objects.all()}
    sources = {s.name.lower(): s for s in DataSource.objects.all()}
    rows, errors = [], []
    for line, row in enumerate(reader, start=2):  # header is line 1
        if line - 1 > MAX_ROWS:
            errors.append(f'more than {MAX_ROWS} rows')
            break
        values = {k: _unescape(row.get(k)) for k in (*REQUIRED, 'local_formula', 'local_description')}
        if not any(values.values()):
            continue  # blank line
        metric = metrics.get(values['governance_metric_name'].lower())
        source = sources.get(values['source_name'].lower())
        problems = [f'unknown governance metric "{values["governance_metric_name"]}"'] if not metric else []
        problems += [f'unknown source "{values["source_name"]}"'] if not source else []
        problems += ['local_name is empty'] if not values['local_name'] else []
        if problems:
            errors.append(f'row {line}: ' + '; '.join(problems))
        else:
            rows.append((metric, source, values))

    if errors:
        return {'created': 0, 'updated': 0, 'errors': errors}
    created = updated = 0
    with transaction.atomic():
        for metric, source, v in rows:
            _, was_created = SemanticDefinition.objects.update_or_create(
                governance_metric=metric, source=source,
                defaults={'local_name': v['local_name'], 'local_formula': v['local_formula'],
                          'local_description': v['local_description']})
            created += was_created
            updated += not was_created
    return {'created': created, 'updated': updated, 'errors': []}
