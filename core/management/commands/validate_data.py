from django.core.management.base import BaseCommand
import pandas as pd
import pathlib
import importlib.util


class Command(BaseCommand):
    help = 'Run data quality validation (uses example sample data by default or a CSV file)'

    def add_arguments(self, parser):
        parser.add_argument('--csv', help='Path to CSV file to validate', default=None)

    def handle(self, *args, **options):
        csv_path = options.get('csv')

        try:
            if csv_path:
                df = pd.read_csv(csv_path)
                self.stdout.write(self.style.SUCCESS(f'Loaded CSV: {csv_path} ({len(df)} rows)'))
            else:
                # Load sample data from example_usage
                spec = importlib.util.spec_from_file_location('example_usage', str(pathlib.Path.cwd() / 'example_usage.py'))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                snowflake_df, _ = module.create_sample_data()
                df = snowflake_df
                self.stdout.write(self.style.SUCCESS(f'Using built-in sample data ({len(df)} rows)'))

            from data_quality_validator import DataQualityValidator, generate_validation_report

            validator = DataQualityValidator()
            # Simple default config; real projects should pass config via file or args
            config = {
                'required_columns': ['customer_id', 'revenue', 'order_count', 'customer_segment'],
                'key_columns': ['customer_id'],
                'value_ranges': {'revenue': (0, 100000), 'order_count': (0, 1000)},
                'expected_types': {'customer_id': 'int', 'revenue': 'float', 'order_count': 'int'}
            }

            results, score = validator.run_validation_suite(df, config)
            report = generate_validation_report(results, score)
            self.stdout.write(report)
            self.stdout.write(self.style.SUCCESS(f'Quality score: {score}/100'))

        except Exception as e:
            self.stderr.write(f'Error running validation: {e}')
            raise
