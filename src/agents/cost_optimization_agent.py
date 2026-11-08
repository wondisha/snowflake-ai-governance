"""
Cost Optimization Agent - Tracks costs and identifies optimization opportunities.
Recommends warehouse sizing, auto-suspend settings, and unused resource cleanup.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class CostOptimizationAgent(GovernanceAgent):
    """
    Cost Optimization Agent - Monitors credits and optimizes spending.

    Responsibilities:
    - Track warehouse credit consumption
    - Identify unused resources
    - Recommend cost optimizations
    - Monitor auto-suspend effectiveness
    - Generate cost forecasts
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize Cost Optimization Agent."""
        super().__init__(
            agent_name="CostOptimizationAgent",
            agent_type=AgentType.COST,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # Agent configuration
        self.idle_warehouse_days = 7
        self.high_cost_threshold_daily = 1000  # credits per day
        self.cost_history_days = 30
        self.utilization_threshold = 0.1  # 10% - below this is underutilized

    def execute(self) -> bool:
        """Execute cost optimization checks."""
        try:
            self.start_execution()

            logger.info("Starting Cost Optimization Agent execution")

            # Run detection methods
            self.detect_unused_warehouses()
            self.detect_high_cost_queries()
            self.detect_underutilized_warehouses()
            self.detect_inefficient_auto_suspend()

            # Generate recommendations
            self.generate_recommendations()

            # Process findings
            high_cost_findings = [f for f in self.current_findings if f.severity == DetectionSeverity.CRITICAL]
            if high_cost_findings:
                logger.warning(f"Found {len(high_cost_findings)} high-cost issues")
                self._escalate_cost_findings(high_cost_findings)

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Cost agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DETECTION METHODS
    # ========================================================================

    def detect_unused_warehouses(self) -> None:
        """Detect warehouses with minimal or no activity."""
        logger.info("Detecting unused warehouses...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')

                # Get warehouse costs
                costs = self.snowpark_client.get_warehouse_costs(
                    warehouse_name=warehouse_name,
                    days=self.idle_warehouse_days
                )

                total_credits = sum([c.get('daily_credits', 0) for c in costs])

                if total_credits == 0:
                    finding = Finding(
                        finding_id=None,
                        title=f"Unused warehouse: {warehouse_name}",
                        description=f"Warehouse {warehouse_name} has not been used in {self.idle_warehouse_days} days",
                        severity=DetectionSeverity.MEDIUM,
                        category="unused_resource",
                        resource_type="warehouse",
                        resource_name=warehouse_name,
                        details={
                            "days_unused": self.idle_warehouse_days,
                            "total_credits_last_period": total_credits
                        }
                    )
                    finding.recommendation = f"Consider deleting unused warehouse {warehouse_name}"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Unused warehouse detection failed: {str(e)}")

    def detect_high_cost_queries(self) -> None:
        """Detect individual queries with high credit consumption."""
        logger.info(f"Detecting high-cost queries (threshold: {self.high_cost_threshold_daily} credits/day)...")

        try:
            slow_queries = self.snowpark_client.get_slow_queries(
                threshold_seconds=0,
                hours=24
            )

            for query in slow_queries:
                query_id = query.get('query_id')
                bytes_scanned = query.get('bytes_scanned', 0) or 0

                # Rough cost estimation: 1 credit per 1GB scanned
                estimated_credits = bytes_scanned / (1024 ** 3)

                if estimated_credits > 10:
                    finding = Finding(
                        finding_id=None,
                        title=f"High-cost query: {query_id[:8]}...",
                        description=f"Query estimated to consume {estimated_credits:.1f} credits",
                        severity=DetectionSeverity.HIGH,
                        category="high_cost_query",
                        resource_type="query",
                        resource_name=query_id,
                        details={
                            "estimated_credits": estimated_credits,
                            "data_scanned_gb": bytes_scanned / (1024 ** 3),
                            "user": query.get('user_name'),
                            "warehouse": query.get('warehouse_name')
                        }
                    )
                    finding.recommendation = "Optimize query to reduce data scanned"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"High-cost query detection failed: {str(e)}")

    def detect_underutilized_warehouses(self) -> None:
        """Detect warehouses that are oversized for their usage."""
        logger.info("Detecting underutilized warehouses...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')
                warehouse_size = warehouse.get('warehouse_size')  # XS, S, M, L, XL

                # Get costs over period
                costs = self.snowpark_client.get_warehouse_costs(
                    warehouse_name=warehouse_name,
                    days=self.cost_history_days
                )

                total_credits = sum([c.get('daily_credits', 0) for c in costs])
                avg_daily_credits = total_credits / max(self.cost_history_days, 1)

                # Map warehouse size to baseline cost per day (rough estimates)
                size_costs = {
                    'XS': 4,   # 1 credit/hour
                    'S': 8,    # 2 credits/hour
                    'M': 16,   # 4 credits/hour
                    'L': 32,   # 8 credits/hour
                    'XL': 64   # 16 credits/hour
                }

                baseline_cost = size_costs.get(warehouse_size, 0)
                if baseline_cost > 0:
                    utilization_ratio = avg_daily_credits / baseline_cost

                    if utilization_ratio < self.utilization_threshold:
                        finding = Finding(
                            finding_id=None,
                            title=f"Underutilized warehouse: {warehouse_name}",
                            description=f"Warehouse {warehouse_name} size {warehouse_size} is oversized for usage",
                            severity=DetectionSeverity.MEDIUM,
                            category="underutilized_warehouse",
                            resource_type="warehouse",
                            resource_name=warehouse_name,
                            details={
                                "warehouse_size": warehouse_size,
                                "avg_daily_credits": avg_daily_credits,
                                "utilization_ratio": utilization_ratio,
                                "cost_period_days": self.cost_history_days
                            }
                        )
                        finding.recommendation = f"Consider downscaling {warehouse_name} from {warehouse_size} to smaller size"
                        self.add_finding(finding)

        except Exception as e:
            logger.error(f"Underutilized warehouse detection failed: {str(e)}")

    def detect_inefficient_auto_suspend(self) -> None:
        """Detect warehouses with inefficient auto-suspend settings."""
        logger.info("Detecting inefficient auto-suspend settings...")

        try:
            warehouses = self.snowpark_client.list_warehouses()

            for warehouse in warehouses:
                warehouse_name = warehouse.get('warehouse_name')

                # Get warehouse metrics (would include auto-suspend settings in real implementation)
                metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)

                # In production, this would check:
                # - If auto-suspend is disabled (should be enabled for dev/test)
                # - If auto-suspend timeout is very high (e.g., 60 minutes)
                # - If warehouse rarely reaches the timeout (wasting money)

                logger.debug(f"Auto-suspend analysis for {warehouse_name}: {metrics}")

        except Exception as e:
            logger.error(f"Auto-suspend detection failed: {str(e)}")

    # ========================================================================
    # RECOMMENDATION GENERATION
    # ========================================================================

    def generate_recommendations(self) -> None:
        """Generate cost optimization recommendations."""
        logger.info(f"Generating recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "unused_resource":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Delete unused warehouse: {finding.resource_name}",
                    description=f"Remove unused warehouse {finding.resource_name}",
                    action_type="delete_warehouse",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="low",
                    estimated_benefit=f"Save warehouse maintenance costs"
                )
                rec.add_step(f"Verify {finding.resource_name} is not needed by any teams")
                rec.add_step("Document warehouse purpose and ensure no dependencies")
                rec.add_step("Request approval for deletion")
                rec.add_step(f"Delete warehouse {finding.resource_name}")
                self.add_recommendation(rec)

            elif finding.category == "high_cost_query":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Optimize high-cost query: {finding.resource_name[:8]}",
                    description="Reduce query cost by optimizing execution",
                    action_type="optimize_query",
                    resource_type="query",
                    resource_name=finding.resource_name,
                    impact="high",
                    estimated_benefit=f"Save {finding.details.get('estimated_credits', 0):.0f} credits per execution"
                )
                rec.add_step("Profile query execution and identify inefficiencies")
                rec.add_step("Add WHERE clauses to reduce data scanned")
                rec.add_step("Consider partitioning large tables")
                rec.add_step("Review and optimize joins")
                self.add_recommendation(rec)

            elif finding.category == "underutilized_warehouse":
                current_size = finding.details.get('warehouse_size')
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Downscale warehouse: {finding.resource_name}",
                    description=f"Reduce warehouse from {current_size} to smaller size",
                    action_type="scale_warehouse",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="high",
                    estimated_benefit="Reduce warehouse costs by 50%+"
                )
                rec.add_step(f"Analyze workload on {finding.resource_name}")
                rec.add_step("Determine appropriate smaller size")
                rec.add_step("Schedule downscaling during low-usage period")
                rec.add_step("Monitor performance after downscaling")
                self.add_recommendation(rec)

    def _escalate_cost_findings(self, cost_findings: List[Finding]) -> None:
        """Escalate high-cost findings."""
        for finding in cost_findings:
            logger.warning(f"Escalating cost finding: {finding.title}")

            approver_email = "finance-admin@company.com"
            self.request_approval(
                request_type="high_cost_alert",
                title=f"High Cost Alert: {finding.title}",
                description=finding.description,
                context=finding.to_dict(),
                approver_email=approver_email,
                priority="high",
                sla_hours=4
            )

            self.log_audit_event(
                event_type="high_cost_finding",
                resource_type=finding.resource_type,
                resource_name=finding.resource_name,
                description=finding.description,
                status="pending"
            )
