"""
Base Agent Class - Abstract base for all governance agents.
Provides common lifecycle, state management, and integration patterns.
"""

from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import json
import uuid


logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Agent type classification."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    COST = "cost"
    HEALTH = "health"
    SPILLAGE = "spillage"


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"


class DetectionSeverity(Enum):
    """Severity level for detected issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding:
    """Represents a detected issue or finding."""

    def __init__(
        self,
        finding_id: str,
        title: str,
        description: str,
        severity: DetectionSeverity,
        category: str,
        resource_type: str,
        resource_name: str,
        detected_at: datetime = None,
        details: Dict[str, Any] = None
    ):
        self.finding_id = finding_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.severity = severity
        self.category = category
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.detected_at = detected_at or datetime.utcnow()
        self.details = details or {}
        self.recommendation = None
        self.requires_approval = True
        self.auto_remediate = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "detected_at": self.detected_at.isoformat(),
            "recommendation": self.recommendation,
            "details": self.details,
            "requires_approval": self.requires_approval,
            "auto_remediate": self.auto_remediate
        }


class Recommendation:
    """Represents an optimization or remediation recommendation."""

    def __init__(
        self,
        recommendation_id: str,
        title: str,
        description: str,
        action_type: str,
        resource_type: str,
        resource_name: str,
        impact: str = "medium",  # 'low', 'medium', 'high'
        estimated_benefit: str = None
    ):
        self.recommendation_id = recommendation_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.action_type = action_type
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.impact = impact
        self.estimated_benefit = estimated_benefit
        self.created_at = datetime.utcnow()
        self.implementation_steps = []

    def add_step(self, step: str) -> None:
        """Add implementation step."""
        self.implementation_steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary."""
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "action_type": self.action_type,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "impact": self.impact,
            "estimated_benefit": self.estimated_benefit,
            "implementation_steps": self.implementation_steps,
            "created_at": self.created_at.isoformat()
        }


