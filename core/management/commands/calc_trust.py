from django.core.management.base import BaseCommand
import pandas as pd
import pathlib
import importlib.util


class Command(BaseCommand):
    help = 'Calculate trust score for dataset (uses sample data by default or a CSV)'

    def add_arguments(self, parser):
        parser.add_argument('--csv', help='Path to CSV file to score', default=None)

    def handle(self, *args, **options):
        csv_path = options.get('csv')

        try:
            if csv_path:
                df = pd.read_csv(csv_path)
                self.stdout.write(self.style.SUCCESS(f'Loaded CSV: {csv_path} ({len(df)} rows)'))
            else:
                spec = importlib.util.spec_from_file_location('example_usage', str(pathlib.Path.cwd() / 'example_usage.py'))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                snowflake_df, _ = module.create_sample_data()
                df = snowflake_df
                self.stdout.write(self.style.SUCCESS(f'Using built-in sample data ({len(df)} rows)'))

            from trust_scoring import TrustScoringEngine

            engine = TrustScoringEngine()
            config = {
                'critical_columns': ['customer_id', 'revenue', 'order_count'],
                'timestamp_column': 'last_purchase_date',
                'max_age_days': 90,
                'key_columns': ['customer_id']
            }

            trust_score = engine.calculate_trust_score(df, config)
            report = engine.generate_trust_report(trust_score)
            self.stdout.write(report)
            self.stdout.write(self.style.SUCCESS(f'Trust score: {trust_score.overall_score}/100'))

        except Exception as e:
            self.stderr.write(f'Error calculating trust score: {e}')
            raise
