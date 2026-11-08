"""
Policy as Code DSL - Phase 5
YAML/JSON-based policy language for business users to define governance rules.
Includes policy validation, versioning, testing, and templating.
"""

import logging
import json
import yaml
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    """Actions that policies can enforce."""
    ALERT = "alert"
    AUTO_FIX = "auto_fix"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"
    QUARANTINE = "quarantine"


class PolicyScope(Enum):
    """Scope of policy enforcement."""
    ACCOUNT = "account"
    WAREHOUSE = "warehouse"
    USER = "user"
    ROLE = "role"
    DATABASE = "database"
    SCHEMA = "schema"


@dataclass
class PolicyCondition:
    """Represents a single policy condition."""
    metric: str  # e.g., "query_execution_time", "monthly_spend"
    operator: str  # "gt", "lt", "eq", "gte", "lte", "contains"
    threshold: Any
    lookback_period: str = "24h"  # e.g., "24h", "7d", "30d"

    def evaluate(self, current_value: Any) -> bool:
        """Evaluate if condition is met."""
        if self.operator == "gt":
            return current_value > self.threshold
        elif self.operator == "lt":
            return current_value < self.threshold
        elif self.operator == "eq":
            return current_value == self.threshold
        elif self.operator == "gte":
            return current_value >= self.threshold
        elif self.operator == "lte":
            return current_value <= self.threshold
        elif self.operator == "contains":
            return self.threshold in str(current_value)
        elif self.operator == "not_contains":
            return self.threshold not in str(current_value)
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric": self.metric,
            "operator": self.operator,
            "threshold": self.threshold,
            "lookback_period": self.lookback_period
        }


@dataclass
class PolicyRule:
    """Represents a policy rule with conditions and actions."""
    rule_name: str
    conditions: List[PolicyCondition]  # All conditions must be true (AND logic)
    action: PolicyAction
    severity: str  # "critical", "high", "medium", "low"
    description: str = ""
    exceptions: List[str] = field(default_factory=list)  # Exceptions to rule

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if context matches all conditions."""
        for condition in self.conditions:
            metric_value = context.get(condition.metric)
            if metric_value is None:
                return False
            if not condition.evaluate(metric_value):
                return False
        return True

    def should_apply(self, resource_name: str) -> bool:
        """Check if rule applies to resource (accounting for exceptions)."""
        for exception in self.exceptions:
            if exception.lower() in resource_name.lower():
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "conditions": [c.to_dict() for c in self.conditions],
            "action": self.action.value,
            "severity": self.severity,
            "description": self.description,
            "exceptions": self.exceptions
        }


@dataclass
class GovernancePolicy:
    """Represents a complete governance policy."""
    policy_id: str
    policy_name: str
    scope: PolicyScope
    scope_target: str  # e.g., "prod_warehouse", "analytics_role"
    rules: List[PolicyRule]
    version: str = "1.0.0"
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    environment: str = "prod"  # prod, staging, dev
    owner: str = ""
    tags: List[str] = field(default_factory=list)

    def add_rule(self, rule: PolicyRule) -> None:
        """Add rule to policy."""
        self.rules.append(rule)
        self.updated_at = datetime.utcnow()

    def evaluate(self, context: Dict[str, Any]) -> List[Tuple[PolicyRule, str]]:
        """
        Evaluate context against all rules.

        Returns:
            List of (matched_rule, action) tuples
        """
        matched_rules = []

        for rule in self.rules:
            if rule.matches(context):
                matched_rules.append((rule, rule.action.value))

        return matched_rules

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "scope": self.scope.value,
            "scope_target": self.scope_target,
            "version": self.version,
            "enabled": self.enabled,
            "environment": self.environment,
            "owner": self.owner,
            "tags": self.tags,
            "rules": [r.to_dict() for r in self.rules]
        }

    def to_yaml(self) -> str:
        """Convert to YAML format."""
        return yaml.dump(self.to_dict(), default_flow_style=False)

    def to_json(self) -> str:
        """Convert to JSON format."""
        return json.dumps(self.to_dict(), indent=2)


class PolicyParser:
    """Parse policies from YAML/JSON formats."""

    @staticmethod
    def parse_yaml(yaml_content: str) -> GovernancePolicy:
        """Parse policy from YAML string."""
        data = yaml.safe_load(yaml_content)
        return PolicyParser._dict_to_policy(data)

    @staticmethod
    def parse_json(json_content: str) -> GovernancePolicy:
        """Parse policy from JSON string."""
        data = json.loads(json_content)
        return PolicyParser._dict_to_policy(data)

    @staticmethod
    def _dict_to_policy(data: Dict[str, Any]) -> GovernancePolicy:
        """Convert dictionary to GovernancePolicy object."""
        rules = []
        for rule_data in data.get("rules", []):
            conditions = []
            for cond_data in rule_data.get("conditions", []):
                condition = PolicyCondition(
                    metric=cond_data["metric"],
                    operator=cond_data["operator"],
                    threshold=cond_data["threshold"],
                    lookback_period=cond_data.get("lookback_period", "24h")
                )
                conditions.append(condition)

            rule = PolicyRule(
                rule_name=rule_data["rule_name"],
                conditions=conditions,
                action=PolicyAction(rule_data["action"]),
                severity=rule_data.get("severity", "medium"),
                description=rule_data.get("description", ""),
                exceptions=rule_data.get("exceptions", [])
            )
            rules.append(rule)

        policy = GovernancePolicy(
            policy_id=data.get("policy_id", ""),
            policy_name=data.get("policy_name", ""),
            scope=PolicyScope(data.get("scope", "account")),
            scope_target=data.get("scope_target", ""),
            rules=rules,
            version=data.get("version", "1.0.0"),
            enabled=data.get("enabled", True),
            environment=data.get("environment", "prod"),
            owner=data.get("owner", ""),
            tags=data.get("tags", [])
        )

        return policy


class PolicyValidator:
    """Validates policies for correctness and safety."""

    @staticmethod
    def validate(policy: GovernancePolicy) -> Tuple[bool, List[str]]:
        """
        Validate policy.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if not policy.policy_id:
            errors.append("Missing policy_id")
        if not policy.policy_name:
            errors.append("Missing policy_name")
        if not policy.scope_target:
            errors.append("Missing scope_target")

        # Check rules
        if not policy.rules:
            errors.append("Policy must have at least one rule")

        for i, rule in enumerate(policy.rules):
            if not rule.rule_name:
                errors.append(f"Rule {i} missing rule_name")
            if not rule.conditions:
                errors.append(f"Rule {i} must have at least one condition")
            for j, condition in enumerate(rule.conditions):
                if not condition.metric:
                    errors.append(f"Rule {i}, Condition {j} missing metric")

        return len(errors) == 0, errors

    @staticmethod
    def check_conflicts(policies: List[GovernancePolicy]) -> List[str]:
        """Check for conflicts between multiple policies."""
        conflicts = []

        # Check for policies with same scope targeting same resource
        by_scope = {}
        for policy in policies:
            key = f"{policy.scope.value}:{policy.scope_target}"
            if key not in by_scope:
                by_scope[key] = []
            by_scope[key].append(policy)

        for key, policies_list in by_scope.items():
            if len(policies_list) > 1:
                # Conflicting policies
                policy_names = [p.policy_name for p in policies_list]
                conflicts.append(f"Multiple policies target {key}: {', '.join(policy_names)}")

        return conflicts


