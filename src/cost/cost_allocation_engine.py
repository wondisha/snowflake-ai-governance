"""
Cost Allocation & Chargeback Engine - Tracks and allocates costs to departments/projects.
Enables chargebacks and cost optimization across the organization.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from enum import Enum

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class CostCenter:
    """Represents a cost center (department, team, project)."""

    def __init__(
        self,
        cost_center_id: str,
        name: str,
        cost_center_type: str = "department",
        owner_email: str = None
    ):
        self.cost_center_id = cost_center_id
        self.name = name
        self.cost_center_type = cost_center_type  # department, project, team, business_unit
        self.owner_email = owner_email

        # Budget tracking
        self.monthly_budget = 10000  # Default $10k/month
        self.current_spend = 0.0
        self.ytd_spend = 0.0
        self.monthly_forecast = 0.0

        # Usage tracking
        self.queries_count = 0
        self.warehouses = []
        self.users = []

    def get_budget_percentage(self) -> float:
        """Get percentage of budget used."""
        if self.monthly_budget == 0:
            return 0.0
        return (self.current_spend / self.monthly_budget) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cost_center_id": self.cost_center_id,
            "name": self.name,
            "type": self.cost_center_type,
            "owner": self.owner_email,
            "monthly_budget": self.monthly_budget,
            "current_spend": self.current_spend,
            "ytd_spend": self.ytd_spend,
            "budget_used_percent": self.get_budget_percentage()
        }


class CostAllocation:
    """Represents an individual cost allocation record."""

    def __init__(
        self,
        query_id: str,
        cost_center_id: str,
        credits_used: float,
        execution_time_seconds: float,
        user_email: str,
        warehouse_name: str
    ):
        self.allocation_id = f"{query_id}_{cost_center_id}_{datetime.utcnow().timestamp()}"
        self.query_id = query_id
        self.cost_center_id = cost_center_id
        self.credits_used = credits_used
        self.execution_time_seconds = execution_time_seconds
        self.user_email = user_email
        self.warehouse_name = warehouse_name
        self.allocation_date = datetime.utcnow().date()

        # Cost metrics
        self.credit_cost_usd = credits_used * 4.0  # $4 per credit
        self.efficiency_score = self._calculate_efficiency()

    def _calculate_efficiency(self) -> float:
        """Calculate query efficiency score (0-100)."""
        # Higher score = more efficient
        # Perfect: 1 credit per second
        if self.execution_time_seconds == 0:
            return 100.0

        efficiency_ratio = self.credits_used / self.execution_time_seconds
        # Normalize to 0-100 scale (1 credit/sec = 100)
        score = max(0, min(100, (1 / efficiency_ratio) * 100 if efficiency_ratio > 0 else 0))
        return round(score, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allocation_id": self.allocation_id,
            "query_id": self.query_id,
            "cost_center_id": self.cost_center_id,
            "credits_used": self.credits_used,
            "cost_usd": self.credit_cost_usd,
            "user": self.user_email,
            "warehouse": self.warehouse_name,
            "efficiency_score": self.efficiency_score
        }


class CostAllocationEngine(GovernanceAgent):
    """
    Cost Allocation & Chargeback Engine - Tracks and allocates costs.

    Responsibilities:
    - Allocate query costs to departments/projects
    - Track budget consumption
    - Forecast monthly/annual costs
    - Generate chargeback reports
    - Identify cost optimization opportunities
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize cost allocation engine."""
        super().__init__(
            agent_name="CostAllocationEngine",
            agent_type=AgentType.COST,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # Cost tracking
        self.cost_centers: Dict[str, CostCenter] = {}
        self.allocations: List[CostAllocation] = []

        # Mappings
        self.user_to_cost_center: Dict[str, str] = {}
        self.warehouse_to_cost_center: Dict[str, str] = {}

        # Configuration
        self.credit_cost_usd = 4.0  # Cost per credit
        self.budget_warning_threshold = 0.80  # 80%
        self.budget_critical_threshold = 0.95  # 95%
        self.efficiency_threshold = 50  # Score < 50 is inefficient

    def execute(self) -> bool:
        """Execute cost allocation analysis."""
        try:
            self.start_execution()

            logger.info("Starting Cost Allocation Engine execution")

            # Initialize cost centers
            self.initialize_cost_centers()

            # Allocate costs
            self.allocate_query_costs()

            # Forecast costs
            self.forecast_costs()

            # Identify cost optimization
            self.identify_optimization_opportunities()

            # Generate findings
            self.generate_cost_findings()

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Cost allocation failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # COST CENTER MANAGEMENT
    # ========================================================================

    def initialize_cost_centers(self) -> None:
        """Initialize cost centers from configuration."""
        logger.info("Initializing cost centers...")

        # Example cost centers (would come from config in production)
        cost_centers_config = [
            {"id": "eng_analytics", "name": "Engineering - Analytics", "type": "department", "budget": 15000},
            {"id": "eng_platform", "name": "Engineering - Platform", "type": "department", "budget": 12000},
            {"id": "finance_reports", "name": "Finance - Reports", "type": "department", "budget": 8000},
            {"id": "data_science", "name": "Data Science", "type": "team", "budget": 20000},
            {"id": "ops", "name": "Operations", "type": "department", "budget": 5000}
        ]

        for config in cost_centers_config:
            cc = CostCenter(config["id"], config["name"], config["type"])
            cc.monthly_budget = config["budget"]
            self.cost_centers[cc.cost_center_id] = cc

        logger.info(f"Initialized {len(self.cost_centers)} cost centers")

    def add_cost_center(
        self,
        cost_center_id: str,
        name: str,
        cost_center_type: str,
        monthly_budget: float
    ) -> bool:
        """Add new cost center."""
        if cost_center_id in self.cost_centers:
            logger.warning(f"Cost center already exists: {cost_center_id}")
            return False

        cc = CostCenter(cost_center_id, name, cost_center_type)
        cc.monthly_budget = monthly_budget
        self.cost_centers[cost_center_id] = cc

        logger.info(f"Added cost center: {cost_center_id}")
        return True

    def map_user_to_cost_center(self, user_email: str, cost_center_id: str) -> bool:
        """Map user to cost center."""
        if cost_center_id not in self.cost_centers:
            logger.error(f"Cost center not found: {cost_center_id}")
            return False

        self.user_to_cost_center[user_email] = cost_center_id
        if user_email not in self.cost_centers[cost_center_id].users:
            self.cost_centers[cost_center_id].users.append(user_email)

        logger.debug(f"Mapped {user_email} to {cost_center_id}")
        return True

    def map_warehouse_to_cost_center(self, warehouse_name: str, cost_center_id: str) -> bool:
        """Map warehouse to cost center."""
        if cost_center_id not in self.cost_centers:
            logger.error(f"Cost center not found: {cost_center_id}")
            return False

        self.warehouse_to_cost_center[warehouse_name] = cost_center_id
        if warehouse_name not in self.cost_centers[cost_center_id].warehouses:
            self.cost_centers[cost_center_id].warehouses.append(warehouse_name)

        logger.debug(f"Mapped {warehouse_name} to {cost_center_id}")
        return True

    # ========================================================================
    # COST ALLOCATION
    # ========================================================================

    def allocate_query_costs(self) -> None:
        """Allocate costs for recent queries to cost centers."""
        logger.info("Allocating query costs...")

        try:
            # Get recent queries
            sql = """
            SELECT
                query_id,
                user_name,
                warehouse_name,
                TIMESTAMPDIFF(second, start_time, end_time) as execution_seconds,
                bytes_scanned,
                rows_produced,
                start_time
            FROM snowflake.account_usage.query_history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '1 days'
                AND execution_status = 'SUCCESS'
            ORDER BY start_time DESC
            LIMIT 1000
            """

            queries = self.snowpark_client.execute_query(sql)

            for query in queries:
                query_id = query.get('query_id')
                user_email = query.get('user_name')
                warehouse = query.get('warehouse_name')
                execution_seconds = query.get('execution_seconds', 0) or 0
                bytes_scanned = query.get('bytes_scanned', 0) or 0

                # Estimate credits (1 credit per GB scanned)
                credits_used = max(0.001, bytes_scanned / (1024 ** 3))

                # Determine cost center
                cost_center_id = self._get_cost_center_for_query(user_email, warehouse)

                if cost_center_id:
                    allocation = CostAllocation(
                        query_id=query_id,
                        cost_center_id=cost_center_id,
                        credits_used=credits_used,
                        execution_time_seconds=execution_seconds,
                        user_email=user_email,
                        warehouse_name=warehouse
                    )

                    self.allocations.append(allocation)

                    # Update cost center
                    self.cost_centers[cost_center_id].current_spend += allocation.credit_cost_usd
                    self.cost_centers[cost_center_id].queries_count += 1

            logger.info(f"Allocated costs for {len(self.allocations)} queries")

        except Exception as e:
            logger.error(f"Cost allocation failed: {str(e)}")

    def _get_cost_center_for_query(self, user_email: str, warehouse_name: str) -> str:
        """Determine cost center for a query."""
        # Try user mapping first
        if user_email in self.user_to_cost_center:
            return self.user_to_cost_center[user_email]

        # Try warehouse mapping
        if warehouse_name in self.warehouse_to_cost_center:
            return self.warehouse_to_cost_center[warehouse_name]

        # Default to "unallocated" (create if needed)
        if "unallocated" not in self.cost_centers:
            self.add_cost_center("unallocated", "Unallocated", "default", 50000)

        return "unallocated"

    # ========================================================================
    # FORECASTING
    # ========================================================================

    def forecast_costs(self) -> None:
        """Forecast monthly and annual costs."""
        logger.info("Forecasting costs...")

        try:
            for cc_id, cost_center in self.cost_centers.items():
                # Get historical spend for this month
                current_day = datetime.utcnow().day
                current_month_spend = cost_center.current_spend

                # Linear forecast: current spend * (days in month / current day)
                days_in_month = 30  # Simplified
                days_remaining = days_in_month - current_day

                if current_day > 0:
                    daily_average = current_month_spend / current_day
                    forecasted_monthly = current_month_spend + (daily_average * days_remaining)
                    forecasted_annual = forecasted_monthly * 12

                    cost_center.monthly_forecast = forecasted_monthly
                    cost_center.ytd_spend = forecasted_annual / 12  # Simplified

                    # Check if forecast exceeds budget
                    if forecasted_monthly > cost_center.monthly_budget:
                        overage_percent = ((forecasted_monthly - cost_center.monthly_budget) / cost_center.monthly_budget) * 100

                        finding = Finding(
                            finding_id=None,
                            title=f"Cost forecast exceeds budget: {cost_center.name}",
                            description=f"Forecasted monthly spend ${forecasted_monthly:.0f} exceeds budget ${cost_center.monthly_budget:.0f}",
                            severity=DetectionSeverity.HIGH,
                            category="budget_forecast",
                            resource_type="cost_center",
                            resource_name=cc_id,
                            details={
                                "forecasted_spend": forecasted_monthly,
                                "budget": cost_center.monthly_budget,
                                "overage_percent": overage_percent,
                                "current_day_spend": current_month_spend
                            }
                        )
                        finding.recommendation = "Review cost optimization opportunities or request budget increase"
                        self.add_finding(finding)

        except Exception as e:
            logger.error(f"Cost forecasting failed: {str(e)}")

    # ========================================================================
    # OPTIMIZATION DETECTION
    # ========================================================================

    def identify_optimization_opportunities(self) -> None:
        """Identify cost optimization opportunities."""
        logger.info("Identifying cost optimization opportunities...")

        try:
            # Inefficient queries
            inefficient_queries = [
                a for a in self.allocations
                if a.efficiency_score < self.efficiency_threshold
            ]

            if inefficient_queries:
                finding = Finding(
                    finding_id=None,
                    title=f"Inefficient queries detected: {len(inefficient_queries)} queries",
                    description=f"Found {len(inefficient_queries)} queries with efficiency score < {self.efficiency_threshold}",
                    severity=DetectionSeverity.MEDIUM,
                    category="inefficient_queries",
                    resource_type="queries",
                    resource_name=f"inefficient_{datetime.utcnow().date()}",
                    details={
                        "count": len(inefficient_queries),
                        "average_efficiency": sum(a.efficiency_score for a in inefficient_queries) / len(inefficient_queries),
                        "total_wasted_credits": sum(a.credits_used for a in inefficient_queries)
                    }
                )
                finding.recommendation = "Optimize inefficient queries to reduce costs"
                self.add_finding(finding)

            # High-spend cost centers
            high_spend_centers = [
                cc for cc in self.cost_centers.values()
                if cc.get_budget_percentage() > self.budget_warning_threshold
            ]

            for cc in high_spend_centers:
                severity = DetectionSeverity.CRITICAL if cc.get_budget_percentage() > self.budget_critical_threshold else DetectionSeverity.HIGH

                finding = Finding(
                    finding_id=None,
                    title=f"High spend alert: {cc.name}",
                    description=f"{cc.name} has spent {cc.get_budget_percentage():.0f}% of monthly budget",
                    severity=severity,
                    category="high_spend",
                    resource_type="cost_center",
                    resource_name=cc.cost_center_id,
                    details={
                        "cost_center": cc.name,
                        "current_spend": cc.current_spend,
                        "budget": cc.monthly_budget,
                        "percent_used": cc.get_budget_percentage()
                    }
                )
                finding.recommendation = "Review usage patterns and optimize or request budget adjustment"
                self.add_finding(finding)

        except Exception as e:
            logger.error(f"Optimization detection failed: {str(e)}")

    def generate_cost_findings(self) -> None:
        """Generate recommendations for cost optimization."""
        logger.info(f"Generating cost findings for {len(self.current_findings)} issues...")

        for finding in self.current_findings:
            if finding.category == "inefficient_queries":
                rec = Recommendation(
                    recommendation_id=None,
                    title="Optimize inefficient queries",
                    description="Improve query efficiency to reduce costs",
                    action_type="optimize_queries",
                    resource_type="queries",
                    resource_name="inefficient",
                    impact="high",
                    estimated_benefit="10-50% cost reduction"
                )
                rec.add_step("Identify queries with lowest efficiency scores")
                rec.add_step("Profile query execution plans")
                rec.add_step("Add clustering keys or indexes")
                rec.add_step("Test optimizations in dev")
                rec.add_step("Deploy to production")
                self.add_recommendation(rec)

            elif finding.category == "high_spend":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Control spending for {finding.resource_name}",
                    description="Implement cost controls for high-spend cost center",
                    action_type="cost_control",
                    resource_type="cost_center",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step("Analyze top cost drivers")
                rec.add_step("Implement warehouse auto-suspend")
                rec.add_step("Set query timeout limits")
                rec.add_step("Review usage by user/team")
                self.add_recommendation(rec)

    # ========================================================================
    # REPORTING
    # ========================================================================

    def generate_chargeback_report(self) -> Dict[str, Any]:
        """Generate chargeback report for all cost centers."""
        report = {}

        for cc_id, cost_center in self.cost_centers.items():
            report[cc_id] = cost_center.to_dict()

        return {
            "report_date": datetime.utcnow().isoformat(),
            "total_spend": sum(cc.current_spend for cc in self.cost_centers.values()),
            "cost_centers": report,
            "allocations_count": len(self.allocations)
        }

    def get_cost_center_summary(self, cost_center_id: str) -> Dict[str, Any]:
        """Get summary for a specific cost center."""
        if cost_center_id not in self.cost_centers:
            return {}

        cc = self.cost_centers[cost_center_id]
        cc_allocations = [a for a in self.allocations if a.cost_center_id == cost_center_id]

        return {
            "cost_center": cc.to_dict(),
            "allocations": len(cc_allocations),
            "average_efficiency": sum(a.efficiency_score for a in cc_allocations) / len(cc_allocations) if cc_allocations else 0,
            "top_users": sorted(
                [(u, len([a for a in cc_allocations if a.user_email == u]))
                 for u in set(a.user_email for a in cc_allocations)],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get cost allocation summary."""
        return {
            "cost_centers": len(self.cost_centers),
            "allocations": len(self.allocations),
            "total_spend": sum(cc.current_spend for cc in self.cost_centers.values()),
            "high_spend_centers": len([cc for cc in self.cost_centers.values() if cc.get_budget_percentage() > self.budget_warning_threshold]),
            "inefficient_queries": len([a for a in self.allocations if a.efficiency_score < self.efficiency_threshold])
        }
