"""
Agent Orchestrator - Main entry point for running governance agents.
Coordinates execution of all agents and manages workflows.
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.snowflake.snowpark_client import SnowparkClient, SnowflakeConfig
from src.orchestration.approval_workflow_manager import ApprovalWorkflowManager
from src.agents.security_compliance_agent import SecurityComplianceAgent
from src.agents.performance_optimization_agent import PerformanceOptimizationAgent
from src.agents.cost_optimization_agent import CostOptimizationAgent
from src.agents.spillage_prevention_agent import DataSpillagePrevention Agent
from src.agents.warehouse_health_agent import WarehouseHealthAgent


logger = logging.getLogger(__name__)


class GovernanceAgentOrchestrator:
    """
    Orchestrator for Snowflake Governance Agents.
    Coordinates execution of all governance agents in sequence or parallel.
    """

    def __init__(self, snowflake_config: SnowflakeConfig, notification_manager=None):
        """
        Initialize orchestrator.

        Args:
            snowflake_config: Snowflake connection configuration
            notification_manager: Optional notification service
        """
        self.snowflake_config = snowflake_config
        self.notification_manager = notification_manager

        # Initialize Snowflake client
        self.snowpark_client = SnowparkClient(snowflake_config)

        # Initialize approval workflow manager
        self.approval_manager = ApprovalWorkflowManager(
            self.snowpark_client,
            notification_manager
        )

        # Initialize all agents
        self.agents = {
            "security": SecurityComplianceAgent(self.snowpark_client, notification_manager),
            "performance": PerformanceOptimizationAgent(self.snowpark_client, notification_manager),
            "cost": CostOptimizationAgent(self.snowpark_client, notification_manager),
            "spillage": DataSpillagePrevention Agent(self.snowpark_client, notification_manager),
            "health": WarehouseHealthAgent(self.snowpark_client, notification_manager)
        }

        # Execution state
        self.execution_start = None
        self.execution_end = None
        self.execution_results = {}

        logger.info("Orchestrator initialized with 5 governance agents")

    def execute_all_agents(self) -> Dict[str, Any]:
        """
        Execute all governance agents sequentially.

        Returns:
            Dictionary with execution results from all agents
        """
        logger.info("=" * 80)
        logger.info("STARTING GOVERNANCE AGENT EXECUTION")
        logger.info("=" * 80)

        self.execution_start = datetime.utcnow()
        self.execution_results = {}

        # Run agents in sequence
        agent_order = ["security", "performance", "cost", "spillage", "health"]

        for agent_name in agent_order:
            logger.info(f"\n--- Executing {agent_name.upper()} Agent ---")
            agent = self.agents[agent_name]

            try:
                success = agent.execute()
                self.execution_results[agent_name] = {
                    "success": success,
                    "summary": agent.get_execution_summary(),
                    "findings_count": len(agent.current_findings),
                    "recommendations_count": len(agent.current_recommendations)
                }

                if success:
                    logger.info(f"✓ {agent_name} agent completed")
                    logger.info(f"  - Findings: {len(agent.current_findings)}")
                    logger.info(f"  - Recommendations: {len(agent.current_recommendations)}")
                else:
                    logger.error(f"✗ {agent_name} agent failed")

            except Exception as e:
                logger.error(f"Unexpected error in {agent_name} agent: {str(e)}")
                self.execution_results[agent_name] = {
                    "success": False,
                    "error": str(e)
                }

        # Check SLA and escalate approvals
        logger.info("\n--- Checking Approval SLAs ---")
        escalated = self.approval_manager.check_sla_and_escalate()
        if escalated:
            logger.warning(f"Escalated {len(escalated)} approval requests")

        self.execution_end = datetime.utcnow()
        duration = (self.execution_end - self.execution_start).total_seconds()

        logger.info("\n" + "=" * 80)
        logger.info("EXECUTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Approval stats: {self.approval_manager.get_statistics()}")
        logger.info("=" * 80 + "\n")

        return self._build_execution_report()

    def execute_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Execute a specific agent.

        Args:
            agent_name: Name of agent to execute ('security', 'performance', 'cost', 'spillage', 'health')

        Returns:
            Execution summary
        """
        if agent_name not in self.agents:
            logger.error(f"Unknown agent: {agent_name}")
            return {"error": f"Unknown agent: {agent_name}"}

        logger.info(f"Executing {agent_name} agent...")
        agent = self.agents[agent_name]

        try:
            success = agent.execute()
            return {
                "agent": agent_name,
                "success": success,
                "summary": agent.get_execution_summary(),
                "findings": [f.to_dict() for f in agent.current_findings],
                "recommendations": [r.to_dict() for r in agent.current_recommendations]
            }
        except Exception as e:
            logger.error(f"Failed to execute {agent_name}: {str(e)}")
            return {
                "agent": agent_name,
                "success": False,
                "error": str(e)
            }

    def get_pending_approvals(self, approver_email: str) -> List[Dict[str, Any]]:
        """Get pending approval requests."""
        pending = self.approval_manager.get_pending_requests(approver_email)
        return [r.to_dict() for r in pending]

    def approve_request(
        self,
        request_id: str,
        approver_email: str,
        comments: str = ""
    ) -> Dict[str, Any]:
        """Approve an approval request."""
        success = self.approval_manager.approve_request(request_id, approver_email, comments)
        request = self.approval_manager.get_request(request_id)

        return {
            "request_id": request_id,
            "success": success,
            "request": request.to_dict() if request else None
        }

    def reject_request(
        self,
        request_id: str,
        approver_email: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Reject an approval request."""
        success = self.approval_manager.reject_request(request_id, approver_email, reason)
        request = self.approval_manager.get_request(request_id)

        return {
            "request_id": request_id,
            "success": success,
            "request": request.to_dict() if request else None
        }

    def get_agent_status(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of agents."""
        if agent_name:
            if agent_name not in self.agents:
                return {"error": f"Unknown agent: {agent_name}"}
            agent = self.agents[agent_name]
            return {agent_name: agent.get_execution_summary()}
        else:
            return {
                name: agent.get_execution_summary()
                for name, agent in self.agents.items()
            }

    def get_findings_summary(self) -> Dict[str, Any]:
        """Get summary of all findings."""
        summary = {
            "total_findings": 0,
            "by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            },
            "by_agent": {}
        }

        for agent_name, agent in self.agents.items():
            findings = agent.current_findings
            summary["total_findings"] += len(findings)
            summary["by_agent"][agent_name] = {
                "count": len(findings),
                "by_severity": {}
            }

            for finding in findings:
                severity = finding.severity.value
                summary["by_severity"][severity] += 1
                if severity not in summary["by_agent"][agent_name]["by_severity"]:
                    summary["by_agent"][agent_name]["by_severity"][severity] = 0
                summary["by_agent"][agent_name]["by_severity"][severity] += 1

        return summary

    def get_recommendations_summary(self) -> Dict[str, Any]:
        """Get summary of all recommendations."""
        summary = {
            "total_recommendations": 0,
            "by_agent": {}
        }

        for agent_name, agent in self.agents.items():
            recs = agent.current_recommendations
            summary["total_recommendations"] += len(recs)
            summary["by_agent"][agent_name] = {
                "count": len(recs),
                "by_impact": {
                    "low": 0,
                    "medium": 0,
                    "high": 0
                }
            }

            for rec in recs:
                impact = rec.impact.lower()
                if impact in summary["by_agent"][agent_name]["by_impact"]:
                    summary["by_agent"][agent_name]["by_impact"][impact] += 1

        return summary

    def _build_execution_report(self) -> Dict[str, Any]:
        """Build comprehensive execution report."""
        return {
            "execution_timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": (self.execution_end - self.execution_start).total_seconds() if self.execution_end else None,
            "agents": self.execution_results,
            "findings_summary": self.get_findings_summary(),
            "recommendations_summary": self.get_recommendations_summary(),
            "approval_stats": self.approval_manager.get_statistics()
        }

    def close(self):
        """Close orchestrator and cleanup resources."""
        if self.snowpark_client:
            self.snowpark_client.close()
        logger.info("Orchestrator closed")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Example main execution."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create Snowflake config
    config = SnowflakeConfig(
        account="your_account",
        user="your_user",
        password="your_password",
        warehouse="COMPUTE_WH",
        database="GOVERNANCE_DB",
        schema="governance"
    )

    try:
        # Create orchestrator
        orchestrator = GovernanceAgentOrchestrator(config)

        # Execute all agents
        report = orchestrator.execute_all_agents()

        # Print report
        print("\n" + "=" * 80)
        print("EXECUTION REPORT")
        print("=" * 80)
        print(json.dumps(report, indent=2))
        print("=" * 80)

    except Exception as e:
        logger.error(f"Orchestrator failed: {str(e)}")
        raise

    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
