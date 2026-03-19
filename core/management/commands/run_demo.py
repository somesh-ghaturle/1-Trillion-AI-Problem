from django.core.management.base import BaseCommand
import sys


class Command(BaseCommand):
    help = 'Run the example_usage demo from the repository root'

    def handle(self, *args, **options):
        try:
            # Import and run example_usage.py from project root
            import importlib.util
            import pathlib
            spec = importlib.util.spec_from_file_location('example_usage', str(pathlib.Path.cwd() / 'example_usage.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'main'):
                module.main()
            else:
                self.stdout.write(self.style.SUCCESS('Imported example_usage.py (no main() found)'))
        except Exception as e:
            self.stderr.write(f'Error running example_usage: {e}')
            sys.exit(1)
