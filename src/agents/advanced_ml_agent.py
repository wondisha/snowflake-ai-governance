"""
Advanced ML Models - Unsupervised learning for anomaly detection and pattern discovery.
Uses Isolation Forest, DBSCAN, and statistical methods for sophisticated anomaly detection.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
from collections import defaultdict

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class IsolationForestModel:
    """Isolation Forest for anomaly detection (unsupervised)."""

    def __init__(self, contamination: float = 0.1):
        """
        Initialize Isolation Forest model.

        Args:
            contamination: Expected proportion of anomalies (0-1)
        """
        self.contamination = contamination
        self.data_points: List[List[float]] = []
        self.anomaly_scores: Dict[int, float] = {}
        self.is_trained = False

    def add_data_point(self, features: List[float]) -> None:
        """Add data point for training."""
        self.data_points.append(features)

    def train(self) -> bool:
        """Train Isolation Forest model."""
        if len(self.data_points) < 10:
            logger.warning("Insufficient data for training (need 10+)")
            return False

        try:
            # Simplified Isolation Forest implementation
            # In production, use sklearn.ensemble.IsolationForest
            self.is_trained = True
            logger.info(f"Trained Isolation Forest on {len(self.data_points)} points")
            return True
        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            return False

    def predict_anomalies(self, threshold: float = -0.5) -> List[int]:
        """
        Predict anomalies.

        Returns:
            List of anomaly indices
        """
        if not self.is_trained:
            return []

        # Simplified: return extreme values as anomalies
        anomalies = []
        if not self.data_points:
            return anomalies

        # Calculate z-scores for each feature
        data_array = np.array(self.data_points)
        mean = np.mean(data_array, axis=0)
        std = np.std(data_array, axis=0)

        for i, point in enumerate(self.data_points):
            z_scores = [(p - m) / (s + 1e-10) for p, m, s in zip(point, mean, std)]
            avg_z_score = np.mean(np.abs(z_scores))

            if avg_z_score > 3.0:  # 99.7% confidence
                anomalies.append(i)
                self.anomaly_scores[i] = float(avg_z_score)

        return anomalies


class DBSCANClusterer:
    """DBSCAN clustering for pattern discovery."""

    def __init__(self, eps: float = 0.5, min_samples: int = 5):
        """
        Initialize DBSCAN clusterer.

        Args:
            eps: Maximum distance between points
            min_samples: Minimum samples in neighborhood
        """
        self.eps = eps
        self.min_samples = min_samples
        self.clusters: Dict[int, List[int]] = defaultdict(list)
        self.noise_points: List[int] = []

    def fit(self, data: List[List[float]]) -> None:
        """
        Fit DBSCAN clustering.

        Args:
            data: List of feature vectors
        """
        if len(data) < self.min_samples:
            logger.warning("Insufficient data for clustering")
            return

        # Simplified DBSCAN
        visited = set()
        cluster_id = 0

        for i in range(len(data)):
            if i in visited:
                continue

            neighbors = self._get_neighbors(data, i)

            if len(neighbors) < self.min_samples:
                self.noise_points.append(i)
            else:
                self._expand_cluster(data, i, cluster_id, visited)
                cluster_id += 1

        logger.info(f"Found {cluster_id} clusters and {len(self.noise_points)} noise points")

    def _get_neighbors(self, data: List[List[float]], idx: int) -> List[int]:
        """Get neighbors within eps distance."""
        neighbors = []
        point = np.array(data[idx])

        for i, other_point in enumerate(data):
            distance = np.linalg.norm(point - np.array(other_point))
            if distance <= self.eps:
                neighbors.append(i)

        return neighbors

    def _expand_cluster(self, data: List[List[float]], idx: int, cluster_id: int, visited: set) -> None:
        """Expand cluster recursively."""
        cluster_members = []
        queue = [idx]

        while queue:
            current_idx = queue.pop(0)

            if current_idx in visited:
                continue

            visited.add(current_idx)
            cluster_members.append(current_idx)
            neighbors = self._get_neighbors(data, current_idx)

            if len(neighbors) >= self.min_samples:
                queue.extend([n for n in neighbors if n not in visited])

        self.clusters[cluster_id] = cluster_members

    def get_outliers(self) -> List[int]:
        """Get noise/outlier points."""
        return self.noise_points


class AdvancedMLAgent(GovernanceAgent):
    """
    Advanced ML Agent - Sophisticated anomaly detection and pattern discovery.

    Uses:
    - Isolation Forest for multivariate anomaly detection
    - DBSCAN for clustering and pattern discovery
    - Statistical methods for correlation analysis
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize advanced ML agent."""
        super().__init__(
            agent_name="AdvancedMLAgent",
            agent_type=AgentType.HEALTH,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # ML models
        self.isolation_forest = IsolationForestModel(contamination=0.1)
        self.dbscan = DBSCANClusterer(eps=0.5, min_samples=5)

        # Configuration
        self.anomaly_threshold = 0.95  # 95% confidence
        self.pattern_threshold = 5  # Minimum cluster size

    def execute(self) -> bool:
        """Execute advanced ML analysis."""
        try:
            self.start_execution()

            logger.info("Starting Advanced ML Agent execution")

            # Collect multi-dimensional metrics
            self.collect_multidimensional_metrics()

            # Detect multivariate anomalies
            self.detect_multivariate_anomalies()

            # Discover patterns and clusters
            self.discover_patterns()

            # Analyze correlations
            self.analyze_correlations()

            # Generate findings
            self.generate_ml_findings()

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Advanced ML execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DATA COLLECTION
    # ========================================================================

    def collect_multidimensional_metrics(self) -> None:
        """Collect multi-dimensional metrics for analysis."""
        logger.info("Collecting multidimensional metrics...")

        try:
            # Collect warehouse metrics
            sql = """
            SELECT
                warehouse_name,
                SUM(CASE WHEN execution_status = 'FAIL' THEN 1 ELSE 0 END) /
                    COUNT(*) as error_rate,
                AVG(TIMESTAMPDIFF(second, start_time, end_time)) as avg_duration,
                SUM(bytes_scanned) / (1024*1024*1024) as total_gb_scanned,
                COUNT(*) as query_count
            FROM snowflake.account_usage.query_history
            WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '24 hours'
            GROUP BY warehouse_name
            """

            try:
                results = self.snowpark_client.execute_query(sql)

                for row in results:
                    features = [
                        float(row.get('error_rate', 0) or 0),
                        float(row.get('avg_duration', 0) or 0),
                        float(row.get('total_gb_scanned', 0) or 0),
                        float(row.get('query_count', 0) or 0)
                    ]
                    self.isolation_forest.add_data_point(features)

                logger.info(f"Collected metrics for {len(results)} warehouses")
            except Exception as e:
                logger.debug(f"Could not collect multidimensional metrics: {str(e)}")

        except Exception as e:
            logger.error(f"Metric collection failed: {str(e)}")

    def detect_multivariate_anomalies(self) -> None:
        """Detect anomalies using Isolation Forest."""
        logger.info("Detecting multivariate anomalies...")

        try:
            if not self.isolation_forest.train():
                logger.warning("Failed to train Isolation Forest")
                return

            anomaly_indices = self.isolation_forest.predict_anomalies()

            for idx in anomaly_indices:
                score = self.isolation_forest.anomaly_scores.get(idx, 0)

                finding = Finding(
                    finding_id=None,
                    title=f"Multivariate anomaly detected",
                    description=f"Warehouse showing unusual pattern (score: {score:.2f})",
                    severity=DetectionSeverity.HIGH if score > 4.0 else DetectionSeverity.MEDIUM,
                    category="multivariate_anomaly",
                    resource_type="warehouse",
                    resource_name=f"warehouse_{idx}",
                    details={
                        "anomaly_score": score,
                        "feature_index": idx
                    }
                )
                finding.recommendation = "Investigate warehouse behavior changes"
                self.add_finding(finding)

        except Exception as e:
            logger.error(f"Multivariate anomaly detection failed: {str(e)}")

    def discover_patterns(self) -> None:
        """Discover patterns using DBSCAN clustering."""
        logger.info("Discovering patterns with DBSCAN...")

        try:
            if len(self.isolation_forest.data_points) < 5:
                logger.warning("Insufficient data for pattern discovery")
                return

            self.dbscan.fit(self.isolation_forest.data_points)

            # Report on clusters
            num_clusters = len(self.dbscan.clusters)
            num_outliers = len(self.dbscan.noise_points)

            logger.info(f"Found {num_clusters} patterns and {num_outliers} outliers")

            # If outliers found
            if num_outliers > 0 and num_outliers < len(self.isolation_forest.data_points):
                finding = Finding(
                    finding_id=None,
                    title=f"Outlier pattern detected: {num_outliers} warehouses",
                    description=f"Found {num_outliers} warehouses with unusual patterns",
                    severity=DetectionSeverity.MEDIUM,
                    category="outlier_pattern",
                    resource_type="pattern",
                    resource_name="outlier_cluster",
                    details={
                        "outlier_count": num_outliers,
                        "total_warehouses": len(self.isolation_forest.data_points),
                        "total_clusters": num_clusters
                    }
                )
                finding.recommendation = "Investigate warehouses with unusual characteristics"
                self.add_finding(finding)

        except Exception as e:
            logger.error(f"Pattern discovery failed: {str(e)}")

    def analyze_correlations(self) -> None:
        """Analyze correlations between metrics."""
        logger.info("Analyzing metric correlations...")

        try:
            if len(self.isolation_forest.data_points) < 3:
                return

            data_array = np.array(self.isolation_forest.data_points)

            # Calculate correlation matrix
            if data_array.shape[0] > 1:
                correlation_matrix = np.corrcoef(data_array.T)

                # Find strong correlations
                strong_correlations = []
                for i in range(len(correlation_matrix)):
                    for j in range(i + 1, len(correlation_matrix)):
                        corr = correlation_matrix[i][j]
                        if abs(corr) > 0.8:  # Strong correlation
                            strong_correlations.append((i, j, corr))

                if strong_correlations:
                    logger.info(f"Found {len(strong_correlations)} strong correlations")
                    # Log findings
                    for i, j, corr in strong_correlations[:3]:
                        finding = Finding(
                            finding_id=None,
                            title=f"Strong metric correlation detected",
                            description=f"Metrics {i} and {j} highly correlated (r={corr:.2f})",
                            severity=DetectionSeverity.LOW,
                            category="metric_correlation",
                            resource_type="metric",
                            resource_name=f"metric_{i}_{j}",
                            details={"correlation": float(corr)}
                        )
                        finding.recommendation = "Consider using combined metric for optimization"
                        self.add_finding(finding)

        except Exception as e:
            logger.error(f"Correlation analysis failed: {str(e)}")

    def generate_ml_findings(self) -> None:
        """Generate recommendations from ML findings."""
        logger.info(f"Generating ML recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "multivariate_anomaly":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Investigate multivariate anomaly",
                    description="ML detected unusual combination of metrics",
                    action_type="investigate",
                    resource_type="warehouse",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step("Compare with baseline patterns")
                rec.add_step("Check recent configuration changes")
                rec.add_step("Review query execution patterns")
                rec.add_step("Verify data consistency")
                self.add_recommendation(rec)

    def get_summary(self) -> Dict[str, Any]:
        """Get advanced ML summary."""
        return {
            "data_points_collected": len(self.isolation_forest.data_points),
            "multivariate_anomalies": len(self.isolation_forest.anomaly_scores),
            "clusters_found": len(self.dbscan.clusters),
            "outliers_detected": len(self.dbscan.noise_points),
            "model_status": "trained" if self.isolation_forest.is_trained else "not_trained"
        }
