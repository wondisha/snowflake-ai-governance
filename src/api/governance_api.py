"""
REST API Server - FastAPI application for governance agent system.
Exposes all capabilities via HTTP endpoints for integrations and dashboards.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthCredential
from pydantic import BaseModel
import jwt


logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"


# ============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================================

class FindingResponse(BaseModel):
    finding_id: str
    title: str
    severity: str
    category: str
    resource_name: str
    resource_type: str
    detected_at: str
    recommendation: Optional[str] = None


class RecommendationResponse(BaseModel):
    recommendation_id: str
    title: str
    description: str
    action_type: str
    resource_name: str
    impact: str
    implementation_steps: List[str]


class ApprovalRequestResponse(BaseModel):
    request_id: str
    request_type: str
    title: str
    priority: str
    status: str
    created_at: str
    expires_at: str
    approver_email: str


class ApprovalActionRequest(BaseModel):
    request_id: str
    approver_email: str
    action: str  # 'approve' or 'reject'
    comments: str = ""


class ExecutionReportResponse(BaseModel):
    execution_timestamp: str
    duration_seconds: float
    findings_summary: Dict[str, Any]
    recommendations_summary: Dict[str, Any]
    approval_stats: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    agents: Dict[str, Any]
    database: str


class SlowQueryResponse(BaseModel):
    query_id: str
    execution_seconds: float
    user_name: str
    warehouse_name: str
    data_scanned_gb: float


class WarehouseMetricsResponse(BaseModel):
    warehouse_name: str
    state: str
    running_queries: int
    queued_queries: int
    size: Optional[str] = None


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

class GovernanceAPI:
    """Governance Agent REST API Server."""

    def __init__(self, orchestrator, slack_bot=None):
        """
        Initialize API server.

        Args:
            orchestrator: GovernanceAgentOrchestrator instance
            slack_bot: Optional SlackBotHandler instance
        """
        self.orchestrator = orchestrator
        self.slack_bot = slack_bot

        # Create FastAPI app
        self.app = FastAPI(
            title="Snowflake Governance API",
            description="REST API for governance agent system",
            version="1.0.0"
        )

        # Setup security
        self.security = HTTPBearer()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all API routes."""

        # ====================================================================
        # HEALTH & STATUS ENDPOINTS
        # ====================================================================

        @self.app.get("/health", response_model=HealthCheckResponse)
        async def health_check():
            """Get system health status."""
            agent_status = self.orchestrator.get_agent_status()
            return HealthCheckResponse(
                status="healthy" if all(a.get("execution_status") != "failed" for a in agent_status.values()) else "degraded",
                timestamp=datetime.utcnow().isoformat(),
                agents=agent_status,
                database="connected"
            )

        @self.app.get("/status")
        async def system_status():
            """Get detailed system status."""
            return {
                "status": "operational",
                "timestamp": datetime.utcnow().isoformat(),
                "agents": self.orchestrator.get_agent_status(),
                "approvals": self.orchestrator.approval_manager.get_statistics()
            }

        # ====================================================================
        # EXECUTION ENDPOINTS
        # ====================================================================

        @self.app.post("/execute/all")
        async def execute_all_agents(credentials: HTTPAuthCredential = Depends(self.security)):
            """Execute all governance agents."""
            self._verify_token(credentials.credentials)

            try:
                report = self.orchestrator.execute_all_agents()
                return report
            except Exception as e:
                logger.error(f"Execution failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/execute/{agent_name}")
        async def execute_specific_agent(agent_name: str, credentials: HTTPAuthCredential = Depends(self.security)):
            """Execute a specific agent."""
            self._verify_token(credentials.credentials)

            valid_agents = ["security", "performance", "cost", "spillage", "health"]
            if agent_name not in valid_agents:
                raise HTTPException(status_code=400, detail=f"Invalid agent: {agent_name}")

            try:
                result = self.orchestrator.execute_agent(agent_name)
                return result
            except Exception as e:
                logger.error(f"Agent execution failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        # ====================================================================
        # FINDINGS ENDPOINTS
        # ====================================================================

        @self.app.get("/findings", response_model=List[FindingResponse])
        async def get_all_findings(
            severity: Optional[str] = None,
            agent: Optional[str] = None
        ):
            """Get all findings."""
            findings = []

            for agent_name, a in self.orchestrator.agents.items():
                if agent and agent_name != agent:
                    continue

                for finding in a.current_findings:
                    if severity and finding.severity.value != severity:
                        continue

                    findings.append(FindingResponse(
                        finding_id=finding.finding_id,
                        title=finding.title,
                        severity=finding.severity.value,
                        category=finding.category,
                        resource_name=finding.resource_name,
                        resource_type=finding.resource_type,
                        detected_at=finding.detected_at.isoformat(),
                        recommendation=finding.recommendation
                    ))

            return findings

        @self.app.get("/findings/summary")
        async def findings_summary():
            """Get findings summary."""
            return self.orchestrator.get_findings_summary()

        @self.app.get("/findings/by-severity/{severity}")
        async def findings_by_severity(severity: str):
            """Get findings filtered by severity."""
            valid_severities = ["critical", "high", "medium", "low", "info"]
            if severity not in valid_severities:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

            findings = []
            for agent in self.orchestrator.agents.values():
                findings.extend([
                    f.to_dict() for f in agent.current_findings
                    if f.severity.value == severity
                ])

            return findings

        # ====================================================================
        # RECOMMENDATIONS ENDPOINTS
        # ====================================================================

        @self.app.get("/recommendations", response_model=List[RecommendationResponse])
        async def get_all_recommendations(agent: Optional[str] = None):
            """Get all recommendations."""
            recommendations = []

            for agent_name, a in self.orchestrator.agents.items():
                if agent and agent_name != agent:
                    continue

                for rec in a.current_recommendations:
                    recommendations.append(RecommendationResponse(
                        recommendation_id=rec.recommendation_id,
                        title=rec.title,
                        description=rec.description,
                        action_type=rec.action_type,
                        resource_name=rec.resource_name,
                        impact=rec.impact,
                        implementation_steps=rec.implementation_steps
                    ))

            return recommendations

        @self.app.get("/recommendations/summary")
        async def recommendations_summary():
            """Get recommendations summary."""
            return self.orchestrator.get_recommendations_summary()

        # ====================================================================
        # APPROVAL ENDPOINTS
        # ====================================================================

        @self.app.get("/approvals/pending", response_model=List[ApprovalRequestResponse])
        async def get_pending_approvals(approver_email: str):
            """Get pending approval requests for approver."""
            pending = self.orchestrator.get_pending_approvals(approver_email)
            return [ApprovalRequestResponse(**p) for p in pending]

        @self.app.post("/approvals/approve")
        async def approve_request(
            request: ApprovalActionRequest,
            credentials: HTTPAuthCredential = Depends(self.security)
        ):
            """Approve an approval request."""
            self._verify_token(credentials.credentials)

            result = self.orchestrator.approve_request(
                request.request_id,
                request.approver_email,
                request.comments
            )

            if not result["success"]:
                raise HTTPException(status_code=400, detail="Failed to approve request")

            return result

        @self.app.post("/approvals/reject")
        async def reject_request(
            request: ApprovalActionRequest,
            credentials: HTTPAuthCredential = Depends(self.security)
        ):
            """Reject an approval request."""
            self._verify_token(credentials.credentials)

            result = self.orchestrator.reject_request(
                request.request_id,
                request.approver_email,
                request.comments
            )

            if not result["success"]:
                raise HTTPException(status_code=400, detail="Failed to reject request")

            return result

        @self.app.get("/approvals/{request_id}")
        async def get_approval_details(request_id: str):
            """Get details of an approval request."""
            request = self.orchestrator.approval_manager.get_request(request_id)
            if not request:
                raise HTTPException(status_code=404, detail="Request not found")

            return request.to_dict()

        @self.app.get("/approvals/stats")
        async def approval_stats():
            """Get approval workflow statistics."""
            return self.orchestrator.approval_manager.get_statistics()

        # ====================================================================
        # PERFORMANCE ENDPOINTS
        # ====================================================================

        @self.app.get("/performance/slow-queries", response_model=List[SlowQueryResponse])
        async def get_slow_queries(threshold_seconds: int = 30, hours: int = 24):
            """Get slow queries."""
            try:
                queries = self.orchestrator.snowpark_client.get_slow_queries(
                    threshold_seconds=threshold_seconds,
                    hours=hours
                )
                return [SlowQueryResponse(**q) for q in queries]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/performance/query/{query_id}")
        async def get_query_profile(query_id: str):
            """Get query execution profile."""
            try:
                profile = self.orchestrator.snowpark_client.get_query_profile(query_id)
                return profile
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ====================================================================
        # WAREHOUSE ENDPOINTS
        # ====================================================================

        @self.app.get("/warehouses", response_model=List[WarehouseMetricsResponse])
        async def list_warehouses():
            """List all warehouses."""
            try:
                warehouses = self.orchestrator.snowpark_client.list_warehouses()
                return [WarehouseMetricsResponse(**w) for w in warehouses]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/warehouses/{warehouse_name}")
        async def get_warehouse_metrics(warehouse_name: str):
            """Get warehouse metrics."""
            try:
                metrics = self.orchestrator.snowpark_client.get_warehouse_metrics(warehouse_name)
                return metrics
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/warehouses/{warehouse_name}/costs")
        async def get_warehouse_costs(warehouse_name: str, days: int = 7):
            """Get warehouse costs."""
            try:
                costs = self.orchestrator.snowpark_client.get_warehouse_costs(warehouse_name, days)
                return costs
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/warehouses/{warehouse_name}/suspend")
        async def suspend_warehouse(
            warehouse_name: str,
            credentials: HTTPAuthCredential = Depends(self.security)
        ):
            """Suspend a warehouse."""
            self._verify_token(credentials.credentials)

            try:
                success = self.orchestrator.snowpark_client.suspend_warehouse(warehouse_name)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to suspend warehouse")

                return {"warehouse_name": warehouse_name, "action": "suspended", "success": True}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ====================================================================
        # COST ENDPOINTS
        # ====================================================================

        @self.app.get("/cost/account")
        async def get_account_costs(days: int = 30):
            """Get account total costs."""
            try:
                costs = self.orchestrator.snowpark_client.get_total_account_costs(days)
                return costs
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ====================================================================
        # SECURITY ENDPOINTS
        # ====================================================================

        @self.app.get("/security/users")
        async def list_users():
            """List all users."""
            try:
                users = self.orchestrator.snowpark_client.list_users()
                return users
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/security/users/{user_name}/permissions")
        async def get_user_permissions(user_name: str):
            """Get user permissions."""
            try:
                perms = self.orchestrator.snowpark_client.get_user_permissions(user_name)
                return perms
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/security/roles")
        async def list_roles():
            """List all roles."""
            try:
                roles = self.orchestrator.snowpark_client.list_roles()
                return roles
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ====================================================================
        # SLACK INTEGRATION ENDPOINTS (if available)
        # ====================================================================

        if self.slack_bot:
            @self.app.post("/slack/slash-command")
            async def handle_slash_command(command: str, args: str = ""):
                """Handle Slack slash command."""
                try:
                    result = self.slack_bot.handle_slash_command(command, args)
                    return result
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))

            @self.app.post("/slack/action")
            async def handle_slack_action(
                action: str,
                request_id: str,
                user_email: str,
                comments: str = ""
            ):
                """Handle Slack button action."""
                try:
                    result = self.slack_bot.handle_approval_action(action, request_id, user_email, comments)
                    return result
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))

    def _verify_token(self, token: str) -> bool:
        """Verify JWT token."""
        try:
            jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return True
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def get_app(self) -> FastAPI:
        """Get FastAPI application instance."""
        return self.app

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run API server."""
        import uvicorn
        logger.info(f"Starting Governance API server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)
