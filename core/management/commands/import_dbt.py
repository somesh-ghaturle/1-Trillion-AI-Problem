from django.core.management.base import BaseCommand, CommandError

from core.utils.dbt_import import import_metrics, load_project


class Command(BaseCommand):
    help = "Import metric definitions from a dbt project's semantic layer YAML as a data source's semantic mappings"

    def add_arguments(self, parser):
        parser.add_argument('path', help='dbt project directory (or a single .yml file)')
        parser.add_argument('--source', default='dbt Semantic Layer', help='Data source name to import into')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without saving')

    def handle(self, path, source, dry_run, **options):
        from pathlib import Path
        if not Path(path).exists():
            raise CommandError(f'{path} does not exist')
        stats = import_metrics(load_project(path), source_name=source, dry_run=dry_run)

        verb = 'Would import' if dry_run else 'Imported'
        self.stdout.write(self.style.SUCCESS(f'{verb} {len(stats["imported"])} metric(s) into "{source}":'))
        for governance, metric in stats['imported']:
            self.stdout.write(f'  {governance.name:30} {metric.formula}')
        if stats['unmatched']:
            self.stdout.write(self.style.WARNING(
                f'{len(stats["unmatched"])} dbt metric(s) have no governance metric with the same name (skipped):'))
            for metric in stats['unmatched']:
                self.stdout.write(f'  {metric.name:30} {metric.formula}')
        for error in stats['errors']:
            self.stderr.write(self.style.ERROR(f'  {error}'))
        if stats['imported'] and not dry_run:
            self.stdout.write('Run reconciliation to compare them with the other sources.')
