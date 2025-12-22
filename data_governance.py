"""
Data Governance Framework

Provides centralized data governance, metric definitions, and metadata
management to ensure consistency across enterprise systems.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json


@dataclass
class MetricDefinition:
    """
    Standardized metric definition
    
    Ensures all systems use the same calculation logic
    """
    name: str
    description: str
    calculation: str
    data_type: str
    business_owner: str
    technical_owner: str
    source_systems: List[str]
    update_frequency: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "calculation": self.calculation,
            "data_type": self.data_type,
            "business_owner": self.business_owner,
            "technical_owner": self.technical_owner,
            "source_systems": self.source_systems,
            "update_frequency": self.update_frequency,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }


@dataclass
class DataAsset:
    """
    Represents a data asset (table, view, dataset)
    """
    name: str
    asset_type: str  # table, view, dataset, report
    description: str
    source_system: str
    schema: Dict[str, str]  # column_name -> data_type
    owner: str
    classification: str  # public, internal, confidential, restricted
    retention_period: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "asset_type": self.asset_type,
            "description": self.description,
            "source_system": self.source_system,
            "schema": self.schema,
            "owner": self.owner,
            "classification": self.classification,
            "retention_period": self.retention_period,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class DataDictionary:
    """
    Centralized data dictionary for all enterprise data
    
    Provides single source of truth for metric definitions
    """
    
    def __init__(self):
        self.metrics: Dict[str, MetricDefinition] = {}
        self.assets: Dict[str, DataAsset] = {}
    
    def register_metric(self, metric: MetricDefinition) -> None:
        """
        Register a new metric definition
        
        Args:
            metric: MetricDefinition object
        """
        self.metrics[metric.name] = metric
    
    def get_metric(self, name: str) -> Optional[MetricDefinition]:
        """
        Get metric definition by name
        
        Args:
            name: Metric name
        
        Returns:
            MetricDefinition or None
        """
        return self.metrics.get(name)
    
    def register_asset(self, asset: DataAsset) -> None:
        """
        Register a data asset
        
        Args:
            asset: DataAsset object
        """
        self.assets[asset.name] = asset
    
    def get_asset(self, name: str) -> Optional[DataAsset]:
        """
        Get data asset by name
        
        Args:
            name: Asset name
        
        Returns:
            DataAsset or None
        """
        return self.assets.get(name)
    
    def search_metrics(self, query: str) -> List[MetricDefinition]:
        """
        Search metrics by name or description
        
        Args:
            query: Search query
        
        Returns:
            List of matching metrics
        """
        query_lower = query.lower()
        results = []
        
        for metric in self.metrics.values():
            if (query_lower in metric.name.lower() or
                query_lower in metric.description.lower() or
                any(query_lower in tag.lower() for tag in metric.tags)):
                results.append(metric)
        
        return results
    
    def export_dictionary(self) -> Dict[str, Any]:
        """
        Export complete data dictionary
        
        Returns:
            Dictionary with all metrics and assets
        """
        return {
            "metrics": {
                name: metric.to_dict()
                for name, metric in self.metrics.items()
            },
            "assets": {
                name: asset.to_dict()
                for name, asset in self.assets.items()
            },
            "exported_at": datetime.utcnow().isoformat()
        }
    
    def import_dictionary(self, data: Dict[str, Any]) -> None:
        """
        Import data dictionary from JSON
        
        Args:
            data: Dictionary data
        """
        if "metrics" in data:
            for name, metric_data in data["metrics"].items():
                metric = MetricDefinition(
                    name=metric_data["name"],
                    description=metric_data["description"],
                    calculation=metric_data["calculation"],
                    data_type=metric_data["data_type"],
                    business_owner=metric_data["business_owner"],
                    technical_owner=metric_data["technical_owner"],
                    source_systems=metric_data["source_systems"],
                    update_frequency=metric_data["update_frequency"],
                    tags=metric_data.get("tags", [])
                )
                self.register_metric(metric)


class DataLineageTracker:
    """
    Track data lineage across systems
    
    Helps understand data flow and transformations
    """
    
    def __init__(self):
        self.lineage_graph: Dict[str, List[str]] = {}
        self.transformations: Dict[str, Dict[str, Any]] = {}
    
    def add_lineage(
        self,
        source: str,
        target: str,
        transformation: Optional[str] = None
    ) -> None:
        """
        Add lineage relationship
        
        Args:
            source: Source data asset
            target: Target data asset
            transformation: Optional transformation description
        """
        if source not in self.lineage_graph:
            self.lineage_graph[source] = []
        
        self.lineage_graph[source].append(target)
        
        if transformation:
            key = f"{source}->{target}"
            self.transformations[key] = {
                "source": source,
                "target": target,
                "transformation": transformation,
                "recorded_at": datetime.utcnow().isoformat()
            }
    
    def get_downstream(self, source: str) -> List[str]:
        """
        Get all downstream dependencies
        
        Args:
            source: Source asset name
        
        Returns:
            List of downstream assets
        """
        return self.lineage_graph.get(source, [])
    
    def get_upstream(self, target: str) -> List[str]:
        """
        Get all upstream dependencies
        
        Args:
            target: Target asset name
        
        Returns:
            List of upstream assets
        """
        upstream = []
        for source, targets in self.lineage_graph.items():
            if target in targets:
                upstream.append(source)
        return upstream
    
    def get_full_lineage(self, asset: str) -> Dict[str, Any]:
        """
        Get complete lineage for an asset
        
        Args:
            asset: Asset name
        
        Returns:
            Dictionary with upstream and downstream lineage
        """
        return {
            "asset": asset,
            "upstream": self.get_upstream(asset),
            "downstream": self.get_downstream(asset),
            "generated_at": datetime.utcnow().isoformat()
        }


class DataGovernancePolicy:
    """
    Define and enforce data governance policies
    """
    
    def __init__(self):
        self.policies: Dict[str, Dict[str, Any]] = {}
    
    def add_policy(
        self,
        name: str,
        description: str,
        rules: List[str],
        enforcement_level: str = "warning"
    ) -> None:
        """
        Add a governance policy
        
        Args:
            name: Policy name
            description: Policy description
            rules: List of policy rules
            enforcement_level: "warning", "error", or "blocking"
        """
        self.policies[name] = {
            "name": name,
            "description": description,
            "rules": rules,
            "enforcement_level": enforcement_level,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def get_policy(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get policy by name
        
        Args:
            name: Policy name
        
        Returns:
            Policy dictionary or None
        """
        return self.policies.get(name)
    
    def list_policies(self) -> List[Dict[str, Any]]:
        """
        List all policies
        
        Returns:
            List of all policies
        """
        return list(self.policies.values())


