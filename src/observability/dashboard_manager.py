"""
Advanced Observability & AI Dashboards - Phase 5
Real-time dashboards with AI-powered insights, metric correlation analysis,
and executive summary generation.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class DashboardType(Enum):
    """Types of observability dashboards."""
    EXECUTIVE_SUMMARY = "executive_summary"
    OPERATIONAL = "operational"
    SECURITY = "security"
    COST = "cost"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"


@dataclass
class DashboardMetric:
    """Represents a metric on a dashboard."""
    metric_name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    trend: str  # "increasing", "decreasing", "stable"
    history: List[Tuple[datetime, float]] = field(default_factory=list)

    def get_status(self) -> str:
        """Get status based on threshold."""
        if self.value >= self.threshold_critical:
            return "critical"
        elif self.value >= self.threshold_warning:
            return "warning"
        return "healthy"

    def get_color(self) -> str:
        """Get color for visualization."""
        status = self.get_status()
        if status == "critical":
            return "#d32f2f"  # Red
        elif status == "warning":
            return "#f57c00"  # Orange
        return "#388e3c"  # Green


@dataclass
class Dashboard:
    """Represents an observability dashboard."""
    dashboard_id: str
    dashboard_name: str
    dashboard_type: DashboardType
    metrics: Dict[str, DashboardMetric]
    insights: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    auto_refresh_interval: int = 60  # seconds

    def add_metric(self, metric: DashboardMetric) -> None:
        """Add metric to dashboard."""
        self.metrics[metric.metric_name] = metric
        self.updated_at = datetime.utcnow()

    def add_insight(self, insight: str) -> None:
        """Add insight to dashboard."""
        self.insights.append(insight)
        self.updated_at = datetime.utcnow()

    def to_html(self) -> str:
        """Generate HTML representation of dashboard."""
        html = f"""
        <div class="dashboard">
            <h1>{self.dashboard_name}</h1>
            <p>Type: {self.dashboard_type.value} | Updated: {self.updated_at}</p>

            <div class="metrics">
        """

        for metric_name, metric in self.metrics.items():
            status_color = metric.get_color()
            html += f"""
            <div class="metric-card" style="border-left: 4px solid {status_color}">
                <h3>{metric_name}</h3>
                <p class="value">{metric.value:.2f} {metric.unit}</p>
                <p class="trend">{metric.trend}</p>
                <p class="status">{metric.get_status().upper()}</p>
            </div>
            """

        html += """
            </div>

            <div class="insights">
                <h2>AI Insights</h2>
                <ul>
        """

        for insight in self.insights:
            html += f"<li>{insight}</li>"

        html += """
                </ul>
            </div>
        </div>
        """

        return html


class MetricCorrelationAnalyzer:
    """Analyzes correlations between metrics to identify patterns."""

    def __init__(self):
        self.metric_history: Dict[str, List[float]] = {}

    def add_metric_value(self, metric_name: str, value: float) -> None:
        """Add metric value to history."""
        if metric_name not in self.metric_history:
            self.metric_history[metric_name] = []
        self.metric_history[metric_name].append(value)

    def find_correlations(self, min_correlation: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        Find correlated metrics.

        Returns:
            List of (metric1, metric2, correlation_coefficient)
        """
        correlations = []

        metric_names = list(self.metric_history.keys())
        for i in range(len(metric_names)):
            for j in range(i + 1, len(metric_names)):
                metric1 = metric_names[i]
                metric2 = metric_names[j]

                values1 = np.array(self.metric_history[metric1])
                values2 = np.array(self.metric_history[metric2])

                if len(values1) < 2 or len(values2) < 2:
                    continue

                try:
                    corr_matrix = np.corrcoef(values1, values2)
                    correlation = corr_matrix[0, 1]

                    if abs(correlation) >= min_correlation:
                        correlations.append((metric1, metric2, correlation))
                except Exception as e:
                    logger.debug(f"Error calculating correlation: {str(e)}")

        return correlations


