"""
Data Governance Agent - Manages data classification, lineage, and retention.
Ensures compliance with data governance policies and regulations.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import re

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class DataClassification:
    """Data classification metadata."""

    def __init__(self, database: str, schema: str, table: str, column: str = None):
        self.database = database
        self.schema = schema
        self.table = table
        self.column = column
        self.full_name = f"{database}.{schema}.{table}" + (f".{column}" if column else "")

        # Classification
        self.classification_level = None  # public, internal, confidential, restricted
        self.pii_type = None  # email, phone, ssn, etc.
        self.confidence_score = 0.0
        self.owner_email = None
        self.last_scanned = None

        # Retention
        self.retention_days = 90
        self.archive_enabled = False
        self.archive_location = None


class DataLineage:
    """Data lineage tracking."""

    def __init__(self, source_table: str, target_table: str):
        self.source_table = source_table
        self.target_table = target_table
        self.job_name = None
        self.last_updated = None
        self.update_frequency = None  # daily, weekly, real_time
        self.sla_hours = None


class DataGovernanceAgent(GovernanceAgent):
    """
    Data Governance Agent - Manages data governance policies.

    Responsibilities:
    - Classify data (PII, PHI, financial, public)
    - Track data lineage
    - Enforce retention policies
    - Archive old data
    - Verify compliance
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize Data Governance Agent."""
        super().__init__(
            agent_name="DataGovernanceAgent",
            agent_type=AgentType.SPILLAGE,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # Data governance tracking
        self.data_classifications: Dict[str, DataClassification] = {}
        self.data_lineage: Dict[str, DataLineage] = {}
        self.retention_policies: Dict[str, Dict[str, Any]] = {}

        # Configuration
        self.classification_levels = ["public", "internal", "confidential", "restricted"]
        self.pii_patterns = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "phone": r"^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$",
            "ssn": r"^[0-9]{3}-[0-9]{2}-[0-9]{4}$",
            "credit_card": r"^[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}$"
        }
        self.default_retention_days = 90

    def execute(self) -> bool:
        """Execute data governance checks."""
        try:
            self.start_execution()

            logger.info("Starting Data Governance Agent execution")

            # Classify data
            self.auto_classify_data()

            # Track data lineage
            self.track_data_lineage()

            # Check retention policies
            self.check_retention_policies()

            # Verify masking policies
            self.verify_masking_policies()

            # Check compliance
            self.check_compliance()

            # Generate recommendations
            self.generate_governance_recommendations()

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Data governance agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DATA CLASSIFICATION
    # ========================================================================

    def auto_classify_data(self) -> None:
        """Auto-classify data in all tables."""
        logger.info("Auto-classifying data...")

        try:
            # Get all tables
            sql = """
            SELECT table_catalog, table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('INFORMATION_SCHEMA', 'FIVETRAN_LOG')
            ORDER BY table_catalog, table_schema, table_name
            LIMIT 100
            """
            tables = self.snowpark_client.execute_query(sql)

            for table in tables:
                database = table.get('table_catalog')
                schema = table.get('table_schema')
                table_name = table.get('table_name')

                try:
                    # Get table schema
                    columns = self.snowpark_client.get_table_schema(database, schema, table_name)

                    for column in columns:
                        col_name = column.get('column_name')
                        col_type = column.get('data_type')

                        # Classify column
                        classification = self._classify_column(col_name, col_type, database, schema, table_name)

                        if classification:
                            self.data_classifications[classification.full_name] = classification

                            # Create finding for sensitive data
                            if classification.classification_level in ["confidential", "restricted"]:
                                finding = Finding(
                                    finding_id=None,
                                    title=f"Sensitive data classified: {classification.full_name}",
                                    description=f"Column contains {classification.classification_level} data",
                                    severity=DetectionSeverity.MEDIUM if classification.classification_level == "confidential" else DetectionSeverity.HIGH,
                                    category="data_classified",
                                    resource_type="column",
                                    resource_name=classification.full_name,
                                    details={
                                        "classification_level": classification.classification_level,
                                        "pii_type": classification.pii_type,
                                        "confidence": classification.confidence_score
                                    }
                                )
                                finding.recommendation = f"Verify classification and apply masking policy"
                                self.add_finding(finding)

                except Exception as e:
                    logger.debug(f"Could not classify table {database}.{schema}.{table_name}: {str(e)}")

        except Exception as e:
            logger.error(f"Data classification failed: {str(e)}")

    def _classify_column(
        self,
        column_name: str,
        column_type: str,
        database: str,
        schema: str,
        table_name: str
    ) -> Optional[DataClassification]:
        """Classify a column based on name and type."""
        col_lower = column_name.lower()

        # Check column naming patterns
        if any(sensitive in col_lower for sensitive in ["password", "secret", "token", "key", "auth"]):
            classification = DataClassification(database, schema, table_name, column_name)
            classification.classification_level = "restricted"
            classification.confidence_score = 0.95
            return classification

        if any(pii in col_lower for pii in ["email", "phone", "ssn", "social_security", "credit_card", "account_number"]):
            classification = DataClassification(database, schema, table_name, column_name)
            classification.classification_level = "confidential"

            # Determine PII type
            if "email" in col_lower:
                classification.pii_type = "email"
            elif "phone" in col_lower:
                classification.pii_type = "phone"
            elif "ssn" in col_lower or "social_security" in col_lower:
                classification.pii_type = "ssn"
            elif "credit" in col_lower or "card" in col_lower:
                classification.pii_type = "credit_card"

            classification.confidence_score = 0.85
            return classification

        if any(sensitive in col_lower for sensitive in ["customer", "personal", "medical", "health", "patient"]):
            classification = DataClassification(database, schema, table_name, column_name)
            classification.classification_level = "confidential"
            classification.confidence_score = 0.7
            return classification

        # Default classification for regular columns
        if not any(public in col_lower for public in ["id", "name", "count", "amount", "status"]):
            classification = DataClassification(database, schema, table_name, column_name)
            classification.classification_level = "internal"
            classification.confidence_score = 0.6
            return classification

        return None

    # ========================================================================
    # DATA LINEAGE
    # ========================================================================

    def track_data_lineage(self) -> None:
        """Track data lineage between tables."""
        logger.info("Tracking data lineage...")

        try:
            # Query task_lineage or job_history to understand data flow
            # This is a simplified version - production would need more comprehensive tracking

            sql = """
            SELECT DISTINCT
                qt1.database_name as source_db,
                qt1.schema_name as source_schema,
                qt1.table_name as source_table,
                qt2.database_name as target_db,
                qt2.schema_name as target_schema,
                qt2.table_name as target_table
            FROM snowflake.account_usage.query_history q1
            JOIN snowflake.account_usage.table_store_metrics qt1
                ON q1.database_name = qt1.database_name
            JOIN snowflake.account_usage.table_store_metrics qt2
                ON q1.database_name = qt2.database_name
            WHERE q1.start_time >= CURRENT_TIMESTAMP() - INTERVAL '7 days'
                AND q1.execution_status = 'SUCCESS'
            LIMIT 50
            """

            try:
                lineages = self.snowpark_client.execute_query(sql)
                logger.info(f"Found {len(lineages)} data flow relationships")
            except Exception as e:
                logger.debug(f"Could not query lineage: {str(e)}")

        except Exception as e:
            logger.error(f"Lineage tracking failed: {str(e)}")

    # ========================================================================
    # RETENTION POLICIES
    # ========================================================================

    def check_retention_policies(self) -> None:
        """Check data retention policies."""
        logger.info("Checking retention policies...")

        try:
            sql = """
            SELECT
                table_catalog,
                table_schema,
                table_name,
                DATEDIFF(day, CURRENT_DATE(), MAX(CURRENT_DATE())) as days_old
            FROM snowflake.account_usage.table_storage_metrics
            WHERE deleted = FALSE
            GROUP BY table_catalog, table_schema, table_name
            """

            try:
                tables = self.snowpark_client.execute_query(sql)

                for table in tables:
                    database = table.get('table_catalog')
                    schema = table.get('table_schema')
                    table_name = table.get('table_name')
                    days_old = table.get('days_old', 0) or 0

                    # Check if table exceeds retention period
                    if days_old > self.default_retention_days:
                        finding = Finding(
                            finding_id=None,
                            title=f"Data retention policy: {database}.{schema}.{table_name}",
                            description=f"Table is {days_old} days old, exceeds {self.default_retention_days}-day retention",
                            severity=DetectionSeverity.MEDIUM,
                            category="retention_violation",
                            resource_type="table",
                            resource_name=f"{database}.{schema}.{table_name}",
                            details={
                                "age_days": days_old,
                                "retention_days": self.default_retention_days
                            }
                        )
                        finding.recommendation = f"Archive or delete data older than {self.default_retention_days} days"
                        self.add_finding(finding)

            except Exception as e:
                logger.debug(f"Could not check retention: {str(e)}")

        except Exception as e:
            logger.error(f"Retention check failed: {str(e)}")

    # ========================================================================
    # COMPLIANCE VERIFICATION
    # ========================================================================

    def verify_masking_policies(self) -> None:
        """Verify that masking policies are applied to classified data."""
        logger.info("Verifying masking policies...")

        try:
            # Check for PII columns that don't have masking
            for col_name, classification in self.data_classifications.items():
                if classification.pii_type and classification.classification_level in ["confidential", "restricted"]:
                    # Check if masking is applied (would require Snowflake policy info)
                    finding = Finding(
                        finding_id=None,
                        title=f"Verify masking: {col_name}",
                        description=f"Column contains {classification.pii_type}, verify masking is applied",
                        severity=DetectionSeverity.HIGH,
                        category="masking_required",
                        resource_type="column",
                        resource_name=col_name,
                        details={
                            "pii_type": classification.pii_type,
                            "classification": classification.classification_level
                        }
                    )
                    finding.recommendation = "Apply Snowflake dynamic masking policy"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Masking verification failed: {str(e)}")

    def check_compliance(self) -> None:
        """Check data governance compliance."""
        logger.info("Checking compliance...")

        try:
            # Check for unclassified sensitive tables
            sql = """
            SELECT table_catalog, table_schema, table_name
            FROM information_schema.tables
            WHERE table_name LIKE '%CUSTOMER%'
                OR table_name LIKE '%PERSONAL%'
                OR table_name LIKE '%SENSITIVE%'
            LIMIT 20
            """

            try:
                sensitive_tables = self.snowpark_client.execute_query(sql)

                for table in sensitive_tables:
                    database = table.get('table_catalog')
                    schema = table.get('table_schema')
                    table_name = table.get('table_name')
                    full_name = f"{database}.{schema}.{table_name}"

                    # Check if classified
                    if not any(full_name in col_name for col_name in self.data_classifications.keys()):
                        finding = Finding(
                            finding_id=None,
                            title=f"Unclassified sensitive table: {full_name}",
                            description=f"Table name suggests sensitive data but is not classified",
                            severity=DetectionSeverity.MEDIUM,
                            category="unclassified_sensitive",
                            resource_type="table",
                            resource_name=full_name
                        )
                        finding.recommendation = "Review and classify all columns"
                        self.add_finding(finding)

            except Exception as e:
                logger.debug(f"Could not check compliance: {str(e)}")

        except Exception as e:
            logger.error(f"Compliance check failed: {str(e)}")

    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================

    def generate_governance_recommendations(self) -> None:
        """Generate data governance recommendations."""
        logger.info(f"Generating recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "data_classified":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Protect sensitive data: {finding.resource_name}",
                    description="Apply protective measures to sensitive data",
                    action_type="apply_masking",
                    resource_type="column",
                    resource_name=finding.resource_name,
                    impact="high"
                )
                rec.add_step(f"Review column {finding.resource_name}")
                rec.add_step("Determine who needs to see unmasked data")
                rec.add_step("Create masking policy in Snowflake")
                rec.add_step("Apply masking policy to column")
                self.add_recommendation(rec)

            elif finding.category == "retention_violation":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Archive old data: {finding.resource_name}",
                    description="Data exceeds retention policy",
                    action_type="archive_data",
                    resource_type="table",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step(f"Backup {finding.resource_name}")
                rec.add_step("Archive to S3/external storage")
                rec.add_step("Delete from Snowflake")
                rec.add_step("Document archival location")
                self.add_recommendation(rec)

            elif finding.category == "unclassified_sensitive":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Classify sensitive table: {finding.resource_name}",
                    description="Table contains sensitive data",
                    action_type="classify_data",
                    resource_type="table",
                    resource_name=finding.resource_name,
                    impact="high"
                )
                rec.add_step(f"Review all columns in {finding.resource_name}")
                rec.add_step("Assign classification level to each column")
                rec.add_step("Document PII types")
                rec.add_step("Apply masking policies")
                self.add_recommendation(rec)

    def get_summary(self) -> Dict[str, Any]:
        """Get data governance summary."""
        classified_cols = len(self.data_classifications)
        sensitive_cols = len([
            c for c in self.data_classifications.values()
            if c.classification_level in ["confidential", "restricted"]
        ])

        return {
            "total_classified_columns": classified_cols,
            "sensitive_columns": sensitive_cols,
            "data_lineage_tracked": len(self.data_lineage),
            "retention_policies": len(self.retention_policies),
            "compliance_violations": len([f for f in self.current_findings if "compliance" in f.category.lower()])
        }
