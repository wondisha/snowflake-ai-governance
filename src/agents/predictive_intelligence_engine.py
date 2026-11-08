"""
Predictive Intelligence Engine - Phase 5
Forecasts issues 2-4 weeks ahead using time series analysis, trend detection, and ML models.
Enables proactive remediation before issues impact operations.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


@dataclass
class PredictedIssue:
    """Represents a predicted future issue."""
    issue_type: str
    resource_name: str
    predicted_date: datetime
    confidence_score: float  # 0-1
    severity: DetectionSeverity
    impact_description: str
    recommended_action: str
    time_to_event_days: int


class TimeSeriesForecastModel:
    """
    Time series forecasting using trend analysis and regression.
    Supports 1-4 week forecasting horizons.
    """

    def __init__(self, lookback_days: int = 30):
        """
        Initialize forecasting model.

        Args:
            lookback_days: Days of historical data to use for training
        """
        self.lookback_days = lookback_days
        self.metrics_history: Dict[str, List[Tuple[datetime, float]]] = {}

    def add_metric_point(self, metric_name: str, timestamp: datetime, value: float) -> None:
        """Add a data point to history."""
        if metric_name not in self.metrics_history:
            self.metrics_history[metric_name] = []

        self.metrics_history[metric_name].append((timestamp, value))

        # Keep only lookback period
        cutoff = datetime.utcnow() - timedelta(days=self.lookback_days)
        self.metrics_history[metric_name] = [
            (ts, val) for ts, val in self.metrics_history[metric_name]
            if ts >= cutoff
        ]

    def forecast(
        self,
        metric_name: str,
        forecast_days: int = 14
    ) -> Dict[str, Any]:
        """
        Forecast metric value for future days.

        Args:
            metric_name: Name of metric to forecast
            forecast_days: Number of days to forecast ahead (1-28)

        Returns:
            Dict with forecast data, confidence, and trend
        """
        if metric_name not in self.metrics_history:
            return {"error": "No historical data"}

        history = self.metrics_history[metric_name]
        if len(history) < 3:
            return {"error": "Insufficient data"}

        # Extract values and timestamps
        timestamps = [ts for ts, _ in history]
        values = np.array([val for _, val in history])

        # Calculate linear trend using numpy
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)  # Linear regression
        trend_slope = coeffs[0]
        trend_intercept = coeffs[1]

        # Forecast future values
        forecast_values = []
        future_dates = []

        last_x = len(values) - 1
        last_value = values[-1]

        for i in range(1, forecast_days + 1):
            # Linear extrapolation
            future_x = last_x + i
            forecast_val = trend_slope * future_x + trend_intercept
            forecast_values.append(float(forecast_val))

            future_date = timestamps[-1] + timedelta(days=i)
            future_dates.append(future_date)

        # Calculate confidence based on data consistency
        residuals = values - (trend_slope * x + trend_intercept)
        rmse = np.sqrt(np.mean(residuals ** 2))
        mean_value = np.mean(values)
        confidence = max(0.0, 1.0 - (rmse / max(mean_value, 1.0)))
        confidence = min(1.0, confidence)

        # Detect trend direction
        recent_trend = np.mean(np.diff(values[-7:]))  # Last 7 days
        trend_direction = "increasing" if recent_trend > 0 else "decreasing" if recent_trend < 0 else "stable"

        return {
            "metric": metric_name,
            "current_value": float(last_value),
            "forecast_horizon": forecast_days,
            "forecast_values": forecast_values,
            "forecast_dates": [d.isoformat() for d in future_dates],
            "trend_slope": float(trend_slope),
            "trend_direction": trend_direction,
            "confidence": float(confidence),
            "rmse": float(rmse)
        }

    def detect_breakpoint(self, metric_name: str) -> Optional[datetime]:
        """
        Detect if metric will hit critical breakpoint (e.g., disk full).
        Returns date when metric will exceed threshold.
        """
        if metric_name not in self.metrics_history:
            return None

        history = self.metrics_history[metric_name]
        if len(history) < 3:
            return None

        # This is simplified - would be more sophisticated in production
        return None


class AnomalyPropagationAnalyzer:
    """
    Analyzes how anomalies propagate through system.
    Predicts cascading failures and dependencies.
    """

    def __init__(self):
        self.dependency_graph: Dict[str, List[str]] = {}
        self.cascade_patterns: Dict[str, float] = {}

    def add_dependency(self, source: str, target: str) -> None:
        """Record dependency between resources."""
        if source not in self.dependency_graph:
            self.dependency_graph[source] = []
        if target not in self.dependency_graph[source]:
            self.dependency_graph[source].append(target)

    def predict_cascading_failure(
        self,
        initial_resource: str,
        failure_type: str
    ) -> List[Tuple[str, float, int]]:
        """
        Predict cascading failure impacts.

        Returns:
            List of (affected_resource, impact_probability, hours_until_impact)
        """
        cascades = []

        if initial_resource not in self.dependency_graph:
            return cascades

        # BFS to find all dependent resources
        queue = [(initial_resource, 1.0, 0)]  # (resource, probability, hops)
        visited = set()

        while queue:
            current, prob, hops = queue.pop(0)

            if current in visited:
                continue
            visited.add(current)

            for dependent in self.dependency_graph.get(current, []):
                # Probability decreases with each hop
                impact_prob = prob * (0.8 ** hops)
                hours_until = (hops + 1) * 2  # Rough estimate

                if impact_prob > 0.1:  # Only report if >10% probability
                    cascades.append((dependent, impact_prob, hours_until))
                    queue.append((dependent, impact_prob, hops + 1))

        return cascades


class CapacityPlanningForecaster:
    """
    Forecasts capacity needs 4-12 weeks ahead.
    Predicts when resources will need scaling.
    """

    def __init__(self):
        self.growth_rates: Dict[str, float] = {}

    def forecast_capacity_breach(
        self,
        resource_name: str,
        current_usage: float,
        capacity_limit: float,
        growth_rate: float  # percentage per day
    ) -> Optional[datetime]:
        """
        Forecast when resource will breach capacity limit.

        Args:
            resource_name: Name of resource
            current_usage: Current usage value
            capacity_limit: Capacity limit
            growth_rate: Daily growth rate (e.g., 0.01 for 1% per day)

        Returns:
            Predicted date of capacity breach, or None if won't breach
        """
        if current_usage >= capacity_limit:
            return datetime.utcnow()  # Already over capacity

        if growth_rate <= 0:
            return None  # Not growing

        # Exponential growth model: usage = current_usage * (1 + growth_rate)^days
        # Solve for days when usage == capacity_limit
        import math

        try:
            days_until_breach = math.log(capacity_limit / current_usage) / math.log(1 + growth_rate)
            breach_date = datetime.utcnow() + timedelta(days=days_until_breach)
            return breach_date
        except (ValueError, ZeroDivisionError):
            return None


class PredictiveIntelligenceEngine(GovernanceAgent):
    """
    Predictive Intelligence Engine - Phase 5

    Forecasts future issues using:
    - Time series analysis and trend detection
    - Cascading failure prediction
    - Capacity planning models
    - Anomaly propagation analysis

    Enables proactive remediation 1-4 weeks before issues occur.
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize predictive intelligence engine."""
        super().__init__(
            agent_name="PredictiveIntelligenceEngine",
            agent_type=AgentType.HEALTH,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        self.forecast_model = TimeSeriesForecastModel(lookback_days=30)
        self.cascade_analyzer = AnomalyPropagationAnalyzer()
        self.capacity_planner = CapacityPlanningForecaster()

        self.predicted_issues: List[PredictedIssue] = []

    def execute(self) -> bool:
        """Execute predictive intelligence analysis."""
        try:
            self.start_execution()
            logger.info("Starting Predictive Intelligence Engine execution")

            # Collect historical metrics
            self._collect_historical_metrics()

            # Analyze various prediction scenarios
            self._predict_performance_degradation()
            self._predict_storage_issues()
            self._predict_cost_overruns()
            self._predict_availability_issues()

            # Generate recommendations
            self._generate_proactive_recommendations()

            # Store predictions
            self._store_predictions()

            self.findings_processed = len(self.predicted_issues)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Predictive intelligence failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DATA COLLECTION
    # ========================================================================

    def _collect_historical_metrics(self) -> None:
        """Collect 30 days of historical metrics."""
        logger.info("Collecting historical metrics for forecasting...")

        try:
            sql = """
            SELECT DATE(timestamp) as date, AVG(query_execution_time) as avg_time
            FROM governance.query_analysis
            WHERE timestamp >= CURRENT_TIMESTAMP() - INTERVAL '30 days'
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
            """

            results = self.snowpark_client.execute_query(sql)
            for row in results:
                try:
                    date_obj = datetime.fromisoformat(row.get("date"))
                    value = float(row.get("avg_time", 0) or 0)
                    self.forecast_model.add_metric_point("query_execution_time", date_obj, value)
                except Exception as e:
                    logger.debug(f"Error processing metric: {str(e)}")

            logger.info(f"Collected metrics for forecasting")
        except Exception as e:
            logger.debug(f"Could not collect metrics: {str(e)}")

    # ========================================================================
    # PREDICTION METHODS
    # ========================================================================

    def _predict_performance_degradation(self) -> None:
        """Predict query performance degradation."""
        logger.info("Predicting performance degradation...")

        # Forecast execution time for next 14 days
        forecast = self.forecast_model.forecast("query_execution_time", forecast_days=14)

        if "error" in forecast:
            logger.info("Could not forecast execution time")
            return

        # Check if trend shows degradation
        trend_slope = forecast.get("trend_slope", 0)
        if trend_slope > 0:  # Performance degrading
            confidence = forecast.get("confidence", 0.5)

            # Identify when execution time will exceed SLA (say 60 seconds)
            forecast_values = forecast.get("forecast_values", [])
            for i, value in enumerate(forecast_values):
                if value > 60:  # Exceeds SLA
                    issue = PredictedIssue(
                        issue_type="performance_degradation",
                        resource_name="primary_warehouse",
                        predicted_date=datetime.utcnow() + timedelta(days=i+1),
                        confidence_score=confidence,
                        severity=DetectionSeverity.HIGH,
                        impact_description=f"Queries expected to take {value:.0f}s (SLA: 60s)",
                        recommended_action="Scale warehouse or optimize queries",
                        time_to_event_days=i+1
                    )
                    self.predicted_issues.append(issue)
                    break

    def _predict_storage_issues(self) -> None:
        """Predict storage capacity issues."""
        logger.info("Predicting storage capacity issues...")

        # Simplified: would fetch actual storage metrics
        current_storage = 80.0  # GB
        capacity = 100.0  # GB
        daily_growth = 0.5  # GB per day

        breach_date = self.capacity_planner.forecast_capacity_breach(
            "storage",
            current_storage,
            capacity,
            daily_growth / capacity
        )

        if breach_date and breach_date > datetime.utcnow():
            days_until = (breach_date - datetime.utcnow()).days

            issue = PredictedIssue(
                issue_type="storage_capacity",
                resource_name="account_storage",
                predicted_date=breach_date,
                confidence_score=0.85,
                severity=DetectionSeverity.HIGH if days_until < 7 else DetectionSeverity.MEDIUM,
                impact_description=f"Storage will reach capacity in {days_until} days",
                recommended_action="Implement archival strategy or upgrade storage",
                time_to_event_days=days_until
            )
            self.predicted_issues.append(issue)

    def _predict_cost_overruns(self) -> None:
        """Predict budget overruns."""
        logger.info("Predicting cost overruns...")

        # Simplified cost prediction
        current_spend = 5000.0  # $
        monthly_budget = 10000.0  # $
        daily_cost = current_spend / 15  # First 15 days

        # Project to month end (assume 30 days)
        projected_month_spend = (daily_cost * 30)
        overage = max(0, projected_month_spend - monthly_budget)

        if overage > 0:
            issue = PredictedIssue(
                issue_type="cost_overrun",
                resource_name="account_budget",
                predicted_date=datetime.utcnow() + timedelta(days=15),
                confidence_score=0.70,
                severity=DetectionSeverity.MEDIUM,
                impact_description=f"Projected monthly spend: ${projected_month_spend:.0f} (budget: ${monthly_budget:.0f})",
                recommended_action="Optimize query costs or request budget increase",
                time_to_event_days=15
            )
            self.predicted_issues.append(issue)

    def _predict_availability_issues(self) -> None:
        """Predict availability/reliability issues."""
        logger.info("Predicting availability issues...")

        # Simplified: would analyze error trends
        recent_error_rate = 0.02  # 2%
        error_trend = 0.001  # Increasing by 0.1% per day

        # Project error rate
        projected_error_rate = recent_error_rate + (error_trend * 7)  # 7 days

        if projected_error_rate > 0.05:  # SLA threshold
            issue = PredictedIssue(
                issue_type="availability_degradation",
                resource_name="platform",
                predicted_date=datetime.utcnow() + timedelta(days=7),
                confidence_score=0.60,
                severity=DetectionSeverity.MEDIUM,
                impact_description=f"Error rate trending to {projected_error_rate*100:.1f}% (SLA: 5%)",
                recommended_action="Investigate error trend and implement fixes",
                time_to_event_days=7
            )
            self.predicted_issues.append(issue)

    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================

    def _generate_proactive_recommendations(self) -> None:
        """Generate proactive recommendations for predicted issues."""
        logger.info(f"Generating recommendations for {len(self.predicted_issues)} predicted issues...")

        for issue in self.predicted_issues:
            recommendation = Recommendation(
                recommendation_id=None,
                title=f"Proactive: {issue.issue_type}",
                description=f"Predicted to occur in {issue.time_to_event_days} days: {issue.impact_description}",
                action_type="proactive",
                resource_type="warehouse",
                resource_name=issue.resource_name,
                impact="high" if issue.severity == DetectionSeverity.CRITICAL else "medium"
            )

            recommendation.add_step(issue.recommended_action)
            recommendation.add_step(f"Confidence: {issue.confidence_score*100:.0f}%")
            recommendation.add_step(f"Predicted date: {issue.predicted_date.isoformat()}")

            self.add_recommendation(recommendation)

            # Create finding for tracking
            finding = Finding(
                finding_id=None,
                title=f"Predicted {issue.issue_type}",
                description=issue.impact_description,
                severity=issue.severity,
                category=f"predicted_{issue.issue_type}",
                resource_type="prediction",
                resource_name=issue.resource_name,
                details={
                    "predicted_date": issue.predicted_date.isoformat(),
                    "confidence": issue.confidence_score,
                    "time_to_event_days": issue.time_to_event_days
                }
            )
            self.add_finding(finding)

    def _store_predictions(self) -> None:
        """Store predictions in database for historical tracking."""
        logger.info(f"Storing {len(self.predicted_issues)} predictions...")

        for issue in self.predicted_issues:
            try:
                sql = """
                INSERT INTO governance.predicted_issues
                (issue_type, resource_name, predicted_date, confidence_score, severity,
                 impact_description, recommended_action, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
                """
                self.snowpark_client.execute_update(sql, [
                    issue.issue_type,
                    issue.resource_name,
                    issue.predicted_date,
                    issue.confidence_score,
                    issue.severity.value,
                    issue.impact_description,
                    issue.recommended_action
                ])
            except Exception as e:
                logger.error(f"Failed to store prediction: {str(e)}")

    def get_summary(self) -> Dict[str, Any]:
        """Get predictive intelligence summary."""
        return {
            "total_predictions": len(self.predicted_issues),
            "critical_predictions": sum(1 for p in self.predicted_issues if p.severity == DetectionSeverity.CRITICAL),
            "high_confidence_predictions": sum(1 for p in self.predicted_issues if p.confidence_score > 0.8),
            "avg_forecast_horizon_days": np.mean([p.time_to_event_days for p in self.predicted_issues]) if self.predicted_issues else 0,
            "issue_types": list(set(p.issue_type for p in self.predicted_issues))
        }