class PolicyTemplateLibrary:
    """Pre-built policy templates for common use cases."""

    @staticmethod
    def query_timeout_policy(warehouse_name: str = "COMPUTE_WH") -> GovernancePolicy:
        """Template: Enforce query timeout limits."""
        condition = PolicyCondition(
            metric="query_execution_time",
            operator="gt",
            threshold=3600  # 1 hour
        )

        rule = PolicyRule(
            rule_name="abort_long_running_query",
            conditions=[condition],
            action=PolicyAction.AUTO_FIX,
            severity="high",
            description="Automatically abort queries exceeding 1 hour",
            exceptions=["dbt_run", "maintenance_window"]
        )

        policy = GovernancePolicy(
            policy_id="query_timeout_001",
            policy_name="Query Timeout Policy",
            scope=PolicyScope.WAREHOUSE,
            scope_target=warehouse_name,
            rules=[rule],
            owner="data-engineering"
        )

        return policy

    @staticmethod
    def cost_control_policy(budget_limit: float = 10000) -> GovernancePolicy:
        """Template: Enforce budget limits."""
        condition = PolicyCondition(
            metric="monthly_spend",
            operator="gte",
            threshold=budget_limit
        )

        rule = PolicyRule(
            rule_name="budget_breach_alert",
            conditions=[condition],
            action=PolicyAction.REQUIRE_APPROVAL,
            severity="high",
            description=f"Require approval for spend >= ${budget_limit}"
        )

        policy = GovernancePolicy(
            policy_id="budget_control_001",
            policy_name="Cost Control Policy",
            scope=PolicyScope.ACCOUNT,
            scope_target="default",
            rules=[rule],
            owner="finance"
        )

        return policy

    @staticmethod
    def security_policy() -> GovernancePolicy:
        """Template: Enforce security policies."""
        conditions = [
            PolicyCondition(
                metric="user_activity",
                operator="eq",
                threshold="after_hours"
            )
        ]

        rule = PolicyRule(
            rule_name="after_hours_access_alert",
            conditions=conditions,
            action=PolicyAction.ALERT,
            severity="medium",
            description="Alert on after-hours data access"
        )

        policy = GovernancePolicy(
            policy_id="security_001",
            policy_name="Security Policy",
            scope=PolicyScope.ACCOUNT,
            scope_target="default",
            rules=[rule],
            owner="security-team"
        )

        return policy

    @staticmethod
    def warehouse_efficiency_policy() -> GovernancePolicy:
        """Template: Enforce warehouse efficiency."""
        condition = PolicyCondition(
            metric="warehouse_utilization",
            operator="lt",
            threshold=10  # 10%
        )

        rule = PolicyRule(
            rule_name="suspend_underutilized",
            conditions=[condition],
            action=PolicyAction.AUTO_FIX,
            severity="low",
            description="Auto-suspend warehouses with <10% utilization",
            exceptions=["prod_warehouse", "critical"]
        )

        policy = GovernancePolicy(
            policy_id="efficiency_001",
            policy_name="Warehouse Efficiency Policy",
            scope=PolicyScope.ACCOUNT,
            scope_target="default",
            rules=[rule],
            owner="devops"
        )

        return policy


