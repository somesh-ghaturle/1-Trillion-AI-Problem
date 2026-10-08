"""
Read metric definitions from a dbt project's semantic layer (MetricFlow YAML) and render
each as a formula in the shape the reconciliation engine parses: "AGG(expr) WHERE cond".

Supports both YAML layouts:
  - dbt <= 1.11: top-level `semantic_models` (measures, dimensions) + `metrics` with `type_params`
  - dbt >= 1.12: `agg`/`expr` directly on simple metrics; metrics and column dimensions under `models`

Only reads YAML (yaml.safe_load). It never runs dbt or connects to a warehouse.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SKIP_DIRS = {'target', 'dbt_packages', 'dbt_modules', 'logs', '.venv', 'venv', 'node_modules', '.git'}

_AGG = {
    'sum': 'SUM({})', 'count': 'COUNT({})', 'count_distinct': 'COUNT(DISTINCT {})',
    'average': 'AVG({})', 'avg': 'AVG({})', 'min': 'MIN({})', 'max': 'MAX({})', 'median': 'MEDIAN({})',
    'sum_boolean': 'SUM(CAST({} AS INT))',
}
_JINJA_REF = re.compile(r"\{\{\s*(?:Dimension|TimeDimension|Entity)\(\s*['\"]([^'\"]+)['\"][^}]*\}\}")
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*$')


@dataclass
class DbtMetric:
    name: str
    type: str
    formula: str
    label: str = ''
    description: str = ''
    file: str = ''
    notes: list = field(default_factory=list)


@dataclass
class DbtProject:
    metrics: dict = field(default_factory=dict)      # name -> raw metric dict (+ '_file')
    measures: dict = field(default_factory=dict)     # name -> {'agg', 'expr'}
    dimensions: dict = field(default_factory=dict)   # name -> SQL expr
    errors: list = field(default_factory=list)

    def add_document(self, doc, filename):
        if not isinstance(doc, dict):
            return
        for sm in doc.get('semantic_models') or []:
            for m in sm.get('measures') or []:
                self.measures[m['name']] = {'agg': m.get('agg', 'sum'), 'expr': m.get('expr') or m['name'],
                                            'agg_params': m.get('agg_params') or {}}
            for d in sm.get('dimensions') or []:
                self.dimensions[d['name']] = str(d.get('expr') or d['name'])
        for metric in doc.get('metrics') or []:
            self.metrics[metric['name']] = {**metric, '_file': filename}
        for model in doc.get('models') or []:  # dbt >= 1.12: semantics live on the model
            for col in model.get('columns') or []:
                dim = col.get('dimension')
                if isinstance(dim, dict):
                    self.dimensions[dim.get('name') or col['name']] = col['name']
            for metric in model.get('metrics') or []:
                self.metrics[metric['name']] = {**metric, '_file': filename}

    # --- rendering -------------------------------------------------------

    def render_filter(self, raw):
        """`{{ Dimension('order__status') }} = 'x'` -> `status = 'x'` (using the dimension's SQL expr)."""
        def resolve(match):
            name = match.group(1).split('__')[-1]
            expr = self.dimensions.get(name, name)
            return expr if _IDENTIFIER.match(expr) else f'({expr})'
        text = _JINJA_REF.sub(resolve, str(raw)).strip().strip('"').strip()
        return f'({text})' if re.search(r'\bor\b', text, re.IGNORECASE) else text

    def _filters(self, *raws):
        out = []
        for raw in raws:
            for item in (raw if isinstance(raw, list) else [raw]):
                if item:
                    out.append(self.render_filter(item))
        return out

    def _aggregate(self, agg, expr, agg_params=None):
        if agg == 'percentile':
            return f"PERCENTILE({expr}, {(agg_params or {}).get('percentile', 0.5)})"
        return _AGG.get(agg, f'{str(agg).upper()}({{}})').format(expr)

    @staticmethod
    def _ref(value):
        """A metric/measure reference is either 'name' or {'name': ..., 'filter': ...}."""
        return (value, None) if isinstance(value, str) else (value.get('name'), value.get('filter'))

    def render(self, name, _seen=()):
        metric = self.metrics[name]
        mtype = metric.get('type', 'simple')
        params = metric.get('type_params') or {}
        notes = []
        if name in _seen:
            raise ValueError(f'circular metric reference: {" -> ".join(_seen + (name,))}')

        if mtype in ('simple', 'cumulative', 'conversion'):
            if 'agg' in metric:  # dbt >= 1.12
                measure = self._aggregate(metric['agg'], metric.get('expr') or name, metric.get('agg_params'))
                measure_filter = None
            else:
                ref = params.get('measure') or (params.get('conversion_type_params') or {}).get('base_measure')
                if ref is None:
                    raise ValueError(f'{mtype} metric has no measure')
                measure_name, measure_filter = self._ref(ref)
                if measure_name not in self.measures:
                    raise ValueError(f'measure "{measure_name}" is not defined in any semantic model')
                m = self.measures[measure_name]
                measure = self._aggregate(m['agg'], m['expr'], m['agg_params'])
            if mtype != 'simple':
                notes.append(f'{mtype} metric: only the base measure is compared')
            filters = self._filters(metric.get('filter'), measure_filter)
            formula = measure + (' WHERE ' + ' AND '.join(filters) if filters else '')

        elif mtype == 'ratio':
            parts = []
            for side in ('numerator', 'denominator'):
                ref = metric.get(side) or params.get(side)
                if ref is None:
                    raise ValueError(f'ratio metric has no {side}')
                ref_name, ref_filter = self._ref(ref)
                if ref_name not in self.metrics:
                    raise ValueError(f'{side} metric "{ref_name}" is not defined')
                inner = self.render(ref_name, _seen + (name,)).formula
                extra = self._filters(ref_filter)
                if extra:
                    inner += (' AND ' if ' WHERE ' in inner else ' WHERE ') + ' AND '.join(extra)
                parts.append(f'({inner})' if ' WHERE ' in inner else inner)
            formula = ' / '.join(parts)
            outer = self._filters(metric.get('filter'))
            if outer:
                notes.append('ratio-level filter applies to both sides: ' + ' AND '.join(outer))

        elif mtype == 'derived':
            formula = str(metric.get('expr') or params.get('expr') or '')
            refs = [self._ref(r)[0] for r in (metric.get('input_metrics') or params.get('metrics') or [])]
            notes.append('derived metric: expression over metrics ' + ', '.join(refs) if refs else 'derived metric')

        else:
            raise ValueError(f'unsupported metric type "{mtype}"')

        return DbtMetric(name=name, type=mtype, formula=formula, label=metric.get('label', ''),
                         description=metric.get('description', '') or '', file=metric.get('_file', ''), notes=notes)

    def rendered_metrics(self):
        """All metrics rendered; a metric that can't be rendered goes to errors instead."""
        out = []
        for name in sorted(self.metrics):
            try:
                out.append(self.render(name))
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                self.errors.append(f'{self.metrics[name].get("_file", "")}: metric "{name}": {e}')
        return out


def _parse_documents(project, text, filename):
    try:
        for doc in yaml.safe_load_all(text):
            project.add_document(doc, filename)
    except yaml.YAMLError as e:
        hint = ' (Jinja like {{ Dimension(...) }} must be quoted in YAML)' if '{{' in text else ''
        project.errors.append(f'{filename}: invalid YAML{hint}: {str(e).splitlines()[0]}')
    except (KeyError, TypeError, AttributeError) as e:
        project.errors.append(f'{filename}: unexpected structure: {e}')


def load_project(path):
    """Parse every .yml/.yaml file under a dbt project directory (or a single file)."""
    project = DbtProject()
    root = Path(path)
    files = [root] if root.is_file() else sorted(
        p for p in root.rglob('*') if p.suffix in ('.yml', '.yaml') and not SKIP_DIRS & set(p.relative_to(root).parts)
    )
    for f in files:
        _parse_documents(project, f.read_text(encoding='utf-8'), str(f.relative_to(root.parent if root.is_file() else root)))
    return project


def load_texts(named_texts):
    """Parse uploaded files: iterable of (filename, text)."""
    project = DbtProject()
    for filename, text in named_texts:
        _parse_documents(project, text, filename)
    return project


def import_metrics(project, source_name='dbt Semantic Layer', dry_run=False):
    """
    Store each dbt metric as the SemanticDefinition of the governance metric with the same name,
    under one DataSource. Unmatched metrics are reported, never created. Returns a stats dict.
    """
    from core.models import DataSource, GovernanceMetric, SemanticDefinition

    rendered = project.rendered_metrics()
    governance = {m.name.lower(): m for m in GovernanceMetric.objects.filter(is_active=True)}
    stats = {'imported': [], 'unmatched': [], 'errors': list(project.errors)}
    source = None
    if not dry_run:
        source, _ = DataSource.objects.get_or_create(
            name=source_name, defaults={'source_type': 'dbt', 'description': 'Metric definitions from the dbt Semantic Layer'})

    for metric in rendered:
        target = governance.get(metric.name.lower())
        if target is None:
            stats['unmatched'].append(metric)
            continue
        stats['imported'].append((target, metric))
        if dry_run:
            continue
        description = metric.description
        if metric.notes:
            description = (description + '\n\n' if description else '') + 'Note: ' + '; '.join(metric.notes)
        SemanticDefinition.objects.update_or_create(
            governance_metric=target, source=source,
            defaults={'local_name': metric.name, 'local_formula': metric.formula,
                      'local_description': f'{description}\n\nImported from dbt: {metric.file}'.strip(),
                      'definition_type': 'metric'},
        )
    return stats
