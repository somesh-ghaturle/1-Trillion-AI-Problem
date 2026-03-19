from django.core.management.base import BaseCommand
import pathlib
import importlib.util


class Command(BaseCommand):
    help = 'Export governance configuration to JSON (uses GovernanceFramework defaults)'

    def add_arguments(self, parser):
        parser.add_argument('--out', help='Output file path', default='governance_export.json')

    def handle(self, *args, **options):
        out_path = options.get('out')

        try:
            # Use GovernanceFramework from data_governance
            from data_governance import GovernanceFramework

            framework = GovernanceFramework()
            framework.register_standard_metrics()
            framework.export_governance_config(out_path)

            self.stdout.write(self.style.SUCCESS(f'Governance config exported to {out_path}'))

        except Exception as e:
            self.stderr.write(f'Error exporting governance config: {e}')
            raise
