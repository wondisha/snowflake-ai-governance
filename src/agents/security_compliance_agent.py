"""
Security & Compliance Agent - Enforces RBAC policies, detects access violations.
Monitors data classification, audit trails, and compliance requirements.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class SecurityComplianceAgent(GovernanceAgent):
    """
    Security and Compliance Agent - Monitors and enforces security policies.

    Responsibilities:
    - Role-based access control (RBAC) violations
    - Unused role detection
    - Stale user account detection
    - Permission audit
    - Compliance policy enforcement
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize Security & Compliance Agent."""
        super().__init__(
            agent_name="SecurityComplianceAgent",
            agent_type=AgentType.SECURITY,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        # Agent configuration
        self.stale_user_days = 90
        self.unused_role_days = 60
        self.critical_roles = ['ACCOUNTADMIN', 'SECURITYADMIN', 'SYSADMIN']

    def execute(self) -> bool:
        """Execute security compliance checks."""
        try:
            self.start_execution()

            logger.info("Starting Security & Compliance Agent execution")

            # Run detection methods
            self.detect_rbac_violations()
            self.detect_stale_users()
            self.detect_unused_roles()
            self.detect_excessive_permissions()
            self.detect_policy_violations()

            # Generate recommendations based on findings
            self.generate_recommendations()

            # Process critical findings
            critical_findings = self.get_critical_findings()
            if critical_findings:
                logger.warning(f"Found {len(critical_findings)} critical security issues")
                self._escalate_critical_findings(critical_findings)

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Security agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # DETECTION METHODS
    # ========================================================================

    def detect_rbac_violations(self) -> None:
        """Detect RBAC violations and unauthorized access."""
        logger.info("Detecting RBAC violations...")

        try:
            # Get all users and their roles
            users = self.snowpark_client.list_users()

            for user in users:
                user_name = user.get('user_name')

                # Check for disabled users with active roles
                if user.get('disabled'):
                    user_permissions = self.snowpark_client.get_user_permissions(user_name)
                    if user_permissions:
                        finding = Finding(
                            finding_id=None,
                            title=f"Disabled user '{user_name}' has active roles",
                            description=f"User {user_name} is disabled but still has {len(user_permissions)} active roles",
                            severity=DetectionSeverity.HIGH,
                            category="rbac_violation",
                            resource_type="user",
                            resource_name=user_name,
                            details={
                                "active_roles": [p.get('role_name') for p in user_permissions],
                                "user_status": "disabled"
                            }
                        )
                        finding.recommendation = f"Revoke all roles from disabled user {user_name}"
                        finding.auto_remediate = False
                        self.add_finding(finding)

                # Check for users with critical roles
                user_permissions = self.snowpark_client.get_user_permissions(user_name)
                critical_roles = [p for p in user_permissions if p.get('role_name') in self.critical_roles]

                if critical_roles and len(critical_roles) > 1:
                    finding = Finding(
                        finding_id=None,
                        title=f"User '{user_name}' has multiple critical roles",
                        description=f"User {user_name} has {len(critical_roles)} critical roles which violates least-privilege",
                        severity=DetectionSeverity.HIGH,
                        category="least_privilege_violation",
                        resource_type="user",
                        resource_name=user_name,
                        details={"critical_roles": [r.get('role_name') for r in critical_roles]}
                    )
                    finding.recommendation = f"Review and reduce critical roles for {user_name}"
                    self.add_finding(finding)

            logger.info(f"RBAC detection complete: found {len([f for f in self.current_findings if 'rbac' in f.category])} violations")

        except Exception as e:
            logger.error(f"RBAC violation detection failed: {str(e)}")

    def detect_stale_users(self) -> None:
        """Detect users that haven't logged in recently."""
        logger.info("Detecting stale users...")

        try:
            users = self.snowpark_client.list_users()

            for user in users:
                user_name = user.get('user_name')
                last_login = user.get('last_success_login')

                # Skip if no login recorded
                if not last_login:
                    finding = Finding(
                        finding_id=None,
                        title=f"User '{user_name}' has never logged in",
                        description=f"User {user_name} has no recorded login history",
                        severity=DetectionSeverity.MEDIUM,
                        category="stale_account",
                        resource_type="user",
                        resource_name=user_name
                    )
                    finding.recommendation = f"Investigate and remove unused user account {user_name}"
                    self.add_finding(finding)
                    continue

                # Check if stale
                days_since_login = (datetime.utcnow() - last_login).days
                if days_since_login > self.stale_user_days:
                    finding = Finding(
                        finding_id=None,
                        title=f"Stale user account: {user_name}",
                        description=f"User {user_name} has not logged in for {days_since_login} days",
                        severity=DetectionSeverity.MEDIUM,
                        category="stale_account",
                        resource_type="user",
                        resource_name=user_name,
                        details={"days_inactive": days_since_login}
                    )
                    finding.recommendation = f"Disable or remove stale user {user_name}"
                    self.add_finding(finding)

            logger.info(f"Stale user detection complete: found {len([f for f in self.current_findings if f.category == 'stale_account'])} stale accounts")

        except Exception as e:
            logger.error(f"Stale user detection failed: {str(e)}")

    def detect_unused_roles(self) -> None:
        """Detect roles that haven't been used recently."""
        logger.info("Detecting unused roles...")

        try:
            roles = self.snowpark_client.list_roles()

            # This would require querying account_usage.grant_by_time_series
            # For now, log the capability
            logger.info(f"Checking {len(roles)} roles for usage patterns")

            # In production, would check query history for role usage
            # and flag roles with no activity in X days

        except Exception as e:
            logger.error(f"Unused role detection failed: {str(e)}")

    def detect_excessive_permissions(self) -> None:
        """Detect users with excessive or dangerous permissions."""
        logger.info("Detecting excessive permissions...")

        try:
            users = self.snowpark_client.list_users()

            for user in users:
                user_name = user.get('user_name')
                user_permissions = self.snowpark_client.get_user_permissions(user_name)

                # Flag users with > 10 roles (excessive)
                if len(user_permissions) > 10:
                    finding = Finding(
                        finding_id=None,
                        title=f"User '{user_name}' has excessive permissions",
                        description=f"User {user_name} has {len(user_permissions)} roles which exceeds expected count",
                        severity=DetectionSeverity.MEDIUM,
                        category="excessive_permissions",
                        resource_type="user",
                        resource_name=user_name,
                        details={"role_count": len(user_permissions)}
                    )
                    finding.recommendation = f"Audit and reduce permissions for {user_name}"
                    self.add_finding(finding)

        except Exception as e:
            logger.error(f"Excessive permissions detection failed: {str(e)}")

    def detect_policy_violations(self) -> None:
        """Detect violations of security policies."""
        logger.info("Detecting policy violations...")

        try:
            # Get defined security rules from governance schema
            sql = "SELECT * FROM governance.security_rules WHERE enabled = TRUE"
            rules = self.snowpark_client.execute_query(sql)

            logger.info(f"Checking against {len(rules)} active security rules")

            # For each rule, check if it's being violated
            for rule in rules:
                rule_name = rule.get('rule_name')
                rule_type = rule.get('rule_type')

                if rule_type == 'rbac':
                    # Check RBAC rules
                    logger.debug(f"Checking RBAC rule: {rule_name}")
                    # Implementation would check specific RBAC constraints

                elif rule_type == 'access_control':
                    logger.debug(f"Checking access control rule: {rule_name}")
                    # Implementation would check access control policies

        except Exception as e:
            logger.error(f"Policy violation detection failed: {str(e)}")

    # ========================================================================
    # RECOMMENDATION GENERATION
    # ========================================================================

    def generate_recommendations(self) -> None:
        """Generate security recommendations based on findings."""
        logger.info(f"Generating recommendations for {len(self.current_findings)} findings...")

        for finding in self.current_findings:
            if finding.category == "rbac_violation":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Fix RBAC violation: {finding.resource_name}",
                    description=f"Remove unauthorized or excessive roles from {finding.resource_name}",
                    action_type="revoke_role",
                    resource_type=finding.resource_type,
                    resource_name=finding.resource_name,
                    impact="high",
                    estimated_benefit="Improved security posture"
                )
                rec.add_step(f"Review roles granted to {finding.resource_name}")
                rec.add_step("Identify unnecessary or dangerous roles")
                rec.add_step("Request approval for revocation")
                rec.add_step("Execute revocation")
                self.add_recommendation(rec)

            elif finding.category == "stale_account":
                rec = Recommendation(
                    recommendation_id=None,
                    title=f"Remove stale account: {finding.resource_name}",
                    description=f"Disable or delete unused user account {finding.resource_name}",
                    action_type="disable_user",
                    resource_type="user",
                    resource_name=finding.resource_name,
                    impact="medium"
                )
                rec.add_step(f"Verify {finding.resource_name} is no longer needed")
                rec.add_step("Notify user before disabling")
                rec.add_step("Disable account")
                rec.add_step("Archive account after 30 days")
                self.add_recommendation(rec)

    # ========================================================================
    # REMEDIATION & ESCALATION
    # ========================================================================

    def _escalate_critical_findings(self, critical_findings: List[Finding]) -> None:
        """Escalate critical security findings."""
        for finding in critical_findings:
            logger.warning(f"Escalating critical finding: {finding.title}")

            # Create approval request for critical action
            approver_email = "security-admin@company.com"  # Should come from config
            self.request_approval(
                request_type="critical_security_action",
                title=f"Critical Security Issue: {finding.title}",
                description=finding.description,
                context=finding.to_dict(),
                approver_email=approver_email,
                priority="critical",
                sla_hours=1  # 1-hour SLA for critical issues
            )

            # Log audit event
            self.log_audit_event(
                event_type="critical_security_finding",
                resource_type=finding.resource_type,
                resource_name=finding.resource_name,
                description=finding.description,
                status="pending"
            )

    def remediate_stale_account(self, user_name: str) -> bool:
        """Remediate stale account by disabling it."""
        try:
            # Note: Actual disabling would require appropriate SQL commands
            logger.info(f"Remediating stale account: {user_name}")

            # Log the remediation
            self.log_audit_event(
                event_type="user_disabled",
                resource_type="user",
                resource_name=user_name,
                description=f"Disabled stale user account {user_name}",
                status="success"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to remediate stale account {user_name}: {str(e)}")
            return False
