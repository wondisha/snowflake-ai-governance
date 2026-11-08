"""
Approval Workflow Manager - Manages approval request lifecycle.
Handles creation, approval, rejection, and escalation of governance actions.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import logging
import uuid


logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class ApprovalPriority(Enum):
    """Approval priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ApprovalRequest:
    """Represents an approval request."""

    def __init__(
        self,
        request_type: str,
        title: str,
        description: str,
        context: Dict[str, Any],
        requestor_email: str,
        approver_email: str,
        priority: ApprovalPriority = ApprovalPriority.MEDIUM,
        sla_hours: int = 24
    ):
        self.request_id = str(uuid.uuid4())
        self.request_type = request_type
        self.title = title
        self.description = description
        self.context = context
        self.requestor_email = requestor_email
        self.approver_email = approver_email
        self.priority = priority
        self.sla_hours = sla_hours

        # Status tracking
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=sla_hours)
        self.approved_at = None
        self.approved_by = None
        self.rejection_reason = None
        self.approval_comments = None

        # Escalation tracking
        self.escalation_count = 0
        self.last_escalation_at = None

    def is_expired(self) -> bool:
        """Check if request has expired."""
        return datetime.utcnow() > self.expires_at and self.status == ApprovalStatus.PENDING

    def approve(self, approver_email: str, comments: str = "") -> bool:
        """Approve the request."""
        if self.status != ApprovalStatus.PENDING:
            logger.error(f"Cannot approve non-pending request {self.request_id}")
            return False

        self.status = ApprovalStatus.APPROVED
        self.approved_at = datetime.utcnow()
        self.approved_by = approver_email
        self.approval_comments = comments
        logger.info(f"Request {self.request_id} approved by {approver_email}")
        return True

    def reject(self, approver_email: str, reason: str = "") -> bool:
        """Reject the request."""
        if self.status != ApprovalStatus.PENDING:
            logger.error(f"Cannot reject non-pending request {self.request_id}")
            return False

        self.status = ApprovalStatus.REJECTED
        self.approved_by = approver_email
        self.rejection_reason = reason
        self.approved_at = datetime.utcnow()
        logger.info(f"Request {self.request_id} rejected by {approver_email}: {reason}")
        return True

    def expire(self) -> bool:
        """Expire the request."""
        if self.status != ApprovalStatus.PENDING:
            logger.error(f"Cannot expire non-pending request {self.request_id}")
            return False

        self.status = ApprovalStatus.EXPIRED
        logger.warning(f"Request {self.request_id} expired")
        return True

    def escalate(self) -> None:
        """Escalate the request."""
        self.escalation_count += 1
        self.last_escalation_at = datetime.utcnow()
        if self.escalation_count >= 2:  # After 2 escalations, mark as escalated
            self.status = ApprovalStatus.ESCALATED
        logger.warning(f"Request {self.request_id} escalated (count: {self.escalation_count})")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "request_type": self.request_type,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "requestor_email": self.requestor_email,
            "approver_email": self.approver_email,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "approval_comments": self.approval_comments,
            "rejection_reason": self.rejection_reason,
            "escalation_count": self.escalation_count,
            "sla_hours": self.sla_hours
        }