class GovernanceAgent(ABC):
    """
    Abstract base class for all governance agents.
    Provides common lifecycle management and integration patterns.
    """

    def __init__(
        self,
        agent_name: str,
        agent_type: AgentType,
        snowpark_client,
        notification_manager=None
    ):
        """
        Initialize governance agent.

        Args:
            agent_name: Unique agent name
            agent_type: Agent type classification
            snowpark_client: Snowflake Snowpark client
            notification_manager: Optional notification manager
        """
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.snowpark_client = snowpark_client
        self.notification_manager = notification_manager

        # Execution state
        self.status = AgentStatus.IDLE
        self.last_execution_start = None
        self.last_execution_end = None
        self.last_execution_duration = None
        self.last_error = None

        # Metrics
        self.findings_detected = 0
        self.findings_processed = 0
        self.recommendations_made = 0
        self.execution_count = 0
        self.error_count = 0

        # Current execution
        self.current_findings: List[Finding] = []
        self.current_recommendations: List[Recommendation] = []

        logger.info(f"Initialized agent: {agent_name} (type: {agent_type.value})")

    # ========================================================================
    # LIFECYCLE MANAGEMENT
    # ========================================================================

    def start_execution(self) -> None:
        """Mark agent as running."""
        self.status = AgentStatus.RUNNING
        self.last_execution_start = datetime.utcnow()
        self.current_findings = []
        self.current_recommendations = []
        logger.info(f"{self.agent_name} starting execution")

    def end_execution(self, success: bool = True, error_message: str = None) -> None:
        """Mark agent as finished."""
        self.last_execution_end = datetime.utcnow()
        self.last_execution_duration = (self.last_execution_end - self.last_execution_start).total_seconds()
        self.execution_count += 1

        if success:
            self.status = AgentStatus.SUCCESS
            logger.info(
                f"{self.agent_name} completed successfully "
                f"(duration: {self.last_execution_duration}s, "
                f"findings: {len(self.current_findings)})"
            )
        else:
            self.status = AgentStatus.FAILED
            self.error_count += 1
            self.last_error = error_message
            logger.error(f"{self.agent_name} failed: {error_message}")

        # Update agent state in database
        self._update_agent_state()

    def _update_agent_state(self) -> None:
        """Update agent state in governance schema."""
        try:
            state_data = {
                "last_execution_timestamp": self.last_execution_end.isoformat() if self.last_execution_end else None,
                "last_successful_execution": self.last_execution_end.isoformat() if self.status == AgentStatus.SUCCESS else None,
                "execution_status": self.status.value,
                "items_detected": self.findings_detected,
                "items_processed": self.findings_processed,
                "error_count": self.error_count,
                "last_error_message": self.last_error
            }
            self.snowpark_client.update_agent_state(self.agent_name, state_data)
        except Exception as e:
            logger.error(f"Failed to update agent state: {str(e)}")

    # ========================================================================
    # FINDING & RECOMMENDATION MANAGEMENT
    # ========================================================================

    def add_finding(self, finding: Finding) -> None:
        """Register a finding."""
        self.current_findings.append(finding)
        self.findings_detected += 1
        logger.debug(f"Finding detected: {finding.title} (severity: {finding.severity.value})")

    def add_recommendation(self, recommendation: Recommendation) -> None:
        """Register a recommendation."""
        self.current_recommendations.append(recommendation)
        self.recommendations_made += 1
        logger.debug(f"Recommendation made: {recommendation.title}")

    def get_critical_findings(self) -> List[Finding]:
        """Get critical severity findings."""
        return [f for f in self.current_findings if f.severity == DetectionSeverity.CRITICAL]

    def get_findings_by_severity(self, severity: DetectionSeverity) -> List[Finding]:
        """Get findings filtered by severity."""
        return [f for f in self.current_findings if f.severity == severity]

    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================

    def log_audit_event(
        self,
        event_type: str,
        resource_type: str,
        resource_name: str,
        description: str,
        status: str = "success",
        before_state: Dict[str, Any] = None,
        after_state: Dict[str, Any] = None,
        error_message: str = None
    ) -> bool:
        """
        Log an event to the audit trail.

        Args:
            event_type: Type of event (e.g., 'permission_granted')
            resource_type: Type of resource affected
            resource_name: Name of resource
            description: Event description
            status: Event status ('success', 'failed', 'pending')
            before_state: State before change
            after_state: State after change
            error_message: Error details if failed

        Returns:
            True if logged successfully
        """
        audit_data = {
            "audit_id": str(uuid.uuid4()),
            "event_type": event_type,
            "event_category": self.agent_type.value,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "actor_email": "agent@governance",
            "action_description": description,
            "before_state": json.dumps(before_state) if before_state else None,
            "after_state": json.dumps(after_state) if after_state else None,
            "status": status,
            "error_message": error_message,
            "event_timestamp": datetime.utcnow().isoformat()
        }

        try:
            self.snowpark_client.insert_audit_log(audit_data)
            logger.info(f"Audit event logged: {event_type} on {resource_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            return False

    # ========================================================================
    # APPROVAL WORKFLOW
    # ========================================================================

    def request_approval(
        self,
        request_type: str,
        title: str,
        description: str,
        context: Dict[str, Any],
        approver_email: str,
        priority: str = "medium",
        sla_hours: int = 24
    ) -> Optional[str]:
        """
        Request approval for an action.

        Args:
            request_type: Type of approval (e.g., 'permission_grant')
            title: Request title
            description: Request description
            context: Full request context
            approver_email: Email of approver
            priority: Priority level ('critical', 'high', 'medium', 'low')
            sla_hours: Hours until auto-expiry

        Returns:
            Request ID if successful, None otherwise
        """
        request_id = str(uuid.uuid4())

        approval_data = {
            "request_id": request_id,
            "request_type": request_type,
            "source_agent": self.agent_name,
            "requestor_email": "agent@governance",
            "approver_email": approver_email,
            "request_context": json.dumps(context),
            "request_title": title,
            "request_description": description,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "request_expires_at": (datetime.utcnow() + timedelta(hours=sla_hours)).isoformat(),
            "sla_hours": sla_hours,
            "priority": priority
        }

        try:
            # Note: This is a simplified insert - actual implementation would use proper SQL
            logger.info(f"Approval request created: {request_id} (type: {request_type})")

            # Notify approver
            if self.notification_manager:
                self.notification_manager.notify_approval_request(
                    request_id=request_id,
                    request_type=request_type,
                    title=title,
                    description=description,
                    approver_email=approver_email,
                    priority=priority
                )

            return request_id
        except Exception as e:
            logger.error(f"Failed to create approval request: {str(e)}")
            return None

    # ========================================================================
    # ABSTRACT METHODS - MUST BE IMPLEMENTED BY SUBCLASSES
    # ========================================================================

    @abstractmethod
    def detect_issues(self) -> None:
        """
        Main detection logic. Subclasses implement domain-specific detection.
        Must call add_finding() for each detected issue.
        """
        pass

    @abstractmethod
    def generate_recommendations(self) -> None:
        """
        Generate recommendations based on detected issues.
        Must call add_recommendation() for each recommendation.
        """
        pass

    @abstractmethod
    def execute(self) -> bool:
        """
        Main execution method. Orchestrates detection and recommendations.

        Returns:
            True if execution was successful
        """
        pass

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of last execution."""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "execution_start": self.last_execution_start.isoformat() if self.last_execution_start else None,
            "execution_end": self.last_execution_end.isoformat() if self.last_execution_end else None,
            "duration_seconds": self.last_execution_duration,
            "findings_detected": self.findings_detected,
            "findings_current": len(self.current_findings),
            "recommendations_made": self.recommendations_made,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "last_error": self.last_error
        }

    def log_summary(self) -> None:
        """Log execution summary."""
        summary = self.get_execution_summary()
        logger.info(f"Agent Summary: {json.dumps(summary, indent=2)}")
