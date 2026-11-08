"""
Workload Intelligence Agent - Manages query queuing, prioritization, and resource allocation.
Prevents resource contention and enforces workload quotas.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class QueryQueue:
    """Represents a warehouse query queue state."""

    def __init__(self, warehouse_name: str):
        self.warehouse_name = warehouse_name
        self.queued_queries = []
        self.running_queries = []
        self.queue_depth = 0
        self.max_concurrency = 0
        self.avg_wait_time = 0


class WorkloadQuota:
    """Resource quota for user/role/department."""

    def __init__(
        self,
        entity_type: str,  # 'user', 'role', 'department'
        entity_name: str,
        warehouse_name: str = None
    ):
        self.entity_type = entity_type
        self.entity_name = entity_name
        self.warehouse_name = warehouse_name

        # Limits
        self.max_queries_per_hour = 1000
        self.max_gb_scanned_per_day = 10000
        self.max_credits_per_month = 50000
        self.priority_level = "medium"  # critical, high, medium, low

        # Current usage
        self.queries_this_hour = 0
        self.gb_scanned_today = 0
        self.credits_this_month = 0


class WorkloadIntelligenceAgent(GovernanceAgent):
    """
    Workload Intelligence Agent - Manages workload distribution and resource quotas.

    Responsibilities:
    - Monitor query queue depth
    - Detect resource contention
    - Enforce resource quotas
    - Recommend query prioritization
    - Optimize concurrency
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize Workload Intelligence Agent."""
        super().__init__(
            agent_name="WorkloadIntelligenceAgent",
            agent_type=AgentType.PERFORMANCE,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # Configuration
        self.queue_warning_threshold = 5
        self.queue_critical_threshold = 15
        self.contention_threshold = 0.7  # 70% resource utilization
        self.quota_warning_threshold = 0.8  # 80% of quota used

        # Workload tracking
        self.warehouse_queues: Dict[str, QueryQueue] = {}
        self.user_quotas: Dict[str, WorkloadQuota] = {}
        self.priority_rules = []

    def execute(self) -> bool:
        """Execute workload intelligence checks."""
        try:
            self.start_execution()

            logger.info("Starting Workload Intelligence Agent execution")

            # Analyze query queues
            self.analyze_query_queues()

            # Check resource quotas
            self.check_resource_quotas()

            # Detect resource contention
            self.detect_resource_contention()

            # Recommend query prioritization
            self.generate_workload_recommendations()

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Workload agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # QUEUE ANALYSIS
    # ========================================================================

    def analyze_query_queues(self) -> None:
        """Analyze query queue on all warehouses."""
        logger.info("Analyzing query queues...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')
                metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)

                queued = metrics.get('queued', 0)
                running = metrics.get('running', 0)

                # Create queue tracking object
                queue = QueryQueue(warehouse_name)
                queue.queue_depth = queued
                queue.running_queries = list(range(running))
                self.warehouse_queues[warehouse_name] = queue

                # Check for queue issues
                if queued >= self.queue_critical_threshold:
                    finding = Finding(
                        finding_id=None,
                        title=f"Critical queue buildup: {warehouse_name}",
                        description=f"{warehouse_name} has {queued} queued queries",
                        severity=DetectionSeverity.CRITICAL,
                        category="critical_queue",
                        resource_type="warehouse",
                        resource_name=warehouse_name,
                        details={
                            "queue_depth": queued,
                            "running": running,
                            "concurrency_ratio": running / max(running + queued, 1)
                        }
                    )
                    finding.recommendation = f"Immediate action: scale {warehouse_name} or kill long-running queries"
                    self.add_finding(finding)

                elif queued >= self.queue_warning_threshold:
                    finding = Finding(
                        finding_id=None,
                        title=f"Queue buildup warning: {warehouse_name}",
                        description=f"{warehouse_name} has {queued} queued queries",
                        severity=DetectionSeverity.HIGH,
                        category="queue_warning",
                        resource_type="warehouse",
                        resource_name=warehouse_name,
                        details={
                            "queue_depth": queued,
                            "running": running
                        }
                    )
                    finding.recommendation = f"Monitor queue on {warehouse_name}, consider scaling"
                    self.add_finding(finding)

                logger.debug(f"{warehouse_name}: running={running}, queued={queued}")

        except Exception as e:
            logger.error(f"Queue analysis failed: {str(e)}")

    # ========================================================================
    # QUOTA MANAGEMENT
    # ========================================================================

    def check_resource_quotas(self) -> None:
        """Check resource quotas for users and departments."""
        logger.info("Checking resource quotas...")

        try:
            # Get users and their current usage
            users = self.snowpark_client.list_users()

            for user in users:
                user_name = user.get('user_name')

                # Get query history for user
                sql = f"""
                SELECT
                    COUNT(*) as query_count,
                    SUM(TIMESTAMPDIFF(second, start_time, end_time)) as total_time,
                    SUM(bytes_scanned) as total_scanned
                FROM snowflake.account_usage.query_history
                WHERE user_name = '{user_name}'
                    AND start_time >= CURRENT_TIMESTAMP() - INTERVAL '1 hours'
                """

                try:
                    results = self.snowpark_client.execute_query(sql)
                    if results:
                        usage = results[0]
                        query_count = usage.get('query_count', 0)

                        # Check query rate quota
                        if query_count > 100:  # More than 100 queries per hour
                            finding = Finding(
                                finding_id=None,
                                title=f"High query rate: {user_name}",
                                description=f"User {user_name} executed {query_count} queries in last hour",
                                severity=DetectionSeverity.MEDIUM,
                                category="high_query_rate",
                                resource_type="user",
                                resource_name=user_name,
                                details={
                                    "queries_per_hour": query_count,
                                    "total_time_seconds": usage.get('total_time', 0)
                                }
                            )
                            finding.recommendation = f"Review query patterns for {user_name}"
                            self.add_finding(finding)

                except Exception as e:
                    logger.debug(f"Could not analyze quota for {user_name}: {str(e)}")

        except Exception as e:
            logger.error(f"Quota check failed: {str(e)}")

    # ========================================================================
    # CONTENTION DETECTION
    # ========================================================================

    def detect_resource_contention(self) -> None:
        """Detect resource contention between concurrent queries."""
        logger.info("Detecting resource contention...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')
                metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)

                running = metrics.get('running', 0)
                queued = metrics.get('queued', 0)

                # Calculate contention indicator
                if running > 0:
                    contention_ratio = queued / (running + queued)

                    if contention_ratio > self.contention_threshold:
                        finding = Finding(
                            finding_id=None,
                            title=f"High resource contention: {warehouse_name}",
                            description=f"Warehouse has {running} running queries + {queued} queued (contention: {contention_ratio*100:.0f}%)",
                            severity=DetectionSeverity.HIGH,
                            category="resource_contention",
                            resource_type="warehouse",
                            resource_name=warehouse_name,
                            details={
                                "running": running,
                                "queued": queued,
                                "contention_ratio": contention_ratio
                            }
                        )
                        finding.recommendation = f"Separate workloads: create dedicated warehouses for different query types"
                        self.add_finding(finding)

        except Exception as e:
            logger.error(f"Contention detection failed: {str(e)}")

    # ========================================================================
    # RECOMMENDATION GENERATION
    # ========================================================================

    def generate_workload_recommendations(self) -> None:
        """Generate workload optimization recommendations."""
        logger.info(f"Generating recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "critical_queue":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Emergency: Resolve queue on {finding.resource_name}",
                    description="Critical queue buildup requires immediate action",
                    action_type="scale_warehouse",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="critical"
                )
                rec.add_step(f"IMMEDIATELY scale {finding.resource_name} to larger size")
                rec.add_step("OR abort oldest queued queries")
                rec.add_step("OR identify and kill long-running queries")
                rec.add_step("Monitor until queue clears")
                self.add_recommendation(rec)

            elif finding.category == "queue_warning":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Resolve queue buildup: {finding.resource_name}",
                    description="Queue buildup detected, action recommended",
                    action_type="scale_warehouse",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="high"
                )
                rec.add_step(f"Analyze workload on {finding.resource_name}")
                rec.add_step("Check for long-running queries")
                rec.add_step("Consider scaling warehouse")
                rec.add_step("Or create separate warehouse for different workload")
                self.add_recommendation(rec)

            elif finding.category == "resource_contention":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Separate workloads: {finding.resource_name}",
                    description="Resource contention between queries",
                    action_type="optimize_workload",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step("Create separate warehouses for:")
                rec.add_step("  1. Short-running queries (BI, dashboards)")
                rec.add_step("  2. Medium queries (ETL jobs)")
                rec.add_step("  3. Long-running queries (analytics)")
                rec.add_step("Route queries to appropriate warehouse based on type")
                self.add_recommendation(rec)

            elif finding.category == "high_query_rate":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Investigate query rate: {finding.resource_name}",
                    description="Unusually high query submission rate",
                    action_type="investigate",
                    resource_type="user",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step(f"Review query patterns for {finding.resource_name}")
                rec.add_step("Identify if queries can be batched")
                rec.add_step("Check if loops or retries are excessive")
                rec.add_step("Consider query result caching")
                self.add_recommendation(rec)

    # ========================================================================
    # QUERY PRIORITIZATION
    # ========================================================================

    def create_priority_rules(self) -> None:
        """Create query prioritization rules."""
        logger.info("Setting up query prioritization rules")

        self.priority_rules = [
            {
                "name": "SLA_critical",
                "priority": "critical",
                "max_runtime": 300,  # 5 minutes
                "warehouse": "SLA_WH",
                "queries": ["system_health", "compliance", "audit"]
            },
            {
                "name": "operational",
                "priority": "high",
                "max_runtime": 600,
                "warehouse": "OPERATIONAL_WH",
                "queries": ["prod_reports", "dashboards", "operational_metrics"]
            },
            {
                "name": "analytics",
                "priority": "medium",
                "max_runtime": 3600,
                "warehouse": "ANALYTICS_WH",
                "queries": ["ad_hoc", "data_science", "analytics"]
            },
            {
                "name": "batch",
                "priority": "low",
                "max_runtime": 86400,  # 24 hours
                "warehouse": "BATCH_WH",
                "queries": ["etl", "imports", "bulk_operations"]
            }
        ]

        logger.info(f"Created {len(self.priority_rules)} priority rules")

    def get_recommended_warehouse(self, query_text: str, user: str = None) -> str:
        """Recommend warehouse for a query based on priority rules."""
        query_lower = query_text.lower()

        for rule in self.priority_rules:
            for keyword in rule.get("queries", []):
                if keyword.lower() in query_lower:
                    return rule.get("warehouse")

        # Default to COMPUTE warehouse
        return "COMPUTE_WH"

    def get_summary(self) -> Dict[str, Any]:
        """Get workload summary."""
        total_queued = sum(q.queue_depth for q in self.warehouse_queues.values())
        total_running = sum(len(q.running_queries) for q in self.warehouse_queues.values())

        return {
            "warehouses_monitored": len(self.warehouse_queues),
            "total_running_queries": total_running,
            "total_queued_queries": total_queued,
            "priority_rules": len(self.priority_rules),
            "high_contention_warehouses": len([
                w for w in self.warehouse_queues.values()
                if w.queue_depth > self.queue_warning_threshold
            ])
        }