class ApprovalWorkflowManager:
    """
    Manages approval workflow for governance actions.
    Handles single-approver workflow with SLA tracking and escalation.
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """
        Initialize Approval Workflow Manager.

        Args:
            snowpark_client: Snowflake connector
            notification_manager: Notification service
        """
        self.snowpark_client = snowpark_client
        self.notification_manager = notification_manager

        # In-memory cache of approval requests
        # In production, these would all be persisted in Snowflake
        self.active_requests: Dict[str, ApprovalRequest] = {}
        self.history: List[ApprovalRequest] = []

    # ========================================================================
    # REQUEST LIFECYCLE
    # ========================================================================

    def create_request(
        self,
        request_type: str,
        title: str,
        description: str,
        context: Dict[str, Any],
        requestor_email: str,
        approver_email: str,
        priority: str = "medium",
        sla_hours: int = 24
    ) -> str:
        """
        Create a new approval request.

        Args:
            request_type: Type of approval
            title: Request title
            description: Request description
            context: Full context data
            requestor_email: Email of requestor
            approver_email: Email of approver
            priority: Priority level (critical, high, medium, low)
            sla_hours: Hours until auto-expiry

        Returns:
            Request ID
        """
        priority_enum = ApprovalPriority[priority.upper()] if priority.upper() in [p.name for p in ApprovalPriority] else ApprovalPriority.MEDIUM

        request = ApprovalRequest(
            request_type=request_type,
            title=title,
            description=description,
            context=context,
            requestor_email=requestor_email,
            approver_email=approver_email,
            priority=priority_enum,
            sla_hours=sla_hours
        )

        self.active_requests[request.request_id] = request
        logger.info(f"Created approval request: {request.request_id} (type: {request_type}, priority: {priority})")

        # Persist to database
        self._persist_request_to_db(request)

        # Notify approver
        if self.notification_manager:
            self.notification_manager.notify_approval_pending(
                request_id=request.request_id,
                request_type=request_type,
                title=title,
                approver_email=approver_email,
                priority=priority
            )

        return request.request_id

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Retrieve an approval request."""
        return self.active_requests.get(request_id)

    def get_pending_requests(self, approver_email: str = None) -> List[ApprovalRequest]:
        """Get pending approval requests."""
        pending = [
            r for r in self.active_requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

        if approver_email:
            pending = [r for r in pending if r.approver_email == approver_email]

        # Sort by priority and age
        pending.sort(key=lambda x: (x.priority.name, x.created_at))
        return pending

    def get_pending_count(self, approver_email: str) -> int:
        """Get count of pending requests for approver."""
        return len(self.get_pending_requests(approver_email))

    # ========================================================================
    # APPROVAL ACTIONS
    # ========================================================================

    def approve_request(
        self,
        request_id: str,
        approver_email: str,
        comments: str = ""
    ) -> bool:
        """
        Approve an approval request.

        Args:
            request_id: Request ID
            approver_email: Email of approver
            comments: Optional approval comments

        Returns:
            True if successful
        """
        request = self.get_request(request_id)
        if not request:
            logger.error(f"Request not found: {request_id}")
            return False

        if request.approver_email != approver_email:
            logger.error(f"Approver mismatch: {approver_email} not authorized for {request_id}")
            return False

        if not request.approve(approver_email, comments):
            return False

        logger.info(f"Approved request: {request_id}")

        # Update database
        self._update_request_in_db(request)

        # Log audit event
        self._log_approval_audit(request, "approved")

        # Notify requestor
        if self.notification_manager:
            self.notification_manager.notify_request_approved(
                request_id=request_id,
                requestor_email=request.requestor_email,
                title=request.title
            )

        return True

    def reject_request(
        self,
        request_id: str,
        approver_email: str,
        reason: str = ""
    ) -> bool:
        """
        Reject an approval request.

        Args:
            request_id: Request ID
            approver_email: Email of approver
            reason: Rejection reason

        Returns:
            True if successful
        """
        request = self.get_request(request_id)
        if not request:
            logger.error(f"Request not found: {request_id}")
            return False

        if request.approver_email != approver_email:
            logger.error(f"Approver mismatch: {approver_email} not authorized for {request_id}")
            return False

        if not request.reject(approver_email, reason):
            return False

        logger.info(f"Rejected request: {request_id} - {reason}")

        # Update database
        self._update_request_in_db(request)

        # Log audit event
        self._log_approval_audit(request, "rejected")

        # Notify requestor
        if self.notification_manager:
            self.notification_manager.notify_request_rejected(
                request_id=request_id,
                requestor_email=request.requestor_email,
                title=request.title,
                reason=reason
            )

        return True

    # ========================================================================
    # SLA & ESCALATION
    # ========================================================================

    def check_sla_and_escalate(self) -> List[str]:
        """
        Check for SLA breaches and escalate as needed.

        Returns:
            List of escalated request IDs
        """
        escalated = []

        for request in self.get_pending_requests():
            if request.is_expired():
                logger.warning(f"SLA breach on request {request.request_id}")
                request.expire()
                self._update_request_in_db(request)
                self._log_sla_breach(request)

                # Escalate if not already done
                if not request.is_expired():
                    request.escalate()
                    escalated.append(request.request_id)
                    self._handle_escalation(request)

            # Also check for near-SLA (e.g., > 75% of time passed)
            else:
                hours_remaining = (request.expires_at - datetime.utcnow()).total_seconds() / 3600
                if hours_remaining < request.sla_hours * 0.25:  # < 25% time remaining
                    logger.warning(f"SLA warning on request {request.request_id}: {hours_remaining:.1f} hours remaining")
                    if self.notification_manager:
                        self.notification_manager.notify_sla_warning(
                            request_id=request.request_id,
                            approver_email=request.approver_email,
                            hours_remaining=hours_remaining
                        )

        return escalated

    def _handle_escalation(self, request: ApprovalRequest) -> None:
        """Handle escalation of a request."""
        logger.warning(f"Escalating request {request.request_id}")

        # Update status
        request.escalate()
        self._update_request_in_db(request)

        # Notify higher-level approvers (in production, this would route to manager, etc.)
        if self.notification_manager:
            self.notification_manager.notify_escalation(
                request_id=request.request_id,
                original_approver=request.approver_email,
                title=request.title,
                priority=request.priority.value
            )

        # Log escalation audit
        self._log_escalation_audit(request)

    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================

    def _persist_request_to_db(self, request: ApprovalRequest) -> bool:
        """Persist approval request to database."""
        try:
            # Build SQL insert
            sql = f"""
            INSERT INTO governance.approval_requests (
                request_id, request_type, source_agent, requestor_email,
                approver_email, request_context, request_title,
                request_description, status, created_at, request_expires_at,
                sla_hours, priority
            ) VALUES (
                '{request.request_id}',
                '{request.request_type}',
                'approval_manager',
                '{request.requestor_email}',
                '{request.approver_email}',
                '{self._escape_json(request.context)}',
                '{self._escape_string(request.title)}',
                '{self._escape_string(request.description)}',
                '{request.status.value}',
                '{request.created_at.isoformat()}',
                '{request.expires_at.isoformat()}',
                {request.sla_hours},
                '{request.priority.value}'
            )
            """
            self.snowpark_client.session.sql(sql).collect()
            logger.debug(f"Persisted approval request {request.request_id} to database")
            return True
        except Exception as e:
            logger.error(f"Failed to persist request to database: {str(e)}")
            return False

    def _update_request_in_db(self, request: ApprovalRequest) -> bool:
        """Update approval request in database."""
        try:
            sql = f"""
            UPDATE governance.approval_requests
            SET status = '{request.status.value}',
                approved_by = '{request.approved_by}',
                approval_comments = '{self._escape_string(request.approval_comments or "")}',
                approved_at = {'CURRENT_TIMESTAMP()' if request.approved_at else 'NULL'}
            WHERE request_id = '{request.request_id}'
            """
            self.snowpark_client.session.sql(sql).collect()
            logger.debug(f"Updated approval request {request.request_id} in database")
            return True
        except Exception as e:
            logger.error(f"Failed to update request in database: {str(e)}")
            return False

    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================

    def _log_approval_audit(self, request: ApprovalRequest, action: str) -> None:
        """Log approval action to audit trail."""
        try:
            self.snowpark_client.insert_audit_log({
                "audit_id": str(uuid.uuid4()),
                "event_type": f"approval_{action}",
                "event_category": "approval_workflow",
                "resource_type": "approval_request",
                "resource_name": request.request_id,
                "actor_email": request.approved_by,
                "action_description": f"{action.title()} approval request: {request.title}",
                "status": "success",
                "event_timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to log approval audit: {str(e)}")

    def _log_sla_breach(self, request: ApprovalRequest) -> None:
        """Log SLA breach to audit trail."""
        try:
            self.snowpark_client.insert_audit_log({
                "audit_id": str(uuid.uuid4()),
                "event_type": "sla_breach",
                "event_category": "approval_workflow",
                "resource_type": "approval_request",
                "resource_name": request.request_id,
                "actor_email": "system",
                "action_description": f"SLA breach on approval request: {request.title}",
                "status": "warning",
                "event_timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to log SLA breach: {str(e)}")

    def _log_escalation_audit(self, request: ApprovalRequest) -> None:
        """Log escalation to audit trail."""
        try:
            self.snowpark_client.insert_audit_log({
                "audit_id": str(uuid.uuid4()),
                "event_type": "escalation",
                "event_category": "approval_workflow",
                "resource_type": "approval_request",
                "resource_name": request.request_id,
                "actor_email": "system",
                "action_description": f"Escalated approval request: {request.title}",
                "status": "warning",
                "event_timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to log escalation: {str(e)}")

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _escape_string(self, s: str) -> str:
        """Escape single quotes in string for SQL."""
        if not s:
            return ""
        return s.replace("'", "''")

    def _escape_json(self, obj: Any) -> str:
        """Escape JSON for SQL."""
        import json
        json_str = json.dumps(obj)
        return self._escape_string(json_str)

    def get_statistics(self) -> Dict[str, Any]:
        """Get approval workflow statistics."""
        total_requests = len(self.active_requests) + len(self.history)
        pending = len(self.get_pending_requests())
        approved = len([r for r in self.active_requests.values() if r.status == ApprovalStatus.APPROVED])
        rejected = len([r for r in self.active_requests.values() if r.status == ApprovalStatus.REJECTED])

        return {
            "total_requests": total_requests,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": f"{(approved / max(total_requests, 1)) * 100:.1f}%",
            "average_sla_hours": sum([r.sla_hours for r in self.active_requests.values()]) / max(len(self.active_requests), 1)
        }
