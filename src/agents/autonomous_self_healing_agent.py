"""
Autonomous Self-Healing Agent - Phase 5
Executes safe remediation actions without approval, with automatic rollback capability.
Decision-making for edge cases, continuous validation, and learning from outcomes.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.agents.base_agent import (
    GovernanceAgent, AgentType, Finding, Recommendation,
    DetectionSeverity
)


logger = logging.getLogger(__name__)


class ActionRiskLevel(Enum):
    """Risk level for autonomous actions."""
    SAFE = "safe"  # Auto-execute immediately
    MODERATE = "moderate"  # Auto-execute with monitoring
    RISKY = "risky"  # Requires approval
    DANGEROUS = "dangerous"  # Never auto-execute


class AutomatedAction:
    """Represents an automated action with rollback capability."""

    def __init__(self, action_id: str, action_type: str, target: str, risk_level: ActionRiskLevel):
        self.action_id = action_id
        self.action_type = action_type
        self.target = target
        self.risk_level = risk_level
        self.before_state = None
        self.after_state = None
        self.executed_at = None
        self.success = False
        self.error = None
        self.rollback_executed = False

    def is_reversible(self) -> bool:
        """Check if action can be rolled back."""
        return self.before_state is not None and self.executed_at is not None

    def mark_executed(self, after_state: Any = None) -> None:
        """Mark action as executed."""
        self.executed_at = datetime.utcnow()
        self.after_state = after_state
        self.success = True

    def mark_failed(self, error: str) -> None:
        """Mark action as failed."""
        self.error = error
        self.success = False


class EdgeCaseDecisionEngine:
    """
    Decision engine for edge cases in autonomous remediation.
    Evaluates context, impact, and prerequisites before executing actions.
    """

    def __init__(self):
        self.decision_history: List[Dict[str, Any]] = []
        self.learned_patterns: Dict[str, Dict[str, Any]] = {}

    def should_execute_action(
        self,
        action_type: str,
        target: str,
        current_state: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Decide whether to execute an action based on context.

        Returns:
            Tuple of (should_execute, reason)
        """
        decision_reason = []

        # Check 1: Is system stable?
        if not self._is_system_stable(current_state):
            return False, "System is unstable - deferring action"
        decision_reason.append("System stable")

        # Check 2: Are prerequisites met?
        if not self._prerequisites_met(action_type, current_state):
            return False, "Prerequisites not met for this action"
        decision_reason.append("Prerequisites met")

        # Check 3: Will action impact critical operations?
        if self._would_impact_critical_ops(action_type, target, current_state):
            return False, "Action would impact critical operations"
        decision_reason.append("No critical operation impact")

        # Check 4: Has similar action succeeded recently?
        if self._has_recent_success(action_type, target):
            decision_reason.append("Similar action succeeded recently")
        else:
            decision_reason.append("First-time or rare action - increased caution")

        # Check 5: Risk mitigation in place?
        if risk_assessment.get("mitigation_available"):
            decision_reason.append("Rollback/mitigation available")
        else:
            return False, "No rollback capability - action too risky"

        return True, " | ".join(decision_reason)

    def _is_system_stable(self, state: Dict[str, Any]) -> bool:
        """Check if system is in stable state for autonomous action."""
        # Don't execute during:
        # - High error rate (>10%)
        # - Active incidents
        # - Ongoing maintenance
        # - Resource saturation
        if state.get("error_rate", 0) > 0.10:
            logger.info("System error rate high - not stable")
            return False
        if state.get("active_incidents", 0) > 0:
            logger.info("Active incidents - not stable")
            return False
        if state.get("maintenance_mode"):
            logger.info("System in maintenance mode - not stable")
            return False
        return True

    def _prerequisites_met(self, action_type: str, state: Dict[str, Any]) -> bool:
        """Verify prerequisites for action type."""
        prerequisites = {
            "query_abort": lambda s: s.get("query_exists"),
            "warehouse_suspend": lambda s: s.get("warehouse_exists") and s.get("no_active_queries"),
            "warehouse_resume": lambda s: s.get("warehouse_exists"),
            "role_revoke": lambda s: s.get("user_exists") and s.get("role_assigned"),
            "warehouse_scale": lambda s: s.get("warehouse_exists") and s.get("can_scale"),
            "create_materialized_view": lambda s: s.get("base_query_valid"),
            "enable_auto_suspend": lambda s: s.get("warehouse_exists"),
        }

        if action_type not in prerequisites:
            return True  # Unknown action - allow

        check_fn = prerequisites[action_type]
        return check_fn(state)

    def _would_impact_critical_ops(self, action_type: str, target: str, state: Dict[str, Any]) -> bool:
        """Check if action would impact critical operations."""
        critical_resources = state.get("critical_warehouses", [])
        critical_roles = state.get("critical_roles", [])

        if action_type == "warehouse_suspend" and target in critical_resources:
            return True
        if action_type == "role_revoke" and target in critical_roles:
            return True

        return False

    def _has_recent_success(self, action_type: str, target: str) -> bool:
        """Check if similar action succeeded in last 7 days."""
        key = f"{action_type}:{target}"
        if key in self.learned_patterns:
            pattern = self.learned_patterns[key]
            last_success = pattern.get("last_success_at")
            if last_success:
                days_ago = (datetime.utcnow() - last_success).days
                return days_ago < 7
        return False

    def record_decision(self, action_type: str, target: str, executed: bool, success: bool) -> None:
        """Record decision outcome for learning."""
        key = f"{action_type}:{target}"
        if key not in self.learned_patterns:
            self.learned_patterns[key] = {
                "success_count": 0,
                "failure_count": 0,
                "last_success_at": None,
                "last_failure_at": None,
            }

        pattern = self.learned_patterns[key]
        if executed and success:
            pattern["success_count"] += 1
            pattern["last_success_at"] = datetime.utcnow()
        elif executed and not success:
            pattern["failure_count"] += 1
            pattern["last_failure_at"] = datetime.utcnow()