class GovernanceFramework:
    """
    Main governance framework orchestrator
    
    Integrates all governance components
    """
    
    def __init__(self):
        self.data_dictionary = DataDictionary()
        self.lineage_tracker = DataLineageTracker()
        self.policy_engine = DataGovernancePolicy()
        self._initialize_default_policies()
    
    def _initialize_default_policies(self) -> None:
        """Initialize default governance policies"""
        
        # Data Quality Policy
        self.policy_engine.add_policy(
            name="data_quality_standards",
            description="Minimum data quality standards for all datasets",
            rules=[
                "All datasets must have >95% completeness",
                "Critical fields cannot be null",
                "Duplicates must be <1% of total records",
                "Cross-system consistency must be >98%"
            ],
            enforcement_level="error"
        )
        
        # Data Security Policy
        self.policy_engine.add_policy(
            name="data_security",
            description="Data security and access control",
            rules=[
                "All PII must be encrypted at rest",
                "Access requires role-based authentication",
                "Audit logs must be maintained for 2 years",
                "Data must be classified (public/internal/confidential/restricted)"
            ],
            enforcement_level="blocking"
        )
        
        # Data Consistency Policy
        self.policy_engine.add_policy(
            name="cross_system_consistency",
            description="Ensure consistency across all enterprise systems",
            rules=[
                "Metric definitions must be centralized in data dictionary",
                "All systems must use same calculation logic",
                "Data synchronization must occur within SLA",
                "Conflicts must be resolved using defined precedence"
            ],
            enforcement_level="error"
        )
    
    def register_standard_metrics(self) -> None:
        """
        Register common enterprise metrics
        
        This ensures consistency across systems like Snowflake and Tableau
        """
        
        # Revenue Metric
        revenue_metric = MetricDefinition(
            name="revenue",
            description="Total revenue from all sources",
            calculation="SUM(transaction_amount) WHERE transaction_type = 'sale'",
            data_type="numeric",
            business_owner="Finance Team",
            technical_owner="Data Engineering",
            source_systems=["Snowflake", "Tableau", "Salesforce"],
            update_frequency="daily",
            tags=["finance", "kpi", "critical"]
        )
        self.data_dictionary.register_metric(revenue_metric)
        
        # Customer Count Metric
        customer_metric = MetricDefinition(
            name="active_customers",
            description="Number of customers with activity in last 30 days",
            calculation="COUNT(DISTINCT customer_id) WHERE last_activity_date >= CURRENT_DATE - 30",
            data_type="integer",
            business_owner="Customer Success",
            technical_owner="Analytics Team",
            source_systems=["Snowflake", "Tableau", "CRM"],
            update_frequency="daily",
            tags=["customer", "kpi", "growth"]
        )
        self.data_dictionary.register_metric(customer_metric)
        
        # Conversion Rate Metric
        conversion_metric = MetricDefinition(
            name="conversion_rate",
            description="Percentage of visitors who complete a purchase",
            calculation="(COUNT(purchases) / COUNT(visits)) * 100",
            data_type="numeric",
            business_owner="Marketing Team",
            technical_owner="Analytics Team",
            source_systems=["Snowflake", "Google Analytics", "Tableau"],
            update_frequency="hourly",
            tags=["marketing", "conversion", "kpi"]
        )
        self.data_dictionary.register_metric(conversion_metric)
    
    def export_governance_config(self, filepath: str) -> None:
        """
        Export complete governance configuration
        
        Args:
            filepath: Path to save JSON file
        """
        config = {
            "data_dictionary": self.data_dictionary.export_dictionary(),
            "policies": self.policy_engine.list_policies(),
            "exported_at": datetime.utcnow().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
    
    def generate_governance_report(self) -> str:
        """
        Generate governance status report
        
        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 70,
            "DATA GOVERNANCE REPORT",
            "=" * 70,
            f"\nTimestamp: {datetime.utcnow().isoformat()}",
            f"\n--- Metrics Registry ---",
            f"Total Metrics: {len(self.data_dictionary.metrics)}",
            f"Total Assets: {len(self.data_dictionary.assets)}",
            f"\n--- Policies ---",
            f"Total Policies: {len(self.policy_engine.list_policies())}",
        ]
        
        for policy in self.policy_engine.list_policies():
            report_lines.append(
                f"\n  • {policy['name']} ({policy['enforcement_level']})"
            )
            report_lines.append(f"    {policy['description']}")
        
        report_lines.append("\n" + "=" * 70)
        
        return "\n".join(report_lines)
