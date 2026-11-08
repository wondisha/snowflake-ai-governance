"""
Performance Optimization Agent - Detects slow queries and performance issues.
Provides optimization recommendations for queries, warehouses, and resources.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class PerformanceOptimizationAgent(GovernanceAgent):
    """
    Performance Optimization Agent - Monitors and optimizes query and warehouse performance.

    Responsibilities:
    - Detect slow queries
    - Identify resource contention
    - Recommend clustering keys
    - Suggest query optimizations
    - Monitor warehouse performance
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize Performance Optimization Agent."""
        super().__init__(
            agent_name="PerformanceOptimizationAgent",
            agent_type=AgentType.PERFORMANCE,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # Agent configuration
        self.slow_query_threshold_seconds = 30
        self.query_history_hours = 24
        self.spill_threshold_gb = 1.0
        self.resource_contention_threshold = 0.8

    def execute(self) -> bool:
        """Execute performance checks."""
        try:
            self.start_execution()

            logger.info("Starting Performance Optimization Agent execution")

            # Run detection methods
            self.detect_slow_queries()
            self.detect_resource_contention()
            self.detect_spill_issues()
            self.detect_warehouse_queue_buildup()

            # Generate recommendations
            self.generate_recommendations()

            # Process critical findings
            critical_findings = self.get_critical_findings()
            if critical_findings:
                logger.warning(f"Found {len(critical_findings)} critical performance issues")
                self._escalate_critical_findings(critical_findings)

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Performance agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DETECTION METHODS
    # ========================================================================

    def detect_slow_queries(self) -> None:
        """Detect queries exceeding performance threshold."""
        logger.info(f"Detecting slow queries (threshold: {self.slow_query_threshold_seconds}s)...")

        try:
            slow_queries = self.snowpark_client.get_slow_queries(
                threshold_seconds=self.slow_query_threshold_seconds,
                hours=self.query_history_hours
            )

            logger.info(f"Found {len(slow_queries)} slow queries")

            for query in slow_queries:
                query_id = query.get('query_id')
                execution_seconds = query.get('execution_seconds', 0)
                user_name = query.get('user_name')
                warehouse_name = query.get('warehouse_name')
                rows_produced = query.get('rows_produced', 0)
                bytes_scanned = query.get('bytes_scanned', 0)

                severity = self._determine_query_severity(execution_seconds, bytes_scanned)

                finding = Finding(
                    finding_id=None,
                    title=f"Slow query detected: {query_id[:8]}...",
                    description=f"Query executed in {execution_seconds}s (threshold: {self.slow_query_threshold_seconds}s)",
                    severity=severity,
                    category="slow_query",
                    resource_type="query",
                    resource_name=query_id,
                    details={
                        "execution_seconds": execution_seconds,
                        "user": user_name,
                        "warehouse": warehouse_name,
                        "rows_produced": rows_produced,
                        "bytes_scanned": bytes_scanned,
                        "spilled_local": query.get('bytes_spilled_to_local_storage', 0),
                        "spilled_remote": query.get('bytes_spilled_to_remote_storage', 0)
                    }
                )
                finding.recommendation = self._generate_query_optimization_tips(query)
                self.add_finding(finding)

        except Exception as e:
            logger.error(f"Slow query detection failed: {str(e)}")

    def detect_resource_contention(self) -> None:
        """Detect warehouse resource contention issues."""
        logger.info("Detecting resource contention...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')

                # Get warehouse metrics
                metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)
                running_queries = metrics.get('running', 0)
                queued_queries = metrics.get('queued', 0)
                state = metrics.get('state')

                # Check for contention
                if queued_queries > 5:
                    finding = Finding(
                        finding_id=None,
                        title=f"High query queue on {warehouse_name}",
                        description=f"Warehouse {warehouse_name} has {queued_queries} queued queries",
                        severity=DetectionSeverity.HIGH,
                        category="resource_contention",
                        resource_type="warehouse",
                        resource_name=warehouse_name,
                        details={
                            "queued_queries": queued_queries,
                            "running_queries": running_queries,
                            "warehouse_state": state
                        }
                    )
                    finding.recommendation = f"Consider scaling up {warehouse_name} or routing queries to different warehouse"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Resource contention detection failed: {str(e)}")

    def detect_spill_issues(self) -> None:
        """Detect queries spilling to disk."""
        logger.info(f"Detecting spill issues (threshold: {self.spill_threshold_gb}GB)...")

        try:
            slow_queries = self.snowpark_client.get_slow_queries(
                threshold_seconds=0,  # Get all queries
                hours=self.query_history_hours
            )

            for query in slow_queries:
                query_id = query.get('query_id')
                spilled_local = query.get('bytes_spilled_to_local_storage', 0) or 0
                spilled_remote = query.get('bytes_spilled_to_remote_storage', 0) or 0
                total_spilled_gb = (spilled_local + spilled_remote) / (1024 ** 3)

                if total_spilled_gb > self.spill_threshold_gb:
                    finding = Finding(
                        finding_id=None,
                        title=f"Query spilling to disk: {query_id[:8]}...",
                        description=f"Query spilled {total_spilled_gb:.2f}GB to disk",
                        severity=DetectionSeverity.HIGH,
                        category="spill_to_disk",
                        resource_type="query",
                        resource_name=query_id,
                        details={
                            "spilled_local_gb": spilled_local / (1024 ** 3),
                            "spilled_remote_gb": spilled_remote / (1024 ** 3),
                            "total_spilled_gb": total_spilled_gb
                        }
                    )
                    finding.recommendation = "Optimize query: Add WHERE clauses, use aggregation, or increase warehouse size"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Spill detection failed: {str(e)}")

    def detect_warehouse_queue_buildup(self) -> None:
        """Detect warehouse queue buildup patterns."""
        logger.info("Detecting warehouse queue buildup...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')
                warehouse_size = warehouse.get('warehouse_size')
                state = warehouse.get('state')

                metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)
                queued = metrics.get('queued', 0)

                # If suspended warehouse has queued queries, that's a problem
                if state == 'SUSPENDED' and queued > 0:
                    finding = Finding(
                        finding_id=None,
                        title=f"Suspended warehouse has queued queries: {warehouse_name}",
                        description=f"Warehouse {warehouse_name} is suspended but has {queued} queued queries",
                        severity=DetectionSeverity.MEDIUM,
                        category="warehouse_queue",
                        resource_type="warehouse",
                        resource_name=warehouse_name,
                        details={
                            "state": state,
                            "queued_queries": queued,
                            "size": warehouse_size
                        }
                    )
                    finding.recommendation = f"Resume warehouse {warehouse_name} or route queries elsewhere"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Warehouse queue detection failed: {str(e)}")

    # ========================================================================
    # ANALYSIS & RECOMMENDATIONS
    # ========================================================================

    def _determine_query_severity(self, execution_seconds: float, bytes_scanned: int) -> DetectionSeverity:
        """Determine severity based on execution time and data volume."""
        if execution_seconds > 300 or bytes_scanned > (100 * 1024 ** 3):  # > 100GB
            return DetectionSeverity.CRITICAL
        elif execution_seconds > 120 or bytes_scanned > (50 * 1024 ** 3):
            return DetectionSeverity.HIGH
        elif execution_seconds > 60:
            return DetectionSeverity.MEDIUM
        return DetectionSeverity.LOW

    def _generate_query_optimization_tips(self, query: Dict[str, Any]) -> str:
        """Generate optimization tips for a query."""
        tips = []

        spilled_local = query.get('bytes_spilled_to_local_storage', 0) or 0
        spilled_remote = query.get('bytes_spilled_to_remote_storage', 0) or 0

        if spilled_local > 0 or spilled_remote > 0:
            tips.append("- Query spilled to disk: optimize WHERE clauses or use larger warehouse")

        bytes_scanned = query.get('bytes_scanned', 0)
        rows_produced = query.get('rows_produced', 0)

        if bytes_scanned > 0 and rows_produced > 0:
            ratio = bytes_scanned / max(rows_produced, 1)
            if ratio > 1000:
                tips.append("- High data-to-result ratio: add filtering or clustering key")

        if not tips:
            tips.append("- Review query logic and consider adding indexes or materialized view")

        return "; ".join(tips)

    def generate_recommendations(self) -> None:
        """Generate performance recommendations based on findings."""
        logger.info(f"Generating recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "slow_query":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Optimize slow query: {finding.resource_name[:8]}",
                    description="Apply query optimization techniques",
                    action_type="optimize_query",
                    resource_type="query",
                    resource_name=finding.resource_name,
                    impact="high",
                    estimated_benefit="Reduce query time by 50-90%"
                )
                rec.add_step("Analyze query profile and execution plan")
                rec.add_step("Identify missing indexes or clustering keys")
                rec.add_step("Add WHERE clause filters to reduce data scanned")
                rec.add_step("Consider materialized view for repeated queries")
                rec.add_step("Test optimization and compare performance")
                self.add_recommendation(rec)

            elif finding.category == "resource_contention":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Scale warehouse: {finding.resource_name}",
                    description=f"Increase capacity of {finding.resource_name}",
                    action_type="scale_warehouse",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step(f"Analyze query patterns for {finding.resource_name}")
                rec.add_step("Determine appropriate warehouse size increase")
                rec.add_step("Request approval for scaling")
                rec.add_step("Execute scaling operation")
                self.add_recommendation(rec)

    def _escalate_critical_findings(self, critical_findings: List[Finding]) -> None:
        """Escalate critical performance findings."""
        for finding in critical_findings:
            logger.warning(f"Escalating critical finding: {finding.title}")

            approver_email = "performance-admin@company.com"
            self.request_approval(
                request_type="critical_performance_action",
                title=f"Critical Performance Issue: {finding.title}",
                description=finding.description,
                context=finding.to_dict(),
                approver_email=approver_email,
                priority="critical",
                sla_hours=2
            )

            self.log_audit_event(
                event_type="critical_performance_finding",
                resource_type=finding.resource_type,
                resource_name=finding.resource_name,
                description=finding.description,
                status="pending"
            )
