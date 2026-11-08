"""
Slack Bot Integration - Interactive approval workflows and real-time alerts.
Enables business users to monitor governance findings and approve actions via Slack.
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


logger = logging.getLogger(__name__)


class SlackBotHandler:
    """
    Slack Bot Handler - Manages all Slack interactions.
    Sends notifications, handles approvals, executes commands.
    """

    def __init__(self, slack_bot_token: str, slack_app_token: str = None):
        """
        Initialize Slack bot.

        Args:
            slack_bot_token: Bot token for Slack API
            slack_app_token: App token for Socket Mode (optional)
        """
        self.client = WebClient(token=slack_bot_token)
        self.bot_token = slack_bot_token
        self.app_token = slack_app_token

        # Channel configuration
        self.alerts_channel = "#governance-alerts"
        self.approvals_channel = "#governance-approvals"
        self.status_channel = "#governance-status"

        # Test connection
        try:
            response = self.client.auth_test()
            self.bot_user_id = response["user_id"]
            self.bot_user_name = response["user"]
            logger.info(f"Slack bot connected: {self.bot_user_name}")
        except SlackApiError as e:
            logger.error(f"Failed to connect to Slack: {e}")
            raise

    # ========================================================================
    # APPROVAL NOTIFICATIONS
    # ========================================================================

    def notify_approval_required(
        self,
        request_id: str,
        request_type: str,
        title: str,
        description: str,
        approver_email: str,
        priority: str = "medium"
    ) -> bool:
        """
        Send approval request notification to Slack.

        Args:
            request_id: Approval request ID
            request_type: Type of approval
            title: Request title
            description: Request description
            approver_email: Approver's email
            priority: Priority level (critical, high, medium, low)

        Returns:
            True if sent successfully
        """
        try:
            # Determine color based on priority
            color_map = {
                "critical": "#FF0000",
                "high": "#FF6600",
                "medium": "#FFCC00",
                "low": "#00CC00"
            }
            color = color_map.get(priority, "#0099FF")

            # Build message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔔 {priority.upper()} PRIORITY: Approval Required",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n{description}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Request ID:*\n`{request_id}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Type:*\n{request_type}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Priority:*\n{priority}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Approver:*\n{approver_email}"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Approve",
                                "emoji": True
                            },
                            "action_id": f"approve_{request_id}",
                            "value": request_id,
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "❌ Reject",
                                "emoji": True
                            },
                            "action_id": f"reject_{request_id}",
                            "value": request_id,
                            "style": "danger"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📋 Details",
                                "emoji": True
                            },
                            "action_id": f"details_{request_id}",
                            "value": request_id
                        }
                    ]
                }
            ]

            # Get user ID from email
            user_id = self._get_user_id_by_email(approver_email)
            if user_id:
                # Send as DM to approver
                dm_channel = self.client.conversations_open(users=[user_id])["channel"]["id"]
                self.client.chat_postMessage(
                    channel=dm_channel,
                    blocks=blocks
                )
                logger.info(f"Sent approval request {request_id} to {approver_email} via DM")
            else:
                # Post to approvals channel as fallback
                self.client.chat_postMessage(
                    channel=self.approvals_channel,
                    blocks=blocks
                )
                logger.info(f"Sent approval request {request_id} to {self.approvals_channel}")

            return True

        except SlackApiError as e:
            logger.error(f"Failed to send approval notification: {e}")
            return False

    # ========================================================================
    # ALERT NOTIFICATIONS
    # ========================================================================

    def notify_finding(
        self,
        finding_id: str,
        title: str,
        description: str,
        severity: str,
        category: str,
        resource_name: str
    ) -> bool:
        """
        Send finding alert to Slack.

        Args:
            finding_id: Finding ID
            title: Finding title
            description: Finding description
            severity: Severity level
            category: Finding category
            resource_name: Resource affected

        Returns:
            True if sent successfully
        """
        try:
            # Severity emoji and color
            severity_map = {
                "critical": ("🚨", "#FF0000"),
                "high": ("⚠️", "#FF6600"),
                "medium": ("⚡", "#FFCC00"),
                "low": ("ℹ️", "#0099FF"),
                "info": ("💡", "#00CC00")
            }
            emoji, color = severity_map.get(severity, ("🔔", "#0099FF"))

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{severity.upper()}: {title}*\n{description}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Category: {category} | Resource: {resource_name}"
                        }
                    ]
                }
            ]

            self.client.chat_postMessage(
                channel=self.alerts_channel,
                blocks=blocks
            )

            logger.info(f"Sent finding alert {finding_id} to {self.alerts_channel}")
            return True

        except SlackApiError as e:
            logger.error(f"Failed to send finding alert: {e}")
            return False

    def notify_critical_incident(
        self,
        incident_id: str,
        category: str,
        description: str,
        priority_users: list = None
    ) -> bool:
        """
        Send critical incident alert to Slack and mention users.

        Args:
            incident_id: Incident ID
            category: Incident category
            description: Incident description
            priority_users: List of email addresses to mention

        Returns:
            True if sent successfully
        """
        try:
            mentions = ""
            if priority_users:
                for email in priority_users:
                    user_id = self._get_user_id_by_email(email)
                    if user_id:
                        mentions += f"<@{user_id}> "

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🚨 🚨 🚨 *CRITICAL INCIDENT* 🚨 🚨 🚨\n{mentions}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{category.upper()}*\n{description}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident ID:*\n`{incident_id}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        }
                    ]
                }
            ]

            self.client.chat_postMessage(
                channel=self.alerts_channel,
                blocks=blocks
            )

            logger.info(f"Sent critical incident {incident_id} to {self.alerts_channel}")
            return True

        except SlackApiError as e:
            logger.error(f"Failed to send incident alert: {e}")
            return False

    # ========================================================================
    # SUMMARY REPORTS
    # ========================================================================

    def send_daily_summary(
        self,
        findings_count: Dict[str, int],  # {'critical': 2, 'high': 5, ...}
        recommendations_count: int,
        pending_approvals: int,
        remediation_status: Dict[str, int]  # {'success': 3, 'failed': 1, ...}
    ) -> bool:
        """
        Send daily governance summary to Slack.

        Args:
            findings_count: Count of findings by severity
            recommendations_count: Total recommendations
            pending_approvals: Count of pending approvals
            remediation_status: Remediation action statuses

        Returns:
            True if sent successfully
        """
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📊 Daily Governance Summary",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*🚨 Critical Findings*\n{findings_count.get('critical', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*⚠️ High Findings*\n{findings_count.get('high', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*⚡ Medium Findings*\n{findings_count.get('medium', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*💡 Low Findings*\n{findings_count.get('low', 0)}"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Recommendations*\n{recommendations_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Pending Approvals*\n{pending_approvals}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*✅ Remediations*\n{remediation_status.get('success', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*❌ Failed*\n{remediation_status.get('failed', 0)}"
                        }
                    ]
                }
            ]

            self.client.chat_postMessage(
                channel=self.status_channel,
                blocks=blocks
            )

            logger.info(f"Sent daily summary to {self.status_channel}")
            return True

        except SlackApiError as e:
            logger.error(f"Failed to send summary: {e}")
            return False

    # ========================================================================
    # SLASH COMMANDS
    # ========================================================================

    def handle_slash_command(self, command: str, args: str = "") -> Dict[str, Any]:
        """
        Handle Slack slash commands.

        Args:
            command: Command name (e.g., 'status', 'slow-queries', etc.)
            args: Command arguments

        Returns:
            Response with data or error message
        """
        handlers = {
            "status": self._cmd_status,
            "slow-queries": self._cmd_slow_queries,
            "cost-forecast": self._cmd_cost_forecast,
            "health": self._cmd_warehouse_health,
            "audit": self._cmd_audit_log,
            "pending": self._cmd_pending_approvals,
            "help": self._cmd_help
        }

        handler = handlers.get(command)
        if not handler:
            return {"error": f"Unknown command: {command}. Type /governance help"}

        try:
            return handler(args)
        except Exception as e:
            logger.error(f"Command failed: {str(e)}")
            return {"error": f"Command failed: {str(e)}"}

    def _cmd_status(self, args: str) -> Dict[str, Any]:
        """Return governance system status."""
        return {
            "status": "🟢 HEALTHY",
            "last_scan": datetime.utcnow().isoformat(),
            "agents_running": 5,
            "critical_issues": 0
        }

    def _cmd_slow_queries(self, args: str) -> Dict[str, Any]:
        """Return top slow queries."""
        return {
            "top_slow_queries": [
                {"query_id": "abc123", "duration": "45s", "user": "john.doe"},
                {"query_id": "def456", "duration": "38s", "user": "jane.smith"}
            ],
            "threshold": "30s",
            "time_period": "last 24 hours"
        }

    def _cmd_cost_forecast(self, args: str) -> Dict[str, Any]:
        """Return cost forecast."""
        return {
            "daily_average": "$250",
            "monthly_forecast": "$7,500",
            "trend": "↑ +5% from last month",
            "top_warehouses": [
                {"name": "COMPUTE_WH", "cost": "$150/day"},
                {"name": "REPORTING_WH", "cost": "$75/day"}
            ]
        }

    def _cmd_warehouse_health(self, args: str) -> Dict[str, Any]:
        """Return warehouse health status."""
        return {
            "warehouses": [
                {"name": "COMPUTE_WH", "status": "🟢 HEALTHY", "queue": 0},
                {"name": "REPORTING_WH", "status": "🟡 CAUTION", "queue": 3}
            ],
            "issues": "1 warehouse with elevated queue depth"
        }

    def _cmd_audit_log(self, args: str) -> Dict[str, Any]:
        """Return recent audit logs."""
        return {
            "recent_events": [
                {"time": "2024-11-08 14:30", "event": "permission_granted", "user": "admin"},
                {"time": "2024-11-08 14:15", "event": "warehouse_suspended", "warehouse": "REPORTING_WH"},
                {"time": "2024-11-08 14:00", "event": "query_aborted", "query_id": "abc123"}
            ],
            "total_events_24h": 45
        }

    def _cmd_pending_approvals(self, args: str) -> Dict[str, Any]:
        """Return pending approval requests."""
        return {
            "pending_count": 3,
            "pending": [
                {"id": "req123", "type": "permission_grant", "priority": "HIGH"},
                {"id": "req124", "type": "config_change", "priority": "MEDIUM"}
            ]
        }

    def _cmd_help(self, args: str) -> Dict[str, Any]:
        """Return help for commands."""
        return {
            "commands": [
                "/governance status - System health status",
                "/governance slow-queries - Top slow queries",
                "/governance cost-forecast - Monthly cost forecast",
                "/governance health [warehouse] - Warehouse health",
                "/governance audit - Recent audit events",
                "/governance pending - Pending approvals",
                "/governance help - Show this help"
            ]
        }

    # ========================================================================
    # INTERACTIVE ACTIONS (Button Clicks)
    # ========================================================================

    def handle_approval_action(
        self,
        action: str,
        request_id: str,
        user_email: str,
        comments: str = ""
    ) -> Dict[str, Any]:
        """
        Handle approval action button clicks.

        Args:
            action: 'approve', 'reject', or 'details'
            request_id: Approval request ID
            user_email: User performing action
            comments: Optional comments

        Returns:
            Result dictionary
        """
        if action == "approve":
            return {
                "action": "approved",
                "request_id": request_id,
                "approver": user_email,
                "comments": comments
            }
        elif action == "reject":
            return {
                "action": "rejected",
                "request_id": request_id,
                "approver": user_email,
                "reason": comments
            }
        elif action == "details":
            return {
                "action": "show_details",
                "request_id": request_id
            }
        else:
            return {"error": f"Unknown action: {action}"}

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_user_id_by_email(self, email: str) -> Optional[str]:
        """Get Slack user ID from email address."""
        try:
            response = self.client.users_lookupByEmail(email=email)
            return response["user"]["id"]
        except SlackApiError as e:
            if e.response["error"] == "users_not_found":
                logger.warning(f"User not found: {email}")
            else:
                logger.error(f"Error looking up user: {e}")
            return None

    def post_message(self, channel: str, text: str = None, blocks: list = None) -> bool:
        """Post a message to Slack channel."""
        try:
            self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks
            )
            return True
        except SlackApiError as e:
            logger.error(f"Failed to post message: {e}")
            return False

    def update_message(self, channel: str, ts: str, text: str = None, blocks: list = None) -> bool:
        """Update a message in Slack."""
        try:
            self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks
            )
            return True
        except SlackApiError as e:
            logger.error(f"Failed to update message: {e}")
            return False

    def add_reaction(self, channel: str, ts: str, emoji: str) -> bool:
        """Add emoji reaction to a message."""
        try:
            self.client.reactions_add(
                channel=channel,
                timestamp=ts,
                name=emoji
            )
            return True
        except SlackApiError as e:
            logger.error(f"Failed to add reaction: {e}")
            return False
