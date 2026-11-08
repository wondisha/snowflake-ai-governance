"""
Warehouse Health Agent - Monitors warehouse health and predicts failures.
Tracks metrics like CPU, memory, queue depth, and error rates.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class WarehouseHealthAgent(GovernanceAgent):
    """
    Warehouse Health Agent - Monitors and predicts warehouse issues.

    Responsibilities:
    - Track warehouse metrics (CPU, memory, queue depth)
    - Detect performance degradation
    - Predict warehouse failures
    - Monitor error rates
    - Alert on queue buildup
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize Warehouse Health Agent."""
        super().__init__(
            agent_name="WarehouseHealthAgent",
            agent_type=AgentType.HEALTH,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # Health thresholds
        self.queue_depth_warning = 5
        self.queue_depth_critical = 20
        self.error_rate_threshold = 0.05  # 5%
        self.failure_prediction_threshold = 0.7  # 70% probability

    def execute(self) -> bool:
        """Execute warehouse health checks."""
        try:
            self.start_execution()

            logger.info("Starting Warehouse Health Agent execution")

            # Run detection methods
            self.collect_warehouse_metrics()
            self.detect_queue_issues()
            self.detect_high_error_rates()
            self.predict_warehouse_failures()
            self.detect_performance_degradation()

            # Generate recommendations
            self.generate_recommendations()

            # Process critical findings
            critical_findings = self.get_critical_findings()
            if critical_findings:
                logger.warning(f"Found {len(critical_findings)} critical health issues")
                self._escalate_critical_findings(critical_findings)

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Health agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DETECTION METHODS
    # ========================================================================

    def collect_warehouse_metrics(self) -> None:
        """Collect current warehouse health metrics."""
        logger.info("Collecting warehouse health metrics...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')
                state = warehouse.get('state')

                # Get current metrics
                metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)

                # Store metrics in governance schema
                health_data = {
                    "health_id": f"{warehouse_name}_{datetime.utcnow().isoformat()}",
                    "warehouse_name": warehouse_name,
                    "metric_timestamp": datetime.utcnow().isoformat(),
                    "warehouse_size": metrics.get('warehouse_size'),
                    "state": state,
                    "active_queries": metrics.get('running', 0),
                    "queued_queries": metrics.get('queued', 0),
                    "health_status": "healthy"  # Will be updated based on metrics
                }

                logger.debug(f"Warehouse {warehouse_name} metrics: running={metrics.get('running')}, queued={metrics.get('queued')}")

        except Exception as e:
            logger.error(f"Metric collection failed: {str(e)}")

    def detect_queue_issues(self) -> None:
        """Detect queue buildup issues."""
        logger.info("Detecting queue issues...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')
                metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)

                queued = metrics.get('queued', 0)
                running = metrics.get('running', 0)
                state = metrics.get('state')

                # Check warning threshold
                if self.queue_depth_warning <= queued < self.queue_depth_critical:
                    finding = Finding(
                        finding_id=None,
                        title=f"Queue buildup warning: {warehouse_name}",
                        description=f"Warehouse {warehouse_name} has {queued} queued queries",
                        severity=DetectionSeverity.MEDIUM,
                        category="queue_buildup",
                        resource_type="warehouse",
                        resource_name=warehouse_name,
                        details={
                            "queued_queries": queued,
                            "running_queries": running,
                            "warehouse_state": state
                        }
                    )
                    finding.recommendation = f"Monitor queue on {warehouse_name} or consider scaling"
                    self.add_finding(finding)

                # Check critical threshold
                elif queued >= self.queue_depth_critical:
                    finding = Finding(
                        finding_id=None,
                        title=f"Critical queue buildup: {warehouse_name}",
                        description=f"Warehouse {warehouse_name} has {queued} queued queries (CRITICAL)",
                        severity=DetectionSeverity.CRITICAL,
                        category="queue_critical",
                        resource_type="warehouse",
                        resource_name=warehouse_name,
                        details={
                            "queued_queries": queued,
                            "running_queries": running,
                            "warehouse_state": state
                        }
                    )
                    finding.recommendation = f"Scale up {warehouse_name} immediately"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Queue detection failed: {str(e)}")

    def detect_high_error_rates(self) -> None:
        """Detect warehouses with high error rates."""
        logger.info("Detecting high error rates...")

        try:
            # Query for recent query errors
            sql = """
            SELECT
                warehouse_name,
                COUNT(*) as total_queries,
                SUM(CASE WHEN execution_status = 'FAIL' THEN 1 ELSE 0 END) as failed_queries
            FROM snowflake.account_usage.query_history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '1 hours'
            GROUP BY warehouse_name
            """
            error_stats = self.snowpark_client.execute_query(sql)

            for stats in error_stats:
                warehouse_name = stats.get('warehouse_name')
                total = stats.get('total_queries', 0)
                failed = stats.get('failed_queries', 0)

                if total > 0:
                    error_rate = failed / total

                    if error_rate > self.error_rate_threshold:
                        severity = DetectionSeverity.CRITICAL if error_rate > 0.1 else DetectionSeverity.HIGH

                        finding = Finding(
                            finding_id=None,
                            title=f"High error rate: {warehouse_name}",
                            description=f"Warehouse {warehouse_name} has {error_rate*100:.1f}% query failure rate",
                            severity=severity,
                            category="high_error_rate",
                            resource_type="warehouse",
                            resource_name=warehouse_name,
                            details={
                                "error_rate": error_rate,
                                "failed_queries": failed,
                                "total_queries": total
                            }
                        )
                        finding.recommendation = f"Investigate error logs for {warehouse_name}"
                        self.add_finding(finding)

        except Exception as e:
            logger.error(f"Error rate detection failed: {str(e)}")

    def predict_warehouse_failures(self) -> None:
        """Predict potential warehouse failures based on patterns."""
        logger.info("Predicting warehouse failures...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')

                # In production, this would use ML model trained on historical data
                # For now, we use heuristics based on recent error trends

                sql = f"""
                SELECT
                    DATE_TRUNC('hour', start_time) as hour,
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN execution_status = 'FAIL' THEN 1 ELSE 0 END) as failed_queries
                FROM snowflake.account_usage.query_history
                WHERE warehouse_name = '{warehouse_name}'
                    AND start_time >= CURRENT_TIMESTAMP() - INTERVAL '24 hours'
                GROUP BY DATE_TRUNC('hour', start_time)
                ORDER BY hour DESC
                LIMIT 24
                """

                hourly_stats = self.snowpark_client.execute_query(sql)

                if len(hourly_stats) > 0:
                    # Calculate trend
                    recent_errors = sum([s.get('failed_queries', 0) for s in hourly_stats[:3]])
                    earlier_errors = sum([s.get('failed_queries', 0) for s in hourly_stats[3:12]])

                    if earlier_errors > 0:
                        error_trend = recent_errors / max(earlier_errors, 1)

                        # If error rate increasing, flag for prediction
                        if error_trend > 1.5:  # 50% increase in error rate
                            failure_probability = min(0.95, error_trend * 0.3)

                            if failure_probability > self.failure_prediction_threshold:
                                finding = Finding(
                                    finding_id=None,
                                    title=f"Warehouse failure prediction: {warehouse_name}",
                                    description=f"Warehouse {warehouse_name} shows {failure_probability*100:.0f}% probability of failure in next 1-4 hours",
                                    severity=DetectionSeverity.CRITICAL,
                                    category="failure_prediction",
                                    resource_type="warehouse",
                                    resource_name=warehouse_name,
                                    details={
                                        "failure_probability": failure_probability,
                                        "error_trend": error_trend,
                                        "recent_error_count": recent_errors
                                    }
                                )
                                finding.recommendation = f"Proactively restart {warehouse_name} or scale up"
                                self.add_finding(finding)

        except Exception as e:
            logger.error(f"Failure prediction failed: {str(e)}")

    def detect_performance_degradation(self) -> None:
        """Detect gradual performance degradation."""
        logger.info("Detecting performance degradation...")

        try:
            # Compare query performance over time
            sql = """
            WITH hourly_performance AS (
                SELECT
                    warehouse_name,
                    DATE_TRUNC('hour', start_time) as hour,
                    AVG(TIMESTAMPDIFF(second, start_time, end_time)) as avg_execution_seconds
                FROM snowflake.account_usage.query_history
                WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '7 days'
                GROUP BY warehouse_name, DATE_TRUNC('hour', start_time)
            )
            SELECT
                warehouse_name,
                avg(avg_execution_seconds) as baseline_avg,
                max(avg_execution_seconds) as peak_avg
            FROM hourly_performance
            GROUP BY warehouse_name
            """

            perf_stats = self.snowpark_client.execute_query(sql)

            for stats in perf_stats:
                warehouse_name = stats.get('warehouse_name')
                baseline = stats.get('baseline_avg', 0)
                peak = stats.get('peak_avg', 0)

                if baseline > 0:
                    degradation_ratio = peak / baseline

                    if degradation_ratio > 2.0:  # 2x increase in average execution time
                        finding = Finding(
                            finding_id=None,
                            title=f"Performance degradation: {warehouse_name}",
                            description=f"Average query time increased {degradation_ratio:.1f}x on {warehouse_name}",
                            severity=DetectionSeverity.HIGH,
                            category="performance_degradation",
                            resource_type="warehouse",
                            resource_name=warehouse_name,
                            details={
                                "baseline_avg_seconds": baseline,
                                "peak_avg_seconds": peak,
                                "degradation_ratio": degradation_ratio
                            }
                        )
                        finding.recommendation = f"Investigate performance issues on {warehouse_name}"
                        self.add_finding(finding)

        except Exception as e:
            logger.error(f"Degradation detection failed: {str(e)}")

    # ========================================================================
    # RECOMMENDATION GENERATION
    # ========================================================================

    def generate_recommendations(self) -> None:
        """Generate health recommendations."""
        logger.info(f"Generating recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "queue_buildup":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Resolve queue on: {finding.resource_name}",
                    description=f"Address queue buildup on {finding.resource_name}",
                    action_type="scale_warehouse",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="high"
                )
                rec.add_step(f"Check query patterns on {finding.resource_name}")
                rec.add_step("Identify long-running queries")
                rec.add_step("Scale up warehouse or optimize queries")
                rec.add_step("Monitor queue until cleared")
                self.add_recommendation(rec)

            elif finding.category == "high_error_rate":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Investigate errors: {finding.resource_name}",
                    description=f"High error rate on {finding.resource_name}",
                    action_type="investigate",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="high"
                )
                rec.add_step(f"Check error logs for {finding.resource_name}")
                rec.add_step("Identify common failure patterns")
                rec.add_step("Restart warehouse if necessary")
                rec.add_step("Monitor for recovery")
                self.add_recommendation(rec)

            elif finding.category == "failure_prediction":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Prevent failure: {finding.resource_name}",
                    description=f"Take proactive action on {finding.resource_name}",
                    action_type="proactive_maintenance",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="critical"
                )
                rec.add_step(f"Schedule restart of {finding.resource_name}")
                rec.add_step("Or scale up warehouse before failure")
                rec.add_step("Monitor closely for next 4 hours")
                self.add_recommendation(rec)

    def _escalate_critical_findings(self, critical_findings: List[Finding]) -> None:
        """Escalate critical health findings."""
        for finding in critical_findings:
            logger.warning(f"Escalating critical finding: {finding.title}")

            approver_email = "warehouse-admin@company.com"
            self.request_approval(
                request_type="critical_health_action",
                title=f"Critical Health Issue: {finding.title}",
                description=finding.description,
                context=finding.to_dict(),
                approver_email=approver_email,
                priority="critical",
                sla_hours=1
            )

            self.log_audit_event(
                event_type="critical_health_finding",
                resource_type=finding.resource_type,
                resource_name=finding.resource_name,
                description=finding.description,
                status="pending"
            )