class PolicyEngine:
    """
    Policy Engine - Evaluates and enforces policies.
    Central execution engine for all governance policies.
    """

    def __init__(self):
        self.policies: Dict[str, GovernancePolicy] = {}
        self.policy_history: List[Dict[str, Any]] = []

    def register_policy(self, policy: GovernancePolicy) -> bool:
        """Register a policy."""
        is_valid, errors = PolicyValidator.validate(policy)

        if not is_valid:
            logger.error(f"Policy validation failed: {errors}")
            return False

        self.policies[policy.policy_id] = policy
        logger.info(f"Registered policy: {policy.policy_name}")
        return True

    def evaluate_context(self, context: Dict[str, Any]) -> List[Tuple[GovernancePolicy, PolicyRule, str]]:
        """
        Evaluate context against all registered policies.

        Returns:
            List of (policy, matched_rule, action) tuples
        """
        matches = []

        for policy in self.policies.values():
            if not policy.enabled:
                continue

            matched_rules = policy.evaluate(context)
            for rule, action in matched_rules:
                matches.append((policy, rule, action))

                # Record in history
                self.policy_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "policy_id": policy.policy_id,
                    "rule_name": rule.rule_name,
                    "action": action,
                    "context": context
                })

        return matches

    def get_applicable_policies(
        self,
        scope: PolicyScope,
        scope_target: str
    ) -> List[GovernancePolicy]:
        """Get policies applicable to a specific scope."""
        return [
            p for p in self.policies.values()
            if p.scope == scope and p.scope_target == scope_target and p.enabled
        ]


# Example YAML policy format:
EXAMPLE_POLICY_YAML = """
policy_id: query_timeout_prod
policy_name: Production Query Timeout
scope: warehouse
scope_target: PROD_COMPUTE_WH
version: 1.0.0
enabled: true
environment: prod
owner: data-engineering
tags:
  - performance
  - production

rules:
  - rule_name: abort_long_running_queries
    description: Abort queries running longer than 1 hour
    action: auto_fix
    severity: high
    conditions:
      - metric: query_execution_time
        operator: gt
        threshold: 3600
        lookback_period: 1m
    exceptions:
      - dbt_run
      - maintenance_job

  - rule_name: alert_on_extreme_queries
    description: Alert when query exceeds 4 hours
    action: alert
    severity: critical
    conditions:
      - metric: query_execution_time
        operator: gt
        threshold: 14400
    exceptions:
      - backup_job
"""

# Example JSON policy format:
EXAMPLE_POLICY_JSON = """
{
  "policy_id": "cost_control_prod",
  "policy_name": "Production Cost Control",
  "scope": "account",
  "scope_target": "default",
  "version": "1.0.0",
  "enabled": true,
  "environment": "prod",
  "owner": "finance",
  "tags": ["cost", "budget"],
  "rules": [
    {
      "rule_name": "daily_cost_alert",
      "description": "Alert when daily spend exceeds $500",
      "action": "alert",
      "severity": "high",
      "conditions": [
        {
          "metric": "daily_spend",
          "operator": "gt",
          "threshold": 500,
          "lookback_period": "24h"
        }
      ],
      "exceptions": []
    },
    {
      "rule_name": "monthly_budget_enforcement",
      "description": "Require approval for monthly spend over budget",
      "action": "require_approval",
      "severity": "high",
      "conditions": [
        {
          "metric": "monthly_spend",
          "operator": "gte",
          "threshold": 10000,
          "lookback_period": "30d"
        }
      ],
      "exceptions": []
    }
  ]
}
"""
