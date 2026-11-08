"""
Data Spillage Prevention Agent - Detects and prevents PII and sensitive data exposure.
Monitors data movement and enforces masking policies.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import re

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class DataSpillagePrevention Agent(GovernanceAgent):
    """
    Data Spillage Prevention Agent - Detects and prevents sensitive data exposure.

    Responsibilities:
    - Scan tables for PII patterns
    - Monitor data access and exports
    - Enforce masking policies
    - Track sensitive data lineage
    - Alert on unauthorized access
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize Data Spillage Prevention Agent."""
        super().__init__(
            agent_name="DataSpillagePrevention Agent",
            agent_type=AgentType.SPILLAGE,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # PII detection patterns
        self.pii_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$',
            'ssn': r'^[0-9]{3}-[0-9]{2}-[0-9]{4}$',
            'credit_card': r'^[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}$',
            'ipv4': r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$',
        }

    def execute(self) -> bool:
        """Execute data spillage prevention checks."""
        try:
            self.start_execution()

            logger.info("Starting Data Spillage Prevention Agent execution")

            # Run detection methods
            self.scan_tables_for_pii()
            self.detect_unauthorized_exports()
            self.detect_sensitive_data_access()
            self.check_masking_policies()

            # Generate recommendations
            self.generate_recommendations()

            # Process critical findings
            critical_findings = self.get_critical_findings()
            if critical_findings:
                logger.warning(f"Found {len(critical_findings)} critical data spillage risks")
                self._escalate_critical_findings(critical_findings)

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Data spillage agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DETECTION METHODS
    # ========================================================================

    def scan_tables_for_pii(self) -> None:
        """Scan tables for PII patterns."""
        logger.info("Scanning tables for PII...")

        try:
            # Get all tables from information schema
            sql = """
            SELECT table_catalog, table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema != 'INFORMATION_SCHEMA'
            ORDER BY table_catalog, table_schema, table_name
            """
            tables = self.snowpark_client.execute_query(sql)

            logger.info(f"Scanning {len(tables)} tables for PII patterns")

            scanned_count = 0
            for table in tables[:100]:  # Limit for performance
                database = table.get('table_catalog')
                schema = table.get('table_schema')
                table_name = table.get('table_name')

                # Get table schema
                columns = self.snowpark_client.get_table_schema(database, schema, table_name)

                for column in columns:
                    col_name = column.get('column_name').lower()
                    col_type = column.get('data_type')

                    # Check column name against common PII patterns
                    pii_type = self._classify_column_by_name(col_name)

                    if pii_type:
                        finding = Finding(
                            finding_id=None,
                            title=f"Potential PII column: {col_name}",
                            description=f"Column {col_name} in {database}.{schema}.{table_name} appears to contain {pii_type}",
                            severity=DetectionSeverity.HIGH,
                            category="pii_detected",
                            resource_type="column",
                            resource_name=f"{database}.{schema}.{table_name}.{col_name}",
                            details={
                                "database": database,
                                "schema": schema,
                                "table": table_name,
                                "column": col_name,
                                "column_type": col_type,
                                "pii_type": pii_type
                            }
                        )
                        finding.recommendation = f"Apply masking policy to {col_name}"
                        self.add_finding(finding)

                scanned_count += 1

            logger.info(f"PII scan complete: scanned {scanned_count} tables")

        except Exception as e:
            logger.error(f"PII scan failed: {str(e)}")

    def detect_unauthorized_exports(self) -> None:
        """Detect attempts to export sensitive data."""
        logger.info("Detecting unauthorized data exports...")

        try:
            # Check query history for UNLOAD commands with potential PII
            sql = """
            SELECT
                query_id,
                query_text,
                user_name,
                start_time,
                database_name
            FROM snowflake.account_usage.query_history
            WHERE query_text LIKE '%UNLOAD%'
                AND start_time >= CURRENT_TIMESTAMP() - INTERVAL '24 hours'
            ORDER BY start_time DESC
            """
            exports = self.snowpark_client.execute_query(sql)

            for export in exports:
                query_text = export.get('query_text', '')
                user_name = export.get('user_name')
                database = export.get('database_name')

                # Check if exporting from sensitive database
                if any(sensitive in database.lower() for sensitive in ['customer', 'personal', 'sensitive', 'pii']):
                    finding = Finding(
                        finding_id=None,
                        title=f"Sensitive data export by {user_name}",
                        description=f"User {user_name} exported data from sensitive database {database}",
                        severity=DetectionSeverity.CRITICAL,
                        category="unauthorized_export",
                        resource_type="query",
                        resource_name=export.get('query_id'),
                        details={
                            "user": user_name,
                            "database": database,
                            "query_time": export.get('start_time')
                        }
                    )
                    finding.recommendation = f"Audit export by {user_name} and verify legitimate business purpose"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Export detection failed: {str(e)}")

    def detect_sensitive_data_access(self) -> None:
        """Detect unusual access patterns to sensitive tables."""
        logger.info("Detecting suspicious data access patterns...")

        try:
            # Check for users accessing sensitive tables outside normal patterns
            sql = """
            SELECT
                user_name,
                database_name,
                COUNT(*) as query_count,
                MAX(start_time) as last_access
            FROM snowflake.account_usage.query_history
            WHERE (database_name LIKE '%CUSTOMER%' OR database_name LIKE '%SENSITIVE%')
                AND start_time >= CURRENT_TIMESTAMP() - INTERVAL '24 hours'
            GROUP BY user_name, database_name
            ORDER BY query_count DESC
            """
            access_logs = self.snowpark_client.execute_query(sql)

            for access in access_logs:
                user = access.get('user_name')
                db = access.get('database_name')
                count = access.get('query_count', 0)

                # Flag unusual access patterns
                if count > 100:
                    finding = Finding(
                        finding_id=None,
                        title=f"Bulk access to sensitive data: {db}",
                        description=f"User {user} accessed {db} {count} times in 24 hours",
                        severity=DetectionSeverity.HIGH,
                        category="bulk_access",
                        resource_type="database",
                        resource_name=db,
                        details={
                            "user": user,
                            "access_count": count,
                            "last_access": access.get('last_access')
                        }
                    )
                    finding.recommendation = f"Audit bulk access by {user} to sensitive database"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Access detection failed: {str(e)}")

    def check_masking_policies(self) -> None:
        """Verify masking policies are applied to PII columns."""
        logger.info("Checking masking policies...")

        try:
            # Get columns detected as PII but check if masking is applied
            sql = """
            SELECT *
            FROM governance.pii_detections
            WHERE status = 'detected'
                AND masked_at IS NULL
            ORDER BY detected_at DESC
            LIMIT 50
            """
            unmasked_pii = self.snowpark_client.execute_query(sql)

            for pii in unmasked_pii:
                col_name = pii.get('column_name')
                table_name = pii.get('table_name')
                pii_type = pii.get('pii_type')

                finding = Finding(
                    finding_id=None,
                    title=f"Unmasked PII: {col_name}",
                    description=f"Column {col_name} contains {pii_type} but masking policy is not applied",
                    severity=DetectionSeverity.CRITICAL,
                    category="unmasked_pii",
                    resource_type="column",
                    resource_name=f"{table_name}.{col_name}",
                    details={
                        "table": table_name,
                        "column": col_name,
                        "pii_type": pii_type,
                        "detected_at": pii.get('detected_at')
                    }
                )
                finding.recommendation = f"Apply masking policy to {col_name} immediately"
                self.add_finding(finding)

        except Exception as e:
            logger.error(f"Masking policy check failed: {str(e)}")

    # ========================================================================
    # ANALYSIS METHODS
    # ========================================================================

    def _classify_column_by_name(self, column_name: str) -> str:
        """Classify column as PII based on naming conventions."""
        col_lower = column_name.lower()

        pii_keywords = {
            'email': ['email', 'email_address', 'mail'],
            'phone': ['phone', 'telephone', 'mobile'],
            'ssn': ['ssn', 'social_security', 'tax_id'],
            'credit_card': ['cc_number', 'card_number', 'credit_card'],
            'name': ['customer_name', 'person_name', 'full_name'],
            'address': ['street_address', 'home_address', 'mailing_address']
        }

        for pii_type, keywords in pii_keywords.items():
            if any(keyword in col_lower for keyword in keywords):
                return pii_type

        return None

    def generate_recommendations(self) -> None:
        """Generate data protection recommendations."""
        logger.info(f"Generating recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "pii_detected":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Apply masking to: {finding.resource_name}",
                    description=f"Apply Snowflake dynamic masking policy to {finding.resource_name}",
                    action_type="apply_masking",
                    resource_type="column",
                    resource_name=finding.resource_name,
                    impact="high"
                )
                rec.add_step("Verify {finding.resource_name} contains sensitive data")
                rec.add_step("Define masking policy (partial mask, encryption, etc.)")
                rec.add_step("Apply masking policy to column")
                rec.add_step("Test masking with different user roles")
                self.add_recommendation(rec)

            elif finding.category == "unmasked_pii":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Urgent: Mask unprotected PII: {finding.resource_name}",
                    description=f"Apply masking immediately to {finding.resource_name}",
                    action_type="apply_masking_urgent",
                    resource_type="column",
                    resource_name=finding.resource_name,
                    impact="critical"
                )
                rec.add_step(f"Apply masking policy to {finding.resource_name} ASAP")
                rec.add_step("Verify masking is effective")
                rec.add_step("Audit who has accessed unmasked data")
                self.add_recommendation(rec)

    def _escalate_critical_findings(self, critical_findings: List[Finding]) -> None:
        """Escalate critical data spillage findings."""
        for finding in critical_findings:
            logger.warning(f"Escalating critical finding: {finding.title}")

            approver_email = "security-admin@company.com"
            self.request_approval(
                request_type="critical_data_spillage",
                title=f"CRITICAL: Data Spillage Risk - {finding.title}",
                description=finding.description,
                context=finding.to_dict(),
                approver_email=approver_email,
                priority="critical",
                sla_hours=1  # 1-hour SLA for data spillage
            )

            self.log_audit_event(
                event_type="critical_data_spillage_detected",
                resource_type=finding.resource_type,
                resource_name=finding.resource_name,
                description=finding.description,
                status="pending"
            )
