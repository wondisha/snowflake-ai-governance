"""
ML Anomaly Detection & Prediction Engine - Advanced machine learning for predictions.
Detects anomalies, predicts failures, and forecasts future issues.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import deque
import json

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class TimeSeriesAnalyzer:
    """Analyzes time series data for anomalies and trends."""

    def __init__(self, window_size: int = 24):
        """
        Initialize time series analyzer.

        Args:
            window_size: Number of periods to keep in rolling window
        """
        self.window_size = window_size
        self.data_points: deque = deque(maxlen=window_size)

    def add_point(self, value: float, timestamp: datetime = None) -> None:
        """Add data point to time series."""
        self.data_points.append({
            "value": value,
            "timestamp": timestamp or datetime.utcnow()
        })

    def calculate_statistics(self) -> Dict[str, float]:
        """Calculate mean, std dev, min, max."""
        if not self.data_points:
            return {}

        values = [p["value"] for p in self.data_points]
        return {
            "mean": float(np.mean(values)),
            "std_dev": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "median": float(np.median(values))
        }

    def detect_anomaly(self, new_value: float, threshold_sigma: float = 3.0) -> Tuple[bool, float]:
        """
        Detect anomaly using z-score method.

        Args:
            new_value: New data point
            threshold_sigma: Standard deviations for anomaly (default: 3.0 = 99.7%)

        Returns:
            Tuple of (is_anomaly, z_score)
        """
        if len(self.data_points) < 2:
            return False, 0.0

        stats = self.calculate_statistics()
        if stats["std_dev"] == 0:
            return False, 0.0

        z_score = (new_value - stats["mean"]) / stats["std_dev"]
        is_anomaly = abs(z_score) > threshold_sigma

        return is_anomaly, z_score

    def calculate_trend(self) -> str:
        """Calculate trend direction (up, down, stable)."""
        if len(self.data_points) < 2:
            return "unknown"

        values = [p["value"] for p in self.data_points]
        recent = np.mean(values[-5:]) if len(values) >= 5 else values[-1]
        historical = np.mean(values[:-5]) if len(values) > 5 else values[0]

        if recent > historical * 1.1:  # 10% increase
            return "up"
        elif recent < historical * 0.9:  # 10% decrease
            return "down"
        else:
            return "stable"

    def forecast_next_value(self, periods: int = 1) -> List[float]:
        """
        Simple linear regression forecast.

        Args:
            periods: Number of periods to forecast

        Returns:
            List of forecasted values
        """
        if len(self.data_points) < 2:
            return []

        values = np.array([p["value"] for p in self.data_points])
        x = np.arange(len(values))

        # Linear regression
        coeffs = np.polyfit(x, values, 1)
        poly = np.poly1d(coeffs)

        forecasts = []
        for i in range(periods):
            forecast_x = len(values) + i
            forecasts.append(float(poly(forecast_x)))

        return forecasts


class AnomalyDetectionModel:
    """ML-based anomaly detection model."""

    def __init__(self):
        """Initialize anomaly detection model."""
        self.analyzers: Dict[str, TimeSeriesAnalyzer] = {}
        self.anomaly_history: List[Dict[str, Any]] = []
        self.model_config = {
            "z_score_threshold": 3.0,  # 99.7% confidence
            "trend_threshold": 1.5,  # 50% change triggers attention
            "memory_size": 24,  # 24 hour window
            "min_data_points": 5
        }

    def add_metric(self, metric_name: str, value: float, timestamp: datetime = None) -> None:
        """Add metric value to analyzer."""
        if metric_name not in self.analyzers:
            self.analyzers[metric_name] = TimeSeriesAnalyzer(self.model_config["memory_size"])

        self.analyzers[metric_name].add_point(value, timestamp)

    def detect_anomalies(self, metric_name: str, new_value: float) -> Dict[str, Any]:
        """
        Detect anomalies in a metric.

        Returns:
            Dictionary with anomaly details
        """
        if metric_name not in self.analyzers:
            return {"anomalies": [], "status": "insufficient_data"}

        analyzer = self.analyzers[metric_name]

        if len(analyzer.data_points) < self.model_config["min_data_points"]:
            return {"anomalies": [], "status": "insufficient_data"}

        anomalies = []

        # Z-score anomaly
        is_anomaly, z_score = analyzer.detect_anomaly(new_value, self.model_config["z_score_threshold"])
        if is_anomaly:
            anomalies.append({
                "type": "statistical_anomaly",
                "z_score": z_score,
                "severity": "high" if abs(z_score) > 4 else "medium"
            })

        # Trend anomaly
        trend = analyzer.calculate_trend()
        stats = analyzer.calculate_statistics()

        if trend == "up" and new_value > stats["mean"] * self.model_config["trend_threshold"]:
            anomalies.append({
                "type": "trend_anomaly",
                "trend": "upward",
                "magnitude": new_value / stats["mean"],
                "severity": "high"
            })

        return {
            "metric": metric_name,
            "anomalies": anomalies,
            "trend": trend,
            "z_score": z_score,
            "statistics": stats,
            "status": "anomalous" if anomalies else "normal"
        }

    def forecast(self, metric_name: str, periods: int = 7) -> Dict[str, Any]:
        """
        Forecast metric values.

        Args:
            metric_name: Metric to forecast
            periods: Number of periods to forecast

        Returns:
            Forecast data
        """
        if metric_name not in self.analyzers:
            return {"status": "no_data"}

        analyzer = self.analyzers[metric_name]
        if len(analyzer.data_points) < 2:
            return {"status": "insufficient_data"}

        forecasts = analyzer.forecast_next_value(periods)

        return {
            "metric": metric_name,
            "forecasts": forecasts,
            "periods": periods,
            "trend": analyzer.calculate_trend()
        }


class MLAnomalyDetectionAgent(GovernanceAgent):
    """
    ML Anomaly Detection Agent - Uses machine learning for predictions.

    Responsibilities:
    - Detect statistical anomalies in metrics
    - Forecast future values
    - Predict failures before they happen
    - Learn patterns from history
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize ML anomaly detection agent."""
        super().__init__(
            agent_name="MLAnomalyDetectionAgent",
            agent_type=AgentType.HEALTH,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # ML models
        self.anomaly_model = AnomalyDetectionModel()

        # Metrics to monitor
        self.monitored_metrics = {
            "query_execution_time": "warehouse",
            "error_rate": "warehouse",
            "queue_depth": "warehouse",
            "cost_per_day": "account",
            "credit_usage": "warehouse"
        }

        # Configuration
        self.failure_prediction_threshold = 0.7  # 70% probability
        self.anomaly_alert_threshold = 0.95  # 95% confidence

    def execute(self) -> bool:
        """Execute ML anomaly detection."""
        try:
            self.start_execution()

            logger.info("Starting ML Anomaly Detection Agent execution")

            # Collect historical metrics
            self.collect_metrics()

            # Detect anomalies
            self.detect_current_anomalies()

            # Predict failures
            self.predict_failures()

            # Generate recommendations
            self.generate_ml_recommendations()

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"ML detection agent failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # METRICS COLLECTION
    # ========================================================================

    def collect_metrics(self) -> None:
        """Collect historical metrics from Snowflake."""
        logger.info("Collecting historical metrics...")

        try:
            # Get query execution time metrics
            sql = """
            SELECT
                DATE_TRUNC('hour', start_time) as hour,
                AVG(TIMESTAMPDIFF(second, start_time, end_time)) as avg_execution_seconds
            FROM snowflake.account_usage.query_history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '7 days'
            GROUP BY DATE_TRUNC('hour', start_time)
            ORDER BY hour DESC
            LIMIT 168
            """

            try:
                results = self.snowpark_client.execute_query(sql)
                for row in results[-24:]:  # Last 24 hours
                    value = row.get('avg_execution_seconds', 0) or 0
                    timestamp = row.get('hour')
                    self.anomaly_model.add_metric("query_execution_time", float(value), timestamp)
            except Exception as e:
                logger.debug(f"Could not collect query metrics: {str(e)}")

            # Get error rate metrics
            sql = """
            SELECT
                DATE_TRUNC('hour', start_time) as hour,
                COUNT(*) as total_queries,
                SUM(CASE WHEN execution_status = 'FAIL' THEN 1 ELSE 0 END) as failed_queries
            FROM snowflake.account_usage.query_history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '7 days'
            GROUP BY DATE_TRUNC('hour', start_time)
            ORDER BY hour DESC
            LIMIT 168
            """

            try:
                results = self.snowpark_client.execute_query(sql)
                for row in results[-24:]:
                    total = row.get('total_queries', 0) or 1
                    failed = row.get('failed_queries', 0) or 0
                    error_rate = (failed / total) * 100
                    timestamp = row.get('hour')
                    self.anomaly_model.add_metric("error_rate", float(error_rate), timestamp)
            except Exception as e:
                logger.debug(f"Could not collect error metrics: {str(e)}")

        except Exception as e:
            logger.error(f"Metric collection failed: {str(e)}")

    def detect_current_anomalies(self) -> None:
        """Detect anomalies in current metrics."""
        logger.info("Detecting anomalies in current metrics...")

        try:
            # Get current metrics
            sql = """
            SELECT
                AVG(TIMESTAMPDIFF(second, start_time, end_time)) as current_execution_seconds
            FROM snowflake.account_usage.query_history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '1 hours'
            """

            try:
                results = self.snowpark_client.execute_query(sql)
                if results:
                    current_value = results[0].get('current_execution_seconds', 0) or 0
                    result = self.anomaly_model.detect_anomalies("query_execution_time", float(current_value))

                    if result["status"] == "anomalous":
                        for anomaly in result.get("anomalies", []):
                            severity = DetectionSeverity.HIGH if anomaly["severity"] == "high" else DetectionSeverity.MEDIUM

                            finding = Finding(
                                finding_id=None,
                                title=f"Anomaly detected: {anomaly['type']}",
                                description=f"Query execution time anomaly detected (z-score: {result.get('z_score', 0):.2f})",
                                severity=severity,
                                category="ml_anomaly",
                                resource_type="metric",
                                resource_name="query_execution_time",
                                details=anomaly
                            )
                            finding.recommendation = "Investigate recent query changes or data volume increases"
                            self.add_finding(finding)

            except Exception as e:
                logger.debug(f"Could not detect current anomalies: {str(e)}")

        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")

    def predict_failures(self) -> None:
        """Predict potential failures using ML models."""
        logger.info("Predicting potential failures...")

        try:
            # Get recent error history
            sql = """
            SELECT
                warehouse_name,
                COUNT(*) as total_queries,
                SUM(CASE WHEN execution_status = 'FAIL' THEN 1 ELSE 0 END) as failed_queries
            FROM snowflake.account_usage.query_history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '24 hours'
            GROUP BY warehouse_name
            """

            try:
                results = self.snowpark_client.execute_query(sql)
                for row in results:
                    warehouse = row.get('warehouse_name')
                    total = row.get('total_queries', 1) or 1
                    failed = row.get('failed_queries', 0) or 0
                    error_rate = (failed / total)

                    self.anomaly_model.add_metric(f"error_rate_{warehouse}", error_rate * 100)

                    # Predict next value
                    forecast = self.anomaly_model.forecast(f"error_rate_{warehouse}", periods=3)

                    if forecast.get("status") == "success":
                        forecasted_rates = forecast.get("forecasts", [])
                        if forecasted_rates and max(forecasted_rates) > 10:  # >10% predicted error rate
                            failure_probability = min(max(forecasted_rates) / 100, 1.0)

                            if failure_probability > self.failure_prediction_threshold:
                                finding = Finding(
                                    finding_id=None,
                                    title=f"Failure prediction: {warehouse}",
                                    description=f"ML model predicts {failure_probability*100:.0f}% probability of warehouse failure",
                                    severity=DetectionSeverity.CRITICAL,
                                    category="ml_prediction",
                                    resource_type="warehouse",
                                    resource_name=warehouse,
                                    details={
                                        "failure_probability": failure_probability,
                                        "current_error_rate": error_rate,
                                        "forecasted_error_rates": forecasted_rates
                                    }
                                )
                                finding.recommendation = "Proactively restart warehouse or scale up"
                                self.add_finding(finding)

            except Exception as e:
                logger.debug(f"Could not predict failures: {str(e)}")

        except Exception as e:
            logger.error(f"Failure prediction failed: {str(e)}")

    def generate_ml_recommendations(self) -> None:
        """Generate recommendations based on ML analysis."""
        logger.info(f"Generating ML recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "ml_anomaly":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Investigate anomaly: {finding.resource_name}",
                    description="ML detected statistical anomaly in metric",
                    action_type="investigate",
                    resource_type="metric",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step("Review metric history in monitoring system")
                rec.add_step("Check for configuration changes")
                rec.add_step("Compare with baseline patterns")
                rec.add_step("Verify data quality")
                self.add_recommendation(rec)

            elif finding.category == "ml_prediction":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Prevent predicted failure: {finding.resource_name}",
                    description="ML model predicts high probability of failure",
                    action_type="proactive_maintenance",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="critical"
                )
                rec.add_step("Scale up warehouse preemptively")
                rec.add_step("Or restart warehouse for fresh state")
                rec.add_step("Monitor closely over next 4 hours")
                rec.add_step("Review recent query patterns")
                self.add_recommendation(rec)

    def get_summary(self) -> Dict[str, Any]:
        """Get ML agent summary."""
        return {
            "metrics_tracked": len(self.anomaly_model.analyzers),
            "anomalies_detected": len([f for f in self.current_findings if f.category == "ml_anomaly"]),
            "failure_predictions": len([f for f in self.current_findings if f.category == "ml_prediction"]),
            "model_status": "operational"
        }
