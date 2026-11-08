"""
Remediation & Incident Manager Agent - Executes approved actions and manages incidents.
Handles auto-remediation of violations, tracks progress, and manages incident lifecycle.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import uuid

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class IncidentSeverity:
    """Incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus:
    """Incident lifecycle status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    ESCALATED = "escalated"


class RemediationAction:
    """Represents a remediation action."""

    def __init__(
        self,
        action_type: str,
        target_resource: str,
        description: str,
        before_state: Dict[str, Any] = None,
        requires_approval: bool = True
    ):
        self.action_id = str(uuid.uuid4())
        self.action_type = action_type  # 'query_abort', 'warehouse_suspend', 'role_revoke', etc.
        self.target_resource = target_resource
        self.description = description
        self.before_state = before_state or {}
        self.after_state = {}
        self.requires_approval = requires_approval

        # Execution tracking
        self.status = "pending"  # pending, executing, success, failed, rolled_back
        self.approval_request_id = None
        self.executed_by = None
        self.execution_timestamp = None
        self.error_message = None
        self.rollback_timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_resource": self.target_resource,
            "description": self.description,
            "status": self.status,
            "requires_approval": self.requires_approval,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "execution_timestamp": self.execution_timestamp.isoformat() if self.execution_timestamp else None,
            "error_message": self.error_message
        }


class Incident:
    """Represents a governance incident."""

    def __init__(
        self,
        category: str,
        severity: str,
        description: str,
        resource_type: str,
        resource_name: str
    ):
        self.incident_id = str(uuid.uuid4())
        self.category = category  # 'performance', 'security', 'cost', 'health'
        self.severity = severity
        self.description = description
        self.resource_type = resource_type
        self.resource_name = resource_name

        # Lifecycle
        self.status = IncidentStatus.OPEN
        self.detected_timestamp = datetime.utcnow()
        self.resolved_timestamp = None
        self.assigned_to = None

        # Tracking
        self.related_findings = []  # Finding IDs
        self.related_actions = []  # Remediation action IDs
        self.escalation_count = 0
        self.escalation_timestamp = None
        self.resolution_notes = None

    def escalate(self) -> None:
        """Escalate the incident."""
        self.escalation_count += 1
        self.escalation_timestamp = datetime.utcnow()
        if self.escalation_count >= 2:
            self.status = IncidentStatus.ESCALATED

    def resolve(self, notes: str = "") -> None:
        """Resolve the incident."""
        self.status = IncidentStatus.RESOLVED
        self.resolved_timestamp = datetime.utcnow()
        self.resolution_notes = notes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "incident_id": self.incident_id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "status": self.status,
            "detected_timestamp": self.detected_timestamp.isoformat(),
            "resolved_timestamp": self.resolved_timestamp.isoformat() if self.resolved_timestamp else None,
            "assigned_to": self.assigned_to,
            "escalation_count": self.escalation_count,
            "related_actions": self.related_actions
        }


class RemediationAgent(GovernanceAgent):
    """
    Remediation & Incident Manager Agent - Executes approved actions.

    Responsibilities:
    - Execute remediation actions (after approval)
    - Manage incident lifecycle
    - Track remediation progress
    - Handle rollback if needed
    - Monitor action effectiveness
    """

    def __init__(self, snowpark_client, approval_manager=None, notification_manager=None):
        """Initialize Remediation Agent."""
        super().__init__(
            agent_name="RemediationAgent",
            agent_type=AgentType.HEALTH,  # Health domain (remediation)
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        self.approval_manager = approval_manager

        # Action tracking
        self.pending_actions: Dict[str, RemediationAction] = {}
        self.active_incidents: Dict[str, Incident] = {}
        self.completed_actions = []

        # Configuration
        self.auto_remediate_safe_actions = True  # Unsafe actions require approval
        self.safe_action_types = [
            'warehouse_suspend',
            'warehouse_auto_suspend_enable',
            'query_abort_timeout'
        ]
        self.rollback_enabled = True

    def execute(self) -> bool:
        """Execute remediation operations."""
        try:
            self.start_execution()

            logger.info("Starting Remediation Agent execution")

            # Process pending actions
            self.process_pending_actions()

            # Check incident status and manage escalation
            self.check_incident_status()

            # Resolve closed incidents
            self.resolve_closed_incidents()

            # Generate recommendations for failed remediations
            self.generate_remediation_recommendations()

            self.findings_processed = len(self.current_findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Remediation agent execution failed: {str(e)}")
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # ACTION EXECUTION
    # ========================================================================

    def create_remediation_action(
        self,
        action_type: str,
        target_resource: str,
        description: str,
        before_state: Dict[str, Any] = None,
        requires_approval: bool = True
    ) -> Optional[str]:
        """
        Create a remediation action.

        Args:
            action_type: Type of action (e.g., 'query_abort', 'warehouse_suspend')
            target_resource: Resource to remediate
            description: Action description
            before_state: Current state before remediation
            requires_approval: Whether action requires approval

        Returns:
            Action ID if successful
        """
        action = RemediationAction(
            action_type=action_type,
            target_resource=target_resource,
            description=description,
            before_state=before_state,
            requires_approval=requires_approval
        )

        self.pending_actions[action.action_id] = action
        logger.info(f"Created remediation action: {action.action_id} (type: {action_type})")

        # If action is safe and auto-remediate enabled, execute immediately
        if self.auto_remediate_safe_actions and action_type in self.safe_action_types and not requires_approval:
            self.execute_action(action.action_id)
        else:
            # Request approval for unsafe actions
            if requires_approval and self.approval_manager:
                self._request_action_approval(action)

        return action.action_id

    def execute_action(self, action_id: str) -> bool:
        """
        Execute a remediation action.

        Args:
            action_id: ID of action to execute

        Returns:
            True if successful
        """
        action = self.pending_actions.get(action_id)
        if not action:
            logger.error(f"Action not found: {action_id}")
            return False

        logger.info(f"Executing action: {action_id} (type: {action.action_type})")
        action.status = "executing"

        try:
            # Execute based on action type
            if action.action_type == "query_abort":
                success = self._abort_query(action)
            elif action.action_type == "warehouse_suspend":
                success = self._suspend_warehouse(action)
            elif action.action_type == "warehouse_resume":
                success = self._resume_warehouse(action)
            elif action.action_type == "role_revoke":
                success = self._revoke_role(action)
            elif action.action_type == "role_grant":
                success = self._grant_role(action)
            elif action.action_type == "warehouse_auto_suspend_enable":
                success = self._enable_auto_suspend(action)
            elif action.action_type == "warehouse_scale":
                success = self._scale_warehouse(action)
            else:
                logger.error(f"Unknown action type: {action.action_type}")
                success = False

            if success:
                action.status = "success"
                action.execution_timestamp = datetime.utcnow()
                action.executed_by = "RemediationAgent"
                logger.info(f"Action executed successfully: {action_id}")

                # Log audit event
                self.log_audit_event(
                    event_type=f"action_{action.action_type}",
                    resource_type=action.action_type.split('_')[0],
                    resource_name=action.target_resource,
                    description=action.description,
                    status="success",
                    before_state=action.before_state,
                    after_state=action.after_state
                )

                # Notify on success
                if self.notification_manager:
                    self.notification_manager.notify_action_executed(
                        action_id=action_id,
                        action_type=action.action_type,
                        resource=action.target_resource,
                        status="success"
                    )

            else:
                action.status = "failed"
                action.execution_timestamp = datetime.utcnow()
                logger.error(f"Action failed: {action_id}")

                # Log audit event
                self.log_audit_event(
                    event_type=f"action_failed_{action.action_type}",
                    resource_type=action.action_type.split('_')[0],
                    resource_name=action.target_resource,
                    description=f"Failed: {action.description}",
                    status="failed",
                    error_message=action.error_message
                )

            return success

        except Exception as e:
            action.status = "failed"
            action.error_message = str(e)
            action.execution_timestamp = datetime.utcnow()
            logger.error(f"Exception executing action {action_id}: {str(e)}")
            return False

    def process_pending_actions(self) -> None:
        """Process all pending remediation actions."""
        logger.info(f"Processing {len(self.pending_actions)} pending actions")

        for action_id, action in list(self.pending_actions.items()):
            if action.status == "pending":
                # Check if approval was received
                if action.approval_request_id:
                    approval_request = self.approval_manager.get_request(action.approval_request_id)
                    if approval_request and approval_request.status.value == "approved":
                        self.execute_action(action_id)
                    elif approval_request and approval_request.status.value == "rejected":
                        action.status = "rejected"
                        logger.info(f"Action rejected: {action_id}")

            elif action.status in ["success", "failed", "rolled_back"]:
                # Move completed actions to history
                self.completed_actions.append(action)
                del self.pending_actions[action_id]

    # ========================================================================
    # INCIDENT MANAGEMENT
    # ========================================================================

    def create_incident(
        self,
        category: str,
        severity: str,
        description: str,
        resource_type: str,
        resource_name: str
    ) -> str:
        """
        Create an incident from a finding.

        Args:
            category: Incident category
            severity: Severity level
            description: Incident description
            resource_type: Type of resource
            resource_name: Name of resource

        Returns:
            Incident ID
        """
        incident = Incident(category, severity, description, resource_type, resource_name)
        self.active_incidents[incident.incident_id] = incident

        logger.info(f"Created incident: {incident.incident_id} (severity: {severity})")

        # Persist to database
        self._persist_incident(incident)

        # Notify if critical
        if severity == IncidentSeverity.CRITICAL:
            if self.notification_manager:
                self.notification_manager.notify_critical_incident(
                    incident_id=incident.incident_id,
                    category=category,
                    description=description
                )

        return incident.incident_id

    def check_incident_status(self) -> None:
        """Check status of active incidents and escalate if needed."""
        logger.info(f"Checking status of {len(self.active_incidents)} incidents")

        for incident_id, incident in list(self.active_incidents.items()):
            if incident.status == IncidentStatus.OPEN:
                # Check how long incident has been open
                hours_open = (datetime.utcnow() - incident.detected_timestamp).total_seconds() / 3600

                # Escalate if open too long
                if incident.severity == IncidentSeverity.CRITICAL and hours_open > 1:
                    incident.escalate()
                    logger.warning(f"Escalated critical incident {incident_id} (open {hours_open:.1f}h)")

                    if self.notification_manager:
                        self.notification_manager.notify_incident_escalation(
                            incident_id=incident_id,
                            severity=incident.severity,
                            hours_open=hours_open
                        )

                elif incident.severity == IncidentSeverity.HIGH and hours_open > 4:
                    incident.escalate()
                    logger.warning(f"Escalated high incident {incident_id} (open {hours_open:.1f}h)")

    def resolve_closed_incidents(self) -> None:
        """Resolve incidents that have been fixed by remediation actions."""
        logger.info("Checking for resolved incidents")

        for incident_id, incident in list(self.active_incidents.items()):
            if incident.status in [IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]:
                # Check if all related actions succeeded
                if incident.related_actions:
                    actions = [self.pending_actions.get(aid) or self._find_completed_action(aid)
                               for aid in incident.related_actions]
                    all_succeeded = all(a and a.status == "success" for a in actions if a)

                    if all_succeeded:
                        incident.resolve(notes="All remediation actions completed successfully")
                        logger.info(f"Resolved incident: {incident_id}")

                        # Persist to database
                        self._persist_incident(incident)

    def add_action_to_incident(self, incident_id: str, action_id: str) -> bool:
        """Associate a remediation action with an incident."""
        incident = self.active_incidents.get(incident_id)
        if not incident:
            logger.error(f"Incident not found: {incident_id}")
            return False

        incident.related_actions.append(action_id)
        logger.info(f"Associated action {action_id} with incident {incident_id}")
        return True

    # ========================================================================
    # SPECIFIC ACTION IMPLEMENTATIONS
    # ========================================================================

    def _abort_query(self, action: RemediationAction) -> bool:
        """Abort a runaway query."""
        try:
            query_id = action.target_resource
            logger.info(f"Aborting query: {query_id}")

            # Record before state
            query_profile = self.snowpark_client.get_query_profile(query_id)
            action.before_state = query_profile

            # Abort the query
            success = self.snowpark_client.abort_query(query_id)

            if success:
                action.after_state = {"status": "aborted", "abort_timestamp": datetime.utcnow().isoformat()}
                logger.info(f"Successfully aborted query: {query_id}")

            return success

        except Exception as e:
            action.error_message = str(e)
            logger.error(f"Failed to abort query: {str(e)}")
            return False

    def _suspend_warehouse(self, action: RemediationAction) -> bool:
        """Suspend a warehouse."""
        try:
            warehouse_name = action.target_resource
            logger.info(f"Suspending warehouse: {warehouse_name}")

            # Record before state
            metrics = self.snowpark_client.get_warehouse_metrics(warehouse_name)
            action.before_state = metrics

            # Suspend warehouse
            success = self.snowpark_client.suspend_warehouse(warehouse_name)

            if success:
                action.after_state = {"state": "suspended", "suspend_timestamp": datetime.utcnow().isoformat()}
                logger.info(f"Successfully suspended warehouse: {warehouse_name}")

            return success

        except Exception as e:
            action.error_message = str(e)
            logger.error(f"Failed to suspend warehouse: {str(e)}")
            return False

    def _resume_warehouse(self, action: RemediationAction) -> bool:
        """Resume a warehouse."""
        try:
            warehouse_name = action.target_resource
            logger.info(f"Resuming warehouse: {warehouse_name}")

            success = self.snowpark_client.resume_warehouse(warehouse_name)

            if success:
                action.after_state = {"state": "resumed", "resume_timestamp": datetime.utcnow().isoformat()}
                logger.info(f"Successfully resumed warehouse: {warehouse_name}")

            return success

        except Exception as e:
            action.error_message = str(e)
            logger.error(f"Failed to resume warehouse: {str(e)}")
            return False

    def _enable_auto_suspend(self, action: RemediationAction) -> bool:
        """Enable auto-suspend on a warehouse."""
        try:
            warehouse_name = action.target_resource
            minutes = action.before_state.get("auto_suspend_minutes", 10)

            logger.info(f"Enabling auto-suspend on {warehouse_name} ({minutes} minutes)")

            success = self.snowpark_client.set_warehouse_auto_suspend(warehouse_name, minutes)

            if success:
                action.after_state = {"auto_suspend_enabled": True, "auto_suspend_minutes": minutes}

            return success

        except Exception as e:
            action.error_message = str(e)
            logger.error(f"Failed to enable auto-suspend: {str(e)}")
            return False

    def _scale_warehouse(self, action: RemediationAction) -> bool:
        """Scale a warehouse to new size."""
        try:
            warehouse_name = action.target_resource
            new_size = action.before_state.get("new_size")

            if not new_size:
                action.error_message = "New size not specified"
                return False

            logger.info(f"Scaling {warehouse_name} to {new_size}")

            success = self.snowpark_client.scale_warehouse(warehouse_name, new_size)

            if success:
                action.after_state = {"size": new_size, "scale_timestamp": datetime.utcnow().isoformat()}

            return success

        except Exception as e:
            action.error_message = str(e)
            logger.error(f"Failed to scale warehouse: {str(e)}")
            return False

    def _revoke_role(self, action: RemediationAction) -> bool:
        """Revoke a role from a user."""
        try:
            user_and_role = action.target_resource.split(":")
            if len(user_and_role) != 2:
                action.error_message = "Invalid target format (expected user:role)"
                return False

            user_name, role_name = user_and_role
            logger.info(f"Revoking {role_name} from {user_name}")

            success = self.snowpark_client.revoke_role_from_user(user_name, role_name)

            if success:
                action.after_state = {"role_revoked": role_name, "from_user": user_name}

            return success

        except Exception as e:
            action.error_message = str(e)
            logger.error(f"Failed to revoke role: {str(e)}")
            return False

    def _grant_role(self, action: RemediationAction) -> bool:
        """Grant a role to a user (for recovery/remediation)."""
        try:
            user_and_role = action.target_resource.split(":")
            if len(user_and_role) != 2:
                action.error_message = "Invalid target format (expected user:role)"
                return False

            user_name, role_name = user_and_role
            logger.info(f"Granting {role_name} to {user_name}")

            success = self.snowpark_client.grant_role_to_user(user_name, role_name)

            if success:
                action.after_state = {"role_granted": role_name, "to_user": user_name}

            return success

        except Exception as e:
            action.error_message = str(e)
            logger.error(f"Failed to grant role: {str(e)}")
            return False

    # ========================================================================
    # RECOMMENDATION GENERATION
    # ========================================================================

    def generate_remediation_recommendations(self) -> None:
        """Generate recommendations for failed remediations."""
        logger.info("Generating recommendations for failed actions")

        failed_actions = [a for a in self.completed_actions if a.status == "failed"]

        for action in failed_actions:
            rec = Recommendation(
                recommendation_id=None,
                title=f"Manual intervention needed: {action.action_type}",
                description=f"Automatic remediation failed: {action.error_message}",
                action_type="manual_intervention",
                resource_type="action",
                resource_name=action.action_id,
                impact="high"
            )
            rec.add_step(f"Review failure reason: {action.error_message}")
            rec.add_step(f"Perform manual {action.action_type} on {action.target_resource}")
            rec.add_step("Verify remediation was effective")
            self.add_recommendation(rec)

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _request_action_approval(self, action: RemediationAction) -> None:
        """Request approval for a remediation action."""
        if not self.approval_manager:
            logger.warning("No approval manager configured")
            return

        request_id = self.approval_manager.create_request(
            request_type="remediation_action",
            title=f"Approve remediation: {action.action_type}",
            description=action.description,
            context=action.to_dict(),
            requestor_email="agent@governance",
            approver_email="admin@company.com",
            priority="high",
            sla_hours=1
        )

        action.approval_request_id = request_id
        logger.info(f"Requested approval for action {action.action_id}: {request_id}")

    def _persist_incident(self, incident: Incident) -> bool:
        """Persist incident to database."""
        try:
            sql = f"""
            INSERT INTO governance.incidents (
                incident_id, severity, category, description, detected_timestamp,
                assigned_to, status, related_actions
            ) VALUES (
                '{incident.incident_id}',
                '{incident.severity}',
                '{incident.category}',
                '{incident.description}',
                '{incident.detected_timestamp.isoformat()}',
                '{incident.assigned_to}',
                '{incident.status}',
                '{incident.related_actions}'
            )
            """
            self.snowpark_client.session.sql(sql).collect()
            logger.debug(f"Persisted incident {incident.incident_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist incident: {str(e)}")
            return False

    def _find_completed_action(self, action_id: str) -> Optional[RemediationAction]:
        """Find a completed action."""
        return next((a for a in self.completed_actions if a.action_id == action_id), None)

    def get_action_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a remediation action."""
        action = self.pending_actions.get(action_id) or self._find_completed_action(action_id)
        return action.to_dict() if action else None

    def get_incident_status(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an incident."""
        incident = self.active_incidents.get(incident_id)
        return incident.to_dict() if incident else None

    def get_summary(self) -> Dict[str, Any]:
        """Get remediation agent summary."""
        return {
            "pending_actions": len(self.pending_actions),
            "completed_actions": len(self.completed_actions),
            "active_incidents": len(self.active_incidents),
            "successful_remediations": len([a for a in self.completed_actions if a.status == "success"]),
            "failed_remediations": len([a for a in self.completed_actions if a.status == "failed"])
        }
