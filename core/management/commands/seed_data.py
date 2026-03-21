"""
Seed realistic enterprise data that demonstrates the $1T AI Problem.

Creates data sources, governance metrics with intentional cross-source
inconsistencies, semantic definitions, lineage flows, validation results,
trust scores, and runs reconciliation to surface divergences.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from core.models import (
    DataSource, ValidationResult, TrustScore, GovernanceMetric,
    SemanticDefinition, ReconciliationRun, DataLineage,
)
from core.utils.reconciliation import ReconciliationEngine


class Command(BaseCommand):
    help = 'Populate the database with realistic enterprise sample data'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete all existing data first')

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing data...')
            DataLineage.objects.all().delete()
            ReconciliationRun.objects.all().delete()
            SemanticDefinition.objects.all().delete()
            TrustScore.objects.all().delete()
            ValidationResult.objects.all().delete()
            GovernanceMetric.objects.all().delete()
            DataSource.objects.all().delete()

        sources = self._create_sources()
        metrics = self._create_governance_metrics()
        self._create_semantic_definitions(metrics, sources)
        self._create_lineage(sources, metrics)
        self._create_validations(sources)
        self._create_trust_scores(sources)
        self._run_reconciliation(metrics)

        self.stdout.write(self.style.SUCCESS(
            '\nSample data created successfully!\n'
            f'  - {DataSource.objects.count()} data sources\n'
            f'  - {GovernanceMetric.objects.count()} governance metrics\n'
            f'  - {SemanticDefinition.objects.count()} semantic definitions\n'
            f'  - {DataLineage.objects.count()} lineage flows\n'
            f'  - {ValidationResult.objects.count()} validation results\n'
            f'  - {TrustScore.objects.count()} trust scores\n'
            f'  - {ReconciliationRun.objects.count()} reconciliation runs\n'
        ))

    def _create_sources(self):
        self.stdout.write('Creating data sources...')
        source_data = [
            {
                'name': 'Snowflake DWH',
                'source_type': 'snowflake',
                'connector': 'snowflake-connector-python',
                'description': 'Enterprise data warehouse. Primary source of truth for financial and customer analytics. Contains 500+ tables across 12 schemas.',
            },
            {
                'name': 'Tableau Cloud',
                'source_type': 'tableau',
                'connector': 'tableau-api-lib',
                'description': 'Business intelligence and reporting platform. 200+ dashboards used by executives and analysts. Pulls data from Snowflake and PostgreSQL.',
            },
            {
                'name': 'PostgreSQL Production',
                'source_type': 'database',
                'connector': 'psycopg2',
                'description': 'Primary operational database for the SaaS platform. Handles 50K+ transactions per hour. Source of transactional revenue data.',
            },
            {
                'name': 'Salesforce CRM',
                'source_type': 'api',
                'connector': 'simple-salesforce',
                'description': 'Customer relationship management system. Contains customer lifecycle data, deal pipeline, and revenue forecasts from 200+ sales reps.',
            },
            {
                'name': 'Stripe Payments',
                'source_type': 'api',
                'connector': 'stripe-python',
                'description': 'Payment processing platform. Handles all subscription billing, one-time charges, and refunds. Source of ground-truth payment data.',
            },
            {
                'name': 'HubSpot Marketing',
                'source_type': 'api',
                'connector': 'hubspot-api-client',
                'description': 'Marketing automation platform. Tracks leads, campaigns, attribution, and marketing-sourced revenue across all channels.',
            },
            {
                'name': 'Google BigQuery',
                'source_type': 'database',
                'connector': 'google-cloud-bigquery',
                'description': 'Analytics data lake for product usage, event tracking, and behavioral analytics. Ingests 10M+ events per day.',
            },
            {
                'name': 'CSV Uploads',
                'source_type': 'file',
                'connector': 'pandas',
                'description': 'Manual data uploads from finance team for quarterly reconciliation, budget data, and ad-hoc analysis.',
            },
        ]
        sources = {}
        for data in source_data:
            source, _ = DataSource.objects.get_or_create(
                name=data['name'],
                defaults=data,
            )
            sources[source.name] = source
        return sources

    def _create_governance_metrics(self):
        self.stdout.write('Creating governance metrics...')
        metric_data = [
            {
                'name': 'total_revenue',
                'display_name': 'Total Revenue',
                'description': 'Sum of all completed revenue transactions including subscriptions, one-time charges, and professional services. Excludes refunds, credits, and pending transactions.',
                'formula': "SUM(amount) WHERE status = 'completed' AND type IN ('subscription', 'one_time', 'services')",
                'data_type': 'numeric',
                'category': 'Revenue',
                'owner': 'Finance Team',
            },
            {
                'name': 'monthly_recurring_revenue',
                'display_name': 'Monthly Recurring Revenue (MRR)',
                'description': 'Total recurring subscription revenue normalized to a monthly amount. The single most important SaaS metric. Includes upgrades and downgrades, excludes one-time fees.',
                'formula': "SUM(subscription_amount / billing_interval_months) WHERE subscription_status = 'active'",
                'data_type': 'numeric',
                'category': 'Revenue',
                'owner': 'Finance Team',
            },
            {
                'name': 'customer_count',
                'display_name': 'Active Customer Count',
                'description': 'Total number of unique active customers with at least one active subscription or paid account. A customer must have logged in within the last 90 days.',
                'formula': "COUNT(DISTINCT customer_id) WHERE subscription_status = 'active' AND last_login >= DATEADD(day, -90, CURRENT_DATE)",
                'data_type': 'numeric',
                'category': 'Customer',
                'owner': 'Customer Success',
            },
            {
                'name': 'churn_rate',
                'display_name': 'Monthly Churn Rate',
                'description': 'Percentage of customers who cancelled or did not renew their subscription in a given month. Calculated as churned customers divided by total customers at the start of the month.',
                'formula': "COUNT(churned_customers) / COUNT(total_customers_at_period_start) * 100",
                'data_type': 'numeric',
                'category': 'Customer',
                'owner': 'Customer Success',
            },
            {
                'name': 'customer_acquisition_cost',
                'display_name': 'Customer Acquisition Cost (CAC)',
                'description': 'Total sales and marketing spend divided by the number of new customers acquired in the period. Includes salaries, ad spend, tools, and events.',
                'formula': "SUM(sales_marketing_spend) / COUNT(new_customers)",
                'data_type': 'numeric',
                'category': 'Marketing',
                'owner': 'Marketing Team',
            },
            {
                'name': 'net_promoter_score',
                'display_name': 'Net Promoter Score (NPS)',
                'description': 'Customer satisfaction metric. Percentage of promoters (9-10 rating) minus percentage of detractors (0-6 rating) from customer surveys.',
                'formula': "((COUNT(rating >= 9) - COUNT(rating <= 6)) / COUNT(total_responses)) * 100",
                'data_type': 'numeric',
                'category': 'Customer',
                'owner': 'Product Team',
            },
            {
                'name': 'average_deal_size',
                'display_name': 'Average Deal Size',
                'description': 'Mean value of closed-won deals in the sales pipeline. Calculated from annual contract value (ACV) of new and expansion deals.',
                'formula': "AVG(annual_contract_value) WHERE deal_status = 'closed_won'",
                'data_type': 'numeric',
                'category': 'Sales',
                'owner': 'Sales Leadership',
            },
            {
                'name': 'data_pipeline_uptime',
                'display_name': 'Data Pipeline Uptime',
                'description': 'Percentage of time that critical data pipelines (ETL, replication, streaming) are operational without failures or delays exceeding SLA thresholds.',
                'formula': "(total_minutes - downtime_minutes) / total_minutes * 100",
                'data_type': 'numeric',
                'category': 'Operations',
                'owner': 'Data Engineering',
            },
        ]
        metrics = {}
        for data in metric_data:
            metric, _ = GovernanceMetric.objects.get_or_create(
                name=data['name'],
                defaults=data,
            )
            metrics[metric.name] = metric
        return metrics

    def _create_semantic_definitions(self, metrics, sources):
        """Create semantic definitions showing real-world inconsistencies."""
        self.stdout.write('Creating semantic definitions (with intentional inconsistencies)...')

        definitions = [
            # === TOTAL REVENUE: Defined differently across 5 systems ===
            {
                'metric': 'total_revenue',
                'source': 'Snowflake DWH',
                'local_name': 'total_revenue',
                'local_formula': "SUM(amount) WHERE status = 'completed' AND type IN ('subscription', 'one_time', 'services')",
                'local_description': 'Matches canonical definition. Primary source of truth.',
                'is_consistent': True,
            },
            {
                'metric': 'total_revenue',
                'source': 'Tableau Cloud',
                'local_name': 'revenue_total',
                'local_formula': "SUM(amount) WHERE status IN ('completed', 'pending')",
                'local_description': 'INCLUDES PENDING TRANSACTIONS. Overstates revenue by ~12% compared to Snowflake. Finance team unaware of this discrepancy.',
                'is_consistent': False,
                'consistency_notes': 'Includes pending transactions, overstating revenue by ~12%',
            },
            {
                'metric': 'total_revenue',
                'source': 'PostgreSQL Production',
                'local_name': 'total_rev',
                'local_formula': "SUM(charge_amount) WHERE payment_status = 'succeeded'",
                'local_description': 'Uses charge_amount instead of amount (excludes tax). Uses payment_status field instead of status. Net revenue, not gross.',
                'is_consistent': False,
                'consistency_notes': 'Uses net amount (excludes tax), different field names',
            },
            {
                'metric': 'total_revenue',
                'source': 'Salesforce CRM',
                'local_name': 'Total_Revenue__c',
                'local_formula': "SUM(Opportunity.Amount) WHERE StageName = 'Closed Won'",
                'local_description': 'Based on opportunity amounts, not actual payments. Includes forecasted revenue that may not have been collected.',
                'is_consistent': False,
                'consistency_notes': 'Opportunity-based, not payment-based. Can include uncollected revenue.',
            },
            {
                'metric': 'total_revenue',
                'source': 'Stripe Payments',
                'local_name': 'gross_revenue',
                'local_formula': "SUM(charge.amount) WHERE charge.status = 'succeeded' AND charge.refunded = false",
                'local_description': 'Actual payment amounts collected. Most accurate but excludes non-Stripe revenue channels.',
                'is_consistent': True,
                'consistency_notes': 'Accurate for Stripe-processed payments only',
            },

            # === MRR: Defined differently across 3 systems ===
            {
                'metric': 'monthly_recurring_revenue',
                'source': 'Snowflake DWH',
                'local_name': 'mrr',
                'local_formula': "SUM(subscription_amount / billing_interval_months) WHERE subscription_status = 'active'",
                'local_description': 'Canonical MRR calculation from subscription data.',
                'is_consistent': True,
            },
            {
                'metric': 'monthly_recurring_revenue',
                'source': 'Stripe Payments',
                'local_name': 'mrr',
                'local_formula': "SUM(subscription.plan.amount * subscription.quantity) WHERE subscription.status = 'active'",
                'local_description': 'Uses plan amount * quantity. Does not normalize annual plans to monthly. Overstates for annual subscribers.',
                'is_consistent': False,
                'consistency_notes': 'Does not normalize annual plans to monthly amounts',
            },
            {
                'metric': 'monthly_recurring_revenue',
                'source': 'Salesforce CRM',
                'local_name': 'MRR__c',
                'local_formula': "SUM(Opportunity.Annual_Value__c / 12) WHERE Opportunity.StageName = 'Closed Won'",
                'local_description': 'Divides annual opportunity value by 12. Includes churned accounts until renewal date passes.',
                'is_consistent': False,
                'consistency_notes': 'Includes churned accounts until renewal date',
            },

            # === CUSTOMER COUNT: 4 different definitions ===
            {
                'metric': 'customer_count',
                'source': 'Snowflake DWH',
                'local_name': 'active_customers',
                'local_formula': "COUNT(DISTINCT customer_id) WHERE subscription_status = 'active' AND last_login >= DATEADD(day, -90, CURRENT_DATE)",
                'local_description': 'Canonical: active subscription + logged in within 90 days.',
                'is_consistent': True,
            },
            {
                'metric': 'customer_count',
                'source': 'Salesforce CRM',
                'local_name': 'Account_Count__c',
                'local_formula': "COUNT(Account.Id) WHERE Account.Type = 'Customer' AND Account.Status__c = 'Active'",
                'local_description': 'Counts accounts, not unique customers. One company with 3 subsidiaries = 3 customers in Salesforce.',
                'is_consistent': False,
                'consistency_notes': 'Counts accounts, not unique customers. Inflates count by ~15%',
            },
            {
                'metric': 'customer_count',
                'source': 'PostgreSQL Production',
                'local_name': 'user_count',
                'local_formula': "COUNT(DISTINCT user_id) WHERE is_active = true",
                'local_description': 'Counts active users, not customers. One customer can have 50 users. Vastly overstates customer count.',
                'is_consistent': False,
                'consistency_notes': 'Counts users, not customers. Overstates by 10-50x depending on plan size.',
            },
            {
                'metric': 'customer_count',
                'source': 'HubSpot Marketing',
                'local_name': 'customer_contacts',
                'local_formula': "COUNT(contacts) WHERE lifecycle_stage = 'customer'",
                'local_description': 'Counts contacts with customer lifecycle stage. Includes churned customers who were never removed from the stage.',
                'is_consistent': False,
                'consistency_notes': 'Includes churned contacts still marked as customers',
            },

            # === CHURN RATE: 3 different calculations ===
            {
                'metric': 'churn_rate',
                'source': 'Snowflake DWH',
                'local_name': 'monthly_churn_rate',
                'local_formula': "COUNT(churned_customers) / COUNT(total_customers_at_period_start) * 100",
                'local_description': 'Logo churn rate. Canonical calculation based on customer count at period start.',
                'is_consistent': True,
            },
            {
                'metric': 'churn_rate',
                'source': 'Stripe Payments',
                'local_name': 'subscription_churn',
                'local_formula': "COUNT(subscription.status = 'canceled') / COUNT(subscription.status WAS 'active' AT period_start) * 100",
                'local_description': 'Subscription-level churn, not customer-level. One customer cancelling 1 of 3 subscriptions counts as churn.',
                'is_consistent': False,
                'consistency_notes': 'Subscription-level churn, not customer-level',
            },
            {
                'metric': 'churn_rate',
                'source': 'Salesforce CRM',
                'local_name': 'Churn_Rate__c',
                'local_formula': "COUNT(Opportunity.StageName = 'Closed Lost') / COUNT(Opportunity.Renewal = true) * 100",
                'local_description': 'Based on renewal opportunities lost. Misses voluntary cancellations between renewal periods.',
                'is_consistent': False,
                'consistency_notes': 'Only counts lost renewals, misses mid-term cancellations',
            },

            # === CAC: 2 systems ===
            {
                'metric': 'customer_acquisition_cost',
                'source': 'Snowflake DWH',
                'local_name': 'cac',
                'local_formula': "SUM(sales_marketing_spend) / COUNT(new_customers)",
                'local_description': 'Blended CAC across all channels.',
                'is_consistent': True,
            },
            {
                'metric': 'customer_acquisition_cost',
                'source': 'HubSpot Marketing',
                'local_name': 'cost_per_acquisition',
                'local_formula': "SUM(campaign_spend) / COUNT(new_contacts WHERE lifecycle_stage = 'customer')",
                'local_description': 'Only includes marketing campaign spend, not sales salaries or tools. Understates true CAC by ~40%.',
                'is_consistent': False,
                'consistency_notes': 'Only marketing spend, excludes sales costs. Understates CAC by ~40%',
            },

            # === NPS: consistent across 2 systems ===
            {
                'metric': 'net_promoter_score',
                'source': 'Snowflake DWH',
                'local_name': 'nps_score',
                'local_formula': "((COUNT(rating >= 9) - COUNT(rating <= 6)) / COUNT(total_responses)) * 100",
                'local_description': 'Aggregated NPS from all survey responses.',
                'is_consistent': True,
            },
            {
                'metric': 'net_promoter_score',
                'source': 'PostgreSQL Production',
                'local_name': 'nps',
                'local_formula': "((COUNT(score >= 9) - COUNT(score <= 6)) / COUNT(*)) * 100",
                'local_description': 'In-app survey NPS. Same formula but only covers in-app surveys, not email surveys.',
                'is_consistent': True,
            },

            # === AVERAGE DEAL SIZE ===
            {
                'metric': 'average_deal_size',
                'source': 'Salesforce CRM',
                'local_name': 'Avg_Deal_ACV__c',
                'local_formula': "AVG(Opportunity.Amount) WHERE StageName = 'Closed Won'",
                'local_description': 'Average ACV from closed-won opportunities.',
                'is_consistent': True,
            },
            {
                'metric': 'average_deal_size',
                'source': 'Snowflake DWH',
                'local_name': 'avg_deal_size',
                'local_formula': "AVG(annual_contract_value) WHERE deal_status = 'closed_won'",
                'local_description': 'Average ACV from deals table.',
                'is_consistent': True,
            },

            # === DATA PIPELINE UPTIME ===
            {
                'metric': 'data_pipeline_uptime',
                'source': 'Snowflake DWH',
                'local_name': 'pipeline_uptime_pct',
                'local_formula': "(total_minutes - downtime_minutes) / total_minutes * 100",
                'local_description': 'Overall pipeline uptime percentage.',
                'is_consistent': True,
            },
            {
                'metric': 'data_pipeline_uptime',
                'source': 'Google BigQuery',
                'local_name': 'etl_success_rate',
                'local_formula': "COUNT(successful_runs) / COUNT(total_runs) * 100",
                'local_description': 'Measures job success rate, not uptime. A pipeline that runs once and fails = 0% even if system was up all day.',
                'is_consistent': False,
                'consistency_notes': 'Measures job success rate, not actual uptime',
            },
        ]

        for defn in definitions:
            metric = metrics.get(defn['metric'])
            source = sources.get(defn['source'])
            if not metric or not source:
                continue
            SemanticDefinition.objects.update_or_create(
                governance_metric=metric,
                source=source,
                defaults={
                    'local_name': defn['local_name'],
                    'local_formula': defn['local_formula'],
                    'local_description': defn['local_description'],
                    'is_consistent': defn.get('is_consistent', True),
                    'consistency_notes': defn.get('consistency_notes', ''),
                    'last_verified': timezone.now() - timedelta(hours=random.randint(1, 72)),
                    'definition_type': 'metric',
                },
            )

    def _create_lineage(self, sources, metrics):
        self.stdout.write('Creating data lineage flows...')
        flows = [
            {
                'from': 'PostgreSQL Production',
                'to': 'Snowflake DWH',
                'flow_type': 'etl',
                'description': 'Nightly ETL of transactional data (orders, payments, users) via Fivetran. ~2M rows/night.',
                'schedule': 'Daily at 02:00 UTC',
            },
            {
                'from': 'Stripe Payments',
                'to': 'Snowflake DWH',
                'flow_type': 'streaming',
                'description': 'Real-time webhook events for charges, subscriptions, and refunds via Kafka.',
                'schedule': 'Real-time (< 5 min latency)',
            },
            {
                'from': 'Salesforce CRM',
                'to': 'Snowflake DWH',
                'flow_type': 'etl',
                'description': 'Hourly sync of opportunity, account, and contact data via Fivetran.',
                'schedule': 'Hourly',
            },
            {
                'from': 'HubSpot Marketing',
                'to': 'Snowflake DWH',
                'flow_type': 'api_sync',
                'description': 'Daily sync of marketing campaigns, contacts, and attribution data.',
                'schedule': 'Daily at 06:00 UTC',
            },
            {
                'from': 'Snowflake DWH',
                'to': 'Tableau Cloud',
                'flow_type': 'etl',
                'description': 'Tableau live connections and extracts from Snowflake analytics schemas.',
                'schedule': 'Extracts refresh every 4 hours',
            },
            {
                'from': 'Snowflake DWH',
                'to': 'Google BigQuery',
                'flow_type': 'replication',
                'description': 'Cross-cloud replication for the data science team who prefers BigQuery ML.',
                'schedule': 'Daily at 04:00 UTC',
            },
            {
                'from': 'PostgreSQL Production',
                'to': 'Google BigQuery',
                'flow_type': 'streaming',
                'description': 'CDC (Change Data Capture) stream of product usage events via Debezium + Kafka.',
                'schedule': 'Real-time (< 2 min latency)',
            },
            {
                'from': 'CSV Uploads',
                'to': 'Snowflake DWH',
                'flow_type': 'manual',
                'description': 'Quarterly budget data and manual adjustments uploaded by the finance team.',
                'schedule': 'Quarterly / Ad-hoc',
            },
            {
                'from': 'Salesforce CRM',
                'to': 'HubSpot Marketing',
                'flow_type': 'api_sync',
                'description': 'Bi-directional lead and contact sync between sales and marketing.',
                'schedule': 'Every 15 minutes',
            },
        ]

        revenue_metrics = ['total_revenue', 'monthly_recurring_revenue']

        for flow_data in flows:
            source_from = sources.get(flow_data['from'])
            source_to = sources.get(flow_data['to'])
            if not source_from or not source_to:
                continue
            flow, created = DataLineage.objects.update_or_create(
                source_from=source_from,
                source_to=source_to,
                flow_type=flow_data['flow_type'],
                defaults={
                    'description': flow_data['description'],
                    'schedule': flow_data['schedule'],
                },
            )
            # Attach metrics to some flows
            if 'snowflake' in flow_data['to'].lower() or 'snowflake' in flow_data['from'].lower():
                for mname in revenue_metrics:
                    m = metrics.get(mname)
                    if m:
                        flow.metrics_transferred.add(m)

    def _create_validations(self, sources):
        self.stdout.write('Creating validation results...')
        now = timezone.now()

        validation_scenarios = {
            'Snowflake DWH': [
                (95.2, True, 12, 11, 1),
                (92.8, True, 12, 11, 1),
                (97.5, True, 12, 12, 0),
                (88.3, True, 10, 9, 1),
                (94.1, True, 12, 11, 1),
            ],
            'Tableau Cloud': [
                (78.4, True, 8, 6, 2),
                (72.1, True, 8, 6, 2),
                (65.3, False, 8, 5, 3),
                (80.9, True, 8, 7, 1),
                (74.6, True, 8, 6, 2),
            ],
            'PostgreSQL Production': [
                (91.7, True, 10, 9, 1),
                (89.3, True, 10, 9, 1),
                (93.2, True, 10, 9, 1),
                (87.5, True, 10, 9, 1),
                (95.0, True, 10, 10, 0),
            ],
            'Salesforce CRM': [
                (68.2, False, 8, 5, 3),
                (71.5, True, 8, 6, 2),
                (66.8, False, 8, 5, 3),
                (73.9, True, 8, 6, 2),
                (62.4, False, 8, 5, 3),
            ],
            'Stripe Payments': [
                (98.1, True, 6, 6, 0),
                (97.5, True, 6, 6, 0),
                (96.8, True, 6, 6, 0),
                (99.2, True, 6, 6, 0),
                (97.9, True, 6, 6, 0),
            ],
            'HubSpot Marketing': [
                (82.3, True, 8, 7, 1),
                (79.1, True, 8, 6, 2),
                (85.6, True, 8, 7, 1),
                (77.4, True, 8, 6, 2),
                (81.2, True, 8, 7, 1),
            ],
            'Google BigQuery': [
                (90.5, True, 10, 9, 1),
                (88.7, True, 10, 9, 1),
                (92.1, True, 10, 9, 1),
                (86.3, True, 10, 9, 1),
                (91.8, True, 10, 9, 1),
            ],
            'CSV Uploads': [
                (55.2, False, 6, 3, 3),
                (62.8, False, 6, 4, 2),
                (48.3, False, 6, 3, 3),
                (58.7, False, 6, 4, 2),
                (51.4, False, 6, 3, 3),
            ],
        }

        for source_name, scenarios in validation_scenarios.items():
            source = sources.get(source_name)
            if not source:
                continue
            for i, (score, passed, total, p, f) in enumerate(scenarios):
                details = {
                    'results': [
                        {'rule': 'null_check', 'passed': score > 70, 'detail': f'{100 - score:.1f}% null values detected'},
                        {'rule': 'type_check', 'passed': True, 'detail': 'All columns have correct types'},
                        {'rule': 'range_check', 'passed': score > 60, 'detail': 'Numeric values within expected range'},
                    ]
                }
                ValidationResult.objects.create(
                    source=source,
                    passed=passed,
                    quality_score=score,
                    total_rules=total,
                    passed_rules=p,
                    failed_rules=f,
                    details=details,
                    timestamp=now - timedelta(days=i * 2, hours=random.randint(0, 12)),
                )

    def _create_trust_scores(self, sources):
        self.stdout.write('Creating trust scores...')
        now = timezone.now()

        trust_profiles = {
            'Snowflake DWH': {
                'overall': 92.4, 'level': 'verified',
                'completeness': 96.0, 'accuracy': 94.5, 'consistency': 91.2,
                'timeliness': 88.5, 'validity': 93.8, 'uniqueness': 90.1,
                'issues': ['Minor: 3.8% null values in customer_segment column', 'Advisory: timeliness SLA missed twice this month'],
            },
            'Tableau Cloud': {
                'overall': 74.8, 'level': 'medium',
                'completeness': 82.0, 'accuracy': 68.5, 'consistency': 62.3,
                'timeliness': 78.9, 'validity': 85.1, 'uniqueness': 72.0,
                'issues': [
                    'CRITICAL: Revenue metric includes pending transactions (12% overstatement)',
                    'HIGH: Customer count uses stale extract (4-hour delay)',
                    'MEDIUM: 3 calculated fields diverge from Snowflake definitions',
                ],
            },
            'PostgreSQL Production': {
                'overall': 88.6, 'level': 'high',
                'completeness': 91.5, 'accuracy': 92.0, 'consistency': 85.3,
                'timeliness': 95.2, 'validity': 88.7, 'uniqueness': 79.0,
                'issues': ['MEDIUM: Uses charge_amount (net) instead of amount (gross)', 'LOW: 21% duplicate entries in event log table'],
            },
            'Salesforce CRM': {
                'overall': 65.3, 'level': 'medium',
                'completeness': 72.0, 'accuracy': 58.5, 'consistency': 55.8,
                'timeliness': 68.2, 'validity': 75.3, 'uniqueness': 62.0,
                'issues': [
                    'CRITICAL: Revenue based on opportunity amounts, not actual payments',
                    'HIGH: Customer count inflated by subsidiary accounts',
                    'HIGH: Churn calculation misses mid-term cancellations',
                    'MEDIUM: 28% of accounts have stale contact information',
                ],
            },
            'Stripe Payments': {
                'overall': 96.8, 'level': 'verified',
                'completeness': 99.0, 'accuracy': 98.5, 'consistency': 95.2,
                'timeliness': 97.8, 'validity': 96.3, 'uniqueness': 94.0,
                'issues': ['Advisory: Only covers Stripe-processed payments, not wire transfers'],
            },
            'HubSpot Marketing': {
                'overall': 78.2, 'level': 'high',
                'completeness': 85.0, 'accuracy': 76.5, 'consistency': 72.1,
                'timeliness': 80.3, 'validity': 82.5, 'uniqueness': 73.0,
                'issues': [
                    'HIGH: CAC calculation excludes sales team costs (~40% understatement)',
                    'MEDIUM: Customer count includes churned contacts',
                    'LOW: Campaign attribution window differs from Snowflake (30 vs 90 days)',
                ],
            },
            'Google BigQuery': {
                'overall': 85.1, 'level': 'high',
                'completeness': 88.0, 'accuracy': 87.5, 'consistency': 82.3,
                'timeliness': 90.5, 'validity': 83.2, 'uniqueness': 79.0,
                'issues': [
                    'MEDIUM: Pipeline uptime metric measures job success rate, not actual uptime',
                    'LOW: 6-hour replication lag from Snowflake',
                ],
            },
            'CSV Uploads': {
                'overall': 45.2, 'level': 'low',
                'completeness': 52.0, 'accuracy': 38.5, 'consistency': 35.8,
                'timeliness': 28.2, 'validity': 62.3, 'uniqueness': 54.0,
                'issues': [
                    'CRITICAL: Manual data entry with no validation rules',
                    'CRITICAL: Data freshness varies (some files are months old)',
                    'HIGH: Inconsistent column naming across uploads',
                    'HIGH: 45% of uploads contain duplicate rows',
                    'MEDIUM: No referential integrity checks',
                ],
            },
        }

        for source_name, profile in trust_profiles.items():
            source = sources.get(source_name)
            if not source:
                continue
            # Create current and historical scores
            for i in range(3):
                jitter = random.uniform(-3, 3) if i > 0 else 0
                TrustScore.objects.create(
                    source=source,
                    overall_score=min(100, max(0, profile['overall'] + jitter)),
                    trust_level=profile['level'],
                    completeness_score=min(100, max(0, profile['completeness'] + jitter)),
                    accuracy_score=min(100, max(0, profile['accuracy'] + jitter)),
                    consistency_score=min(100, max(0, profile['consistency'] + jitter)),
                    timeliness_score=min(100, max(0, profile['timeliness'] + jitter)),
                    validity_score=min(100, max(0, profile['validity'] + jitter)),
                    uniqueness_score=min(100, max(0, profile['uniqueness'] + jitter)),
                    issues=profile['issues'],
                    metadata={
                        'source_type': source.source_type,
                        'rows_analyzed': random.randint(10000, 5000000),
                        'columns_analyzed': random.randint(15, 120),
                    },
                )

    def _run_reconciliation(self, metrics):
        self.stdout.write('Running reconciliation engine...')
        engine = ReconciliationEngine()
        all_metrics = GovernanceMetric.objects.filter(is_active=True)
        all_defs = SemanticDefinition.objects.select_related('governance_metric', 'source')
        results = engine.reconcile_all(all_metrics, all_defs)

        for result in results:
            metric = GovernanceMetric.objects.get(name=result.metric_name)
            run = ReconciliationRun.objects.create(
                governance_metric=metric,
                status=result.status,
                total_sources=result.total_sources,
                consistent_sources=result.consistent_sources,
                divergent_sources=result.divergent_sources,
                consistency_score=result.consistency_score,
                divergences=[d.to_dict() for d in result.divergences],
                recommendations=result.recommendations,
            )
            source_names = set()
            for d in result.divergences:
                source_names.add(d.source_a)
                source_names.add(d.source_b)
            run.sources_compared.set(DataSource.objects.filter(name__in=source_names))

            # Update consistency flags
            for defn in SemanticDefinition.objects.filter(governance_metric=metric):
                is_consistent = defn.source.name not in {
                    d.source_b for d in result.divergences
                }
                defn.is_consistent = is_consistent
                defn.last_verified = timezone.now()
                defn.save(update_fields=['is_consistent', 'last_verified'])