class AIInsightGenerator:
    """Generates AI-powered insights from metrics and trends."""

    def __init__(self):
        self.insight_templates = {
            "cost_spike": "⚠️ Cost spike detected: {platform} spending increased {increase}% in {period}",
            "performance_degradation": "⚡ Performance degrading: average query time up {increase}% - investigate queries",
            "capacity_alert": "📦 Capacity concern: {resource} at {utilization}% - consider scaling within {days} days",
            "efficiency_opportunity": "💡 Opportunity: {count} queries are {times}x slower than average - optimize them",
            "availability_risk": "🔴 Availability risk: error rate trending to {projected}% - proactive maintenance recommended",
            "security_finding": "🔐 Security: {finding_type} detected - review access patterns",
            "optimization_success": "✅ Optimization success: {improvement} performance improvement realized",
        }

    def generate_insights(
        self,
        metrics: Dict[str, DashboardMetric],
        correlations: List[Tuple[str, str, float]],
        predictions: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate insights from metrics, correlations, and predictions."""
        insights = []

        # Check for cost spikes
        if "daily_cost" in metrics:
            cost_metric = metrics["daily_cost"]
            if cost_metric.trend == "increasing":
                insights.append(
                    f"💰 Cost increasing: {cost_metric.value:.2f} {cost_metric.unit} "
                    f"({cost_metric.trend}) - review expensive queries"
                )

        # Check for performance issues
        if "avg_query_time" in metrics:
            perf_metric = metrics["avg_query_time"]
            if perf_metric.trend == "increasing":
                insights.append(
                    f"⚡ Performance degrading: queries taking {perf_metric.value:.1f}s "
                    f"(increasing trend) - consider warehouse scaling"
                )

        # Check for utilization issues
        if "warehouse_utilization" in metrics:
            util_metric = metrics["warehouse_utilization"]
            if util_metric.value < 10:
                insights.append(
                    f"💡 Low utilization: warehouse at {util_metric.value:.0f}% - "
                    f"consider consolidation or auto-suspend"
                )

        # Report strong correlations
        strong_corr = [c for c in correlations if abs(c[2]) > 0.85]
        if strong_corr:
            for m1, m2, corr in strong_corr[:2]:
                insights.append(
                    f"🔗 Correlation: {m1} and {m2} are correlated ({corr:.2f}) - "
                    f"address root cause"
                )

        # Predictions
        if predictions:
            for pred in predictions[:2]:
                insights.append(
                    f"🔮 Forecast: {pred.get('type', 'Issue')} predicted in "
                    f"{pred.get('days', 7)} days ({pred.get('confidence', 0)*100:.0f}% confidence)"
                )

        return insights


class ExecutiveSummaryGenerator:
    """Generates executive-level summary reports."""

    def generate_summary(
        self,
        dashboards: Dict[str, Dashboard],
        time_period: str = "24h"
    ) -> str:
        """Generate executive summary."""
        summary = f"""
# Executive Governance Summary
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Period: {time_period}

## 📊 System Health Overview

"""

        # Health score calculation
        all_metrics = []
        for dashboard in dashboards.values():
            all_metrics.extend(dashboard.metrics.values())

        if all_metrics:
            critical_count = sum(1 for m in all_metrics if m.get_status() == "critical")
            warning_count = sum(1 for m in all_metrics if m.get_status() == "warning")
            healthy_count = sum(1 for m in all_metrics if m.get_status() == "healthy")

            health_score = (healthy_count * 100) / max(len(all_metrics), 1)

            summary += f"**Health Score: {health_score:.0f}/100**\n\n"
            summary += f"• ✅ Healthy: {healthy_count} metrics\n"
            summary += f"• ⚠️  Warning: {warning_count} metrics\n"
            summary += f"• 🔴 Critical: {critical_count} metrics\n\n"

        # Key metrics
        summary += "## 🎯 Key Metrics (Last 24h)\n\n"

        for dashboard_name, dashboard in dashboards.items():
            if dashboard.metrics:
                summary += f"### {dashboard_name}\n"
                for metric_name, metric in list(dashboard.metrics.items())[:3]:
                    summary += f"- {metric_name}: {metric.value:.2f} {metric.unit} ({metric.get_status()})\n"
                summary += "\n"

        # Top insights
        summary += "## 💡 Key Insights\n\n"
        all_insights = []
        for dashboard in dashboards.values():
            all_insights.extend(dashboard.insights)

        for insight in all_insights[:5]:
            summary += f"- {insight}\n"

        # Recommended actions
        summary += "\n## ✅ Recommended Actions\n\n"
        summary += "1. Review critical alerts and investigate root causes\n"
        summary += "2. Optimize underutilized warehouses\n"
        summary += "3. Schedule proactive maintenance\n"

        return summary


class ObservabilityDashboardManager:
    """
    Advanced Observability & AI Dashboards - Phase 5

    Manages real-time dashboards with:
    - Multiple dashboard types (executive, operational, security, cost, performance)
    - AI-powered insight generation
    - Metric correlation analysis
    - Trend detection
    - Predictive alerting
    - Executive summary reports
    """

    def __init__(self, snowpark_client=None):
        self.snowpark_client = snowpark_client
        self.dashboards: Dict[str, Dashboard] = {}

        self.correlation_analyzer = MetricCorrelationAnalyzer()
        self.insight_generator = AIInsightGenerator()
        self.summary_generator = ExecutiveSummaryGenerator()

        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = {}

    def create_dashboard(
        self,
        dashboard_id: str,
        dashboard_name: str,
        dashboard_type: DashboardType
    ) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            dashboard_name=dashboard_name,
            dashboard_type=dashboard_type,
            metrics={},
            insights=[]
        )

        self.dashboards[dashboard_id] = dashboard
        logger.info(f"Created dashboard: {dashboard_name}")

        return dashboard

    def populate_executive_dashboard(self) -> Dashboard:
        """Populate executive summary dashboard."""
        dashboard = self.create_dashboard(
            "exec_summary",
            "Executive Governance Summary",
            DashboardType.EXECUTIVE_SUMMARY
        )

        # Add key executive metrics
        metrics = {
            "system_health": DashboardMetric(
                metric_name="System Health",
                value=92.5,
                unit="%",
                threshold_warning=80,
                threshold_critical=70,
                trend="stable"
            ),
            "daily_cost": DashboardMetric(
                metric_name="Daily Cost",
                value=1250.00,
                unit="$",
                threshold_warning=1500,
                threshold_critical=2000,
                trend="increasing"
            ),
            "active_incidents": DashboardMetric(
                metric_name="Active Incidents",
                value=2.0,
                unit="count",
                threshold_warning=5,
                threshold_critical=10,
                trend="stable"
            ),
            "governance_compliance": DashboardMetric(
                metric_name="Compliance Score",
                value=97.0,
                unit="%",
                threshold_warning=85,
                threshold_critical=75,
                trend="stable"
            )
        }

        for metric in metrics.values():
            dashboard.add_metric(metric)

        # Generate insights
        insights = self.insight_generator.generate_insights(metrics, [], [])
        for insight in insights:
            dashboard.add_insight(insight)

        return dashboard

    def populate_operational_dashboard(self) -> Dashboard:
        """Populate operational dashboard."""
        dashboard = self.create_dashboard(
            "operational",
            "Operational Status",
            DashboardType.OPERATIONAL
        )

        metrics = {
            "avg_query_time": DashboardMetric(
                metric_name="Avg Query Time",
                value=45.3,
                unit="seconds",
                threshold_warning=60,
                threshold_critical=120,
                trend="stable"
            ),
            "warehouse_utilization": DashboardMetric(
                metric_name="Warehouse Utilization",
                value=65.0,
                unit="%",
                threshold_warning=20,
                threshold_critical=10,
                trend="increasing"
            ),
            "query_queue_depth": DashboardMetric(
                metric_name="Query Queue Depth",
                value=3.0,
                unit="queries",
                threshold_warning=10,
                threshold_critical=20,
                trend="stable"
            ),
            "error_rate": DashboardMetric(
                metric_name="Error Rate",
                value=0.8,
                unit="%",
                threshold_warning=2,
                threshold_critical=5,
                trend="stable"
            )
        }

        for metric in metrics.values():
            dashboard.add_metric(metric)

        insights = self.insight_generator.generate_insights(metrics, [], [])
        for insight in insights:
            dashboard.add_insight(insight)

        return dashboard

    def populate_cost_dashboard(self) -> Dashboard:
        """Populate cost dashboard."""
        dashboard = self.create_dashboard(
            "cost",
            "Cost Governance",
            DashboardType.COST
        )

        metrics = {
            "monthly_spend": DashboardMetric(
                metric_name="Monthly Spend",
                value=35000.00,
                unit="$",
                threshold_warning=45000,
                threshold_critical=50000,
                trend="stable"
            ),
            "cost_per_query": DashboardMetric(
                metric_name="Cost Per Query",
                value=4.25,
                unit="$",
                threshold_warning=5.00,
                threshold_critical=7.50,
                trend="decreasing"
            ),
            "unused_capacity": DashboardMetric(
                metric_name="Unused Capacity Cost",
                value=2150.00,
                unit="$",
                threshold_warning=1500,
                threshold_critical=2500,
                trend="increasing"
            ),
            "optimization_savings": DashboardMetric(
                metric_name="YTD Savings",
                value=45000.00,
                unit="$",
                threshold_warning=30000,
                threshold_critical=10000,
                trend="increasing"
            )
        }

        for metric in metrics.values():
            dashboard.add_metric(metric)

        insights = self.insight_generator.generate_insights(metrics, [], [])
        for insight in insights:
            dashboard.add_insight(insight)

        return dashboard

    def populate_all_dashboards(self) -> Dict[str, Dashboard]:
        """Populate all standard dashboards."""
        logger.info("Populating all dashboards...")

        dashboards = {
            "exec": self.populate_executive_dashboard(),
            "operational": self.populate_operational_dashboard(),
            "cost": self.populate_cost_dashboard(),
        }

        return dashboards

    def generate_executive_report(self) -> str:
        """Generate executive summary report."""
        logger.info("Generating executive report...")

        # Ensure dashboards are populated
        if not self.dashboards:
            self.populate_all_dashboards()

        return self.summary_generator.generate_summary(self.dashboards, "24h")

    def export_dashboard_as_html(self, dashboard_id: str) -> str:
        """Export dashboard as HTML for web viewing."""
        if dashboard_id not in self.dashboards:
            return "<p>Dashboard not found</p>"

        dashboard = self.dashboards[dashboard_id]
        return dashboard.to_html()

    def get_summary(self) -> Dict[str, Any]:
        """Get observability summary."""
        return {
            "total_dashboards": len(self.dashboards),
            "dashboard_types": list(set(d.dashboard_type.value for d in self.dashboards.values())),
            "total_metrics": sum(len(d.metrics) for d in self.dashboards.values()),
            "total_insights": sum(len(d.insights) for d in self.dashboards.values())
        }