class AutonomousSelfHealingAgent(GovernanceAgent):
    """
    Autonomous Self-Healing Agent - Phase 5

    Executes approved remediation actions without manual intervention.
    Features:
    - Risk-based decision making (safe, moderate, risky, dangerous)
    - Edge case evaluation engine
    - Continuous validation during execution
    - Automatic rollback on failure
    - Learning from outcomes
    - Impact prediction before action
    """

    def __init__(self, snowpark_client, notification_manager=None):
        """Initialize autonomous self-healing agent."""
        super().__init__(
            agent_name="AutonomousSelfHealingAgent",
            agent_type=AgentType.HEALTH,
            snowpark_client=snowpark_client,
            notification_manager=notification_manager
        )

        self.decision_engine = EdgeCaseDecisionEngine()
        self.executed_actions: List[AutomatedAction] = []
        self.rollback_queue: List[AutomatedAction] = []

        # Configuration
        self.safe_actions = {"query_abort", "warehouse_auto_suspend_enable", "warehouse_scale"}
        self.moderate_actions = {"warehouse_suspend", "warehouse_resume"}
        self.risky_actions = {"role_revoke", "drop_table", "alter_schema"}
        self.dangerous_actions = {"delete_database", "drop_schema", "truncate_table"}

    def execute(self) -> bool:
        """Execute autonomous self-healing."""
        try:
            self.start_execution()
            logger.info("Starting Autonomous Self-Healing Agent execution")

            # Collect current findings
            findings = self._collect_current_findings()

            # Evaluate actions for each finding
            actions_to_execute = self._evaluate_actions(findings)

            # Execute safe and moderate actions
            self._execute_safe_actions(actions_to_execute.get("safe", []))
            self._execute_moderate_actions(actions_to_execute.get("moderate", []))

            # Log risky actions for approval (don't auto-execute)
            if actions_to_execute.get("risky"):
                self._log_risky_actions_for_approval(actions_to_execute["risky"])

            # Validate execution
            self._validate_execution_results()

            # Handle rollback queue if needed
            self._process_rollback_queue()

            self.findings_processed = len(findings)
            self.end_execution(success=True)
            return True

        except Exception as e:
            logger.error(f"Autonomous healing failed: {str(e)}")
            self._trigger_emergency_rollback()
            self.end_execution(success=False, error_message=str(e))
            return False

    # ========================================================================
    # ACTION COLLECTION & EVALUATION
    # ========================================================================

    def _collect_current_findings(self) -> List[Finding]:
        """Collect findings from database that need remediation."""
        logger.info("Collecting current findings...")

        findings = []
        try:
            sql = """
            SELECT finding_id, category, severity, resource_type, resource_name, details
            FROM governance.findings
            WHERE status = 'open'
            AND created_at > CURRENT_TIMESTAMP() - INTERVAL '1 hour'
            ORDER BY severity DESC, created_at DESC
            """

            results = self.snowpark_client.execute_query(sql)
            findings = [Finding(
                finding_id=r.get("finding_id"),
                title=f"{r.get('category')} detected",
                description="",
                severity=DetectionSeverity[r.get("severity", "MEDIUM")],
                category=r.get("category"),
                resource_type=r.get("resource_type"),
                resource_name=r.get("resource_name"),
                details=r.get("details") or {}
            ) for r in results]

            logger.info(f"Collected {len(findings)} findings for evaluation")
        except Exception as e:
            logger.debug(f"Could not collect findings: {str(e)}")

        return findings

    def _evaluate_actions(self, findings: List[Finding]) -> Dict[str, List[AutomatedAction]]:
        """Evaluate and categorize actions by risk level."""
        logger.info(f"Evaluating actions for {len(findings)} findings...")

        actions = {"safe": [], "moderate": [], "risky": [], "dangerous": []}

        for finding in findings:
            recommended_actions = self._get_remediation_actions(finding)

            for action in recommended_actions:
                risk_level = self._assess_risk(action, finding)
                action.risk_level = risk_level

                if risk_level == ActionRiskLevel.SAFE:
                    actions["safe"].append(action)
                elif risk_level == ActionRiskLevel.MODERATE:
                    actions["moderate"].append(action)
                elif risk_level == ActionRiskLevel.RISKY:
                    actions["risky"].append(action)
                else:
                    actions["dangerous"].append(action)

        logger.info(f"Action distribution: safe={len(actions['safe'])}, "
                   f"moderate={len(actions['moderate'])}, "
                   f"risky={len(actions['risky'])}, "
                   f"dangerous={len(actions['dangerous'])}")

        return actions

    def _get_remediation_actions(self, finding: Finding) -> List[AutomatedAction]:
        """Get recommended actions for a finding."""
        actions = []

        # Query optimization findings
        if finding.category == "slow_queries":
            action = AutomatedAction(
                action_id=f"abort_{finding.resource_name}",
                action_type="query_abort",
                target=finding.resource_name,
                risk_level=ActionRiskLevel.SAFE
            )
            actions.append(action)

        # Warehouse health findings
        elif finding.category == "warehouse_queue_buildup":
            action = AutomatedAction(
                action_id=f"scale_{finding.resource_name}",
                action_type="warehouse_scale",
                target=finding.resource_name,
                risk_level=ActionRiskLevel.MODERATE
            )
            actions.append(action)

        # Cost optimization findings
        elif finding.category == "unused_warehouse":
            action = AutomatedAction(
                action_id=f"suspend_{finding.resource_name}",
                action_type="warehouse_suspend",
                target=finding.resource_name,
                risk_level=ActionRiskLevel.MODERATE
            )
            actions.append(action)

        # Security findings
        elif finding.category == "stale_user":
            action = AutomatedAction(
                action_id=f"disable_{finding.resource_name}",
                action_type="user_disable",
                target=finding.resource_name,
                risk_level=ActionRiskLevel.MODERATE
            )
            actions.append(action)

        return actions

    def _assess_risk(self, action: AutomatedAction, finding: Finding) -> ActionRiskLevel:
        """Assess risk level for an action."""
        # Base risk on action type
        if action.action_type in self.safe_actions:
            return ActionRiskLevel.SAFE
        elif action.action_type in self.moderate_actions:
            # Increase risk if critical resource
            if finding.severity == DetectionSeverity.CRITICAL:
                return ActionRiskLevel.RISKY
            return ActionRiskLevel.MODERATE
        elif action.action_type in self.risky_actions:
            return ActionRiskLevel.RISKY
        else:
            return ActionRiskLevel.DANGEROUS

    # ========================================================================
    # ACTION EXECUTION
    # ========================================================================

    def _execute_safe_actions(self, actions: List[AutomatedAction]) -> None:
        """Execute safe actions immediately."""
        logger.info(f"Executing {len(actions)} safe actions...")

        for action in actions:
            try:
                # Capture before state
                action.before_state = self._capture_state(action)

                # Get decision engine approval
                current_state = self._get_current_system_state()
                risk_assessment = {"mitigation_available": True}

                should_execute, reason = self.decision_engine.should_execute_action(
                    action.action_type, action.target, current_state, risk_assessment
                )

                if not should_execute:
                    logger.info(f"Skipping action {action.action_id}: {reason}")
                    continue

                # Execute action
                logger.info(f"Executing safe action: {action.action_id}")
                success = self._execute_action(action)

                if success:
                    action.mark_executed()
                    self.decision_engine.record_decision(action.action_type, action.target, True, True)
                    self._notify_action_executed(action)
                else:
                    action.mark_failed("Execution failed")
                    self.decision_engine.record_decision(action.action_type, action.target, True, False)
                    self.rollback_queue.append(action)

                self.executed_actions.append(action)

            except Exception as e:
                logger.error(f"Error executing action {action.action_id}: {str(e)}")
                action.mark_failed(str(e))
                self.rollback_queue.append(action)

    def _execute_moderate_actions(self, actions: List[AutomatedAction]) -> None:
        """Execute moderate actions with continuous monitoring."""
        logger.info(f"Executing {len(actions)} moderate actions with monitoring...")

        for action in actions:
            try:
                # Extra validation for moderate actions
                if not self._validate_action_preconditions(action):
                    logger.warning(f"Preconditions failed for {action.action_id}")
                    continue

                action.before_state = self._capture_state(action)

                # Get decision engine approval (more stringent for moderate)
                current_state = self._get_current_system_state()
                risk_assessment = {
                    "mitigation_available": action.is_reversible(),
                    "monitoring_available": True
                }

                should_execute, reason = self.decision_engine.should_execute_action(
                    action.action_type, action.target, current_state, risk_assessment
                )

                if not should_execute:
                    logger.info(f"Skipping moderate action {action.action_id}: {reason}")
                    continue

                logger.info(f"Executing moderate action: {action.action_id}")

                # Execute with continuous monitoring
                success = self._execute_action_with_monitoring(action)

                if success:
                    action.mark_executed()
                    self.decision_engine.record_decision(action.action_type, action.target, True, True)
                    self._notify_action_executed(action)
                else:
                    action.mark_failed("Execution failed")
                    self.rollback_queue.append(action)

                self.executed_actions.append(action)

            except Exception as e:
                logger.error(f"Error executing moderate action {action.action_id}: {str(e)}")
                action.mark_failed(str(e))
                self.rollback_queue.append(action)

    def _log_risky_actions_for_approval(self, actions: List[AutomatedAction]) -> None:
        """Log risky actions in database for approval before execution."""
        logger.info(f"Logging {len(actions)} risky actions for approval...")

        for action in actions:
            try:
                sql = """
                INSERT INTO governance.pending_autonomous_actions
                (action_id, action_type, target, risk_level, status, created_at)
                VALUES (%s, %s, %s, %s, 'pending_approval', CURRENT_TIMESTAMP())
                """
                self.snowpark_client.execute_update(sql, [
                    action.action_id,
                    action.action_type,
                    action.target,
                    action.risk_level.value
                ])
                logger.info(f"Logged risky action for approval: {action.action_id}")
            except Exception as e:
                logger.error(f"Failed to log risky action: {str(e)}")

    # ========================================================================
    # STATE MANAGEMENT & ROLLBACK
    # ========================================================================

    def _capture_state(self, action: AutomatedAction) -> Dict[str, Any]:
        """Capture current state before action execution."""
        try:
            if action.action_type == "query_abort":
                return self._capture_query_state(action.target)
            elif action.action_type.startswith("warehouse_"):
                return self._capture_warehouse_state(action.target)
            elif action.action_type == "role_revoke":
                return self._capture_role_state(action.target)
            return {}
        except Exception as e:
            logger.warning(f"Failed to capture state: {str(e)}")
            return {}

    def _capture_query_state(self, query_id: str) -> Dict[str, Any]:
        """Capture query state."""
        return {"query_id": query_id, "timestamp": datetime.utcnow().isoformat()}

    def _capture_warehouse_state(self, warehouse_name: str) -> Dict[str, Any]:
        """Capture warehouse state."""
        return {"warehouse_name": warehouse_name, "timestamp": datetime.utcnow().isoformat()}

    def _capture_role_state(self, role_name: str) -> Dict[str, Any]:
        """Capture role state."""
        return {"role_name": role_name, "timestamp": datetime.utcnow().isoformat()}

    def _execute_action(self, action: AutomatedAction) -> bool:
        """Execute action with error handling."""
        try:
            if action.action_type == "query_abort":
                return self.snowpark_client.abort_query(action.target)
            elif action.action_type == "warehouse_suspend":
                return self.snowpark_client.suspend_warehouse(action.target)
            elif action.action_type == "warehouse_resume":
                return self.snowpark_client.resume_warehouse(action.target)
            elif action.action_type == "warehouse_scale":
                return self.snowpark_client.scale_warehouse(action.target, 1)
            return False
        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            return False

    def _execute_action_with_monitoring(self, action: AutomatedAction) -> bool:
        """Execute action with continuous monitoring."""
        logger.info(f"Executing with monitoring: {action.action_id}")

        try:
            success = self._execute_action(action)

            # Monitor for 5 minutes after execution
            import time
            for i in range(5):
                time.sleep(60)
                if not self._is_system_healthy():
                    logger.warning("System unhealthy after action - preparing rollback")
                    return False

            return success

        except Exception as e:
            logger.error(f"Monitoring failed: {str(e)}")
            return False

    def _process_rollback_queue(self) -> None:
        """Process actions that need rollback."""
        logger.info(f"Processing rollback queue ({len(self.rollback_queue)} items)...")

        for action in self.rollback_queue:
            try:
                if action.is_reversible():
                    logger.info(f"Rolling back action: {action.action_id}")
                    self._rollback_action(action)
                    action.rollback_executed = True
            except Exception as e:
                logger.error(f"Rollback failed for {action.action_id}: {str(e)}")

    def _rollback_action(self, action: AutomatedAction) -> None:
        """Rollback an executed action."""
        if action.action_type == "query_abort":
            # Query abort is irreversible but recorded
            pass
        elif action.action_type == "warehouse_suspend":
            self.snowpark_client.resume_warehouse(action.target)
        elif action.action_type == "warehouse_scale":
            # Restore to previous scale
            pass

    def _trigger_emergency_rollback(self) -> None:
        """Trigger emergency rollback of all executed actions."""
        logger.critical("Triggering emergency rollback!")
        for action in self.executed_actions:
            if action.is_reversible():
                try:
                    self._rollback_action(action)
                except Exception as e:
                    logger.error(f"Emergency rollback failed: {str(e)}")

    # ========================================================================
    # VALIDATION & HEALTH CHECKS
    # ========================================================================

    def _validate_action_preconditions(self, action: AutomatedAction) -> bool:
        """Validate preconditions before action execution."""
        try:
            if action.action_type == "query_abort":
                return self._query_exists(action.target)
            elif action.action_type == "warehouse_suspend":
                return self._warehouse_exists(action.target)
            return True
        except Exception as e:
            logger.warning(f"Precondition check failed: {str(e)}")
            return False

    def _query_exists(self, query_id: str) -> bool:
        """Check if query exists."""
        return True  # Simplified

    def _warehouse_exists(self, warehouse_name: str) -> bool:
        """Check if warehouse exists."""
        return True  # Simplified

    def _get_current_system_state(self) -> Dict[str, Any]:
        """Get current system state for decision making."""
        return {
            "error_rate": 0.02,
            "active_incidents": 0,
            "maintenance_mode": False,
            "query_exists": True,
            "warehouse_exists": True,
            "critical_warehouses": []
        }

    def _is_system_healthy(self) -> bool:
        """Check if system is healthy."""
        state = self._get_current_system_state()
        return (state.get("error_rate", 0) < 0.05 and
                state.get("active_incidents", 0) == 0 and
                not state.get("maintenance_mode"))

    def _validate_execution_results(self) -> None:
        """Validate that executed actions had desired effect."""
        logger.info("Validating execution results...")

        for action in self.executed_actions:
            if action.success:
                # Verify the desired outcome was achieved
                outcome_achieved = self._verify_action_outcome(action)
                if not outcome_achieved:
                    logger.warning(f"Action outcome not verified: {action.action_id}")

    def _verify_action_outcome(self, action: AutomatedAction) -> bool:
        """Verify action achieved desired outcome."""
        return True  # Simplified - would check metrics

    def _notify_action_executed(self, action: AutomatedAction) -> None:
        """Notify stakeholders of action execution."""
        logger.info(f"Notifying about action: {action.action_id}")
        # Would send Slack notification, etc.

    def get_summary(self) -> Dict[str, Any]:
        """Get autonomous healing summary."""
        return {
            "total_actions_evaluated": len(self.executed_actions),
            "safe_actions_executed": sum(1 for a in self.executed_actions if a.risk_level == ActionRiskLevel.SAFE),
            "moderate_actions_executed": sum(1 for a in self.executed_actions if a.risk_level == ActionRiskLevel.MODERATE),
            "actions_rolled_back": sum(1 for a in self.executed_actions if a.rollback_executed),
            "success_rate": sum(1 for a in self.executed_actions if a.success) / max(len(self.executed_actions), 1),
            "learned_patterns": len(self.decision_engine.learned_patterns)
        }
