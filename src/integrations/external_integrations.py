"""
External Integrations Module - Connects to ServiceNow, DataDog, Splunk, PagerDuty.
Enables enterprise platform integration for incidents, metrics, and logs.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import requests


logger = logging.getLogger(__name__)


class ServiceNowIntegration:
    """ServiceNow incident management integration."""

    def __init__(self, instance_url: str, username: str, password: str):
        """
        Initialize ServiceNow integration.

        Args:
            instance_url: ServiceNow instance URL (e.g., https://dev12345.service-now.com)
            username: ServiceNow username
            password: ServiceNow password
        """
        self.instance_url = instance_url
        self.username = username
        self.password = password
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def create_incident(
        self,
        title: str,
        description: str,
        severity: str,
        category: str,
        assignment_group: str = "Governance Team"
    ) -> Optional[str]:
        """
        Create a ServiceNow incident.

        Args:
            title: Incident title
            description: Incident description
            severity: Severity (1-Critical, 2-High, 3-Medium, 4-Low)
            category: Incident category
            assignment_group: Assignment group

        Returns:
            Incident number if successful
        """
        try:
            severity_map = {
                "critical": "1",
                "high": "2",
                "medium": "3",
                "low": "4"
            }

            payload = {
                "short_description": title,
                "description": description,
                "urgency": severity_map.get(severity, "3"),
                "impact": severity_map.get(severity, "3"),
                "category": category,
                "assignment_group": assignment_group,
                "source": "Snowflake Governance Agent"
            }

            url = f"{self.instance_url}/api/now/table/incident"
            response = requests.post(
                url,
                auth=(self.username, self.password),
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 201:
                incident_data = response.json()
                incident_number = incident_data.get("result", {}).get("number")
                logger.info(f"Created ServiceNow incident: {incident_number}")
                return incident_number
            else:
                logger.error(f"ServiceNow API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Failed to create ServiceNow incident: {str(e)}")
            return None

    def update_incident(
        self,
        incident_number: str,
        status: str = None,
        comments: str = None,
        resolution: str = None
    ) -> bool:
        """
        Update a ServiceNow incident.

        Args:
            incident_number: Incident number
            status: New status (new, in_progress, resolved, closed)
            comments: Add comment
            resolution: Resolution notes

        Returns:
            True if successful
        """
        try:
            payload = {}
            if status:
                payload["state"] = {"new": 1, "in_progress": 2, "resolved": 6, "closed": 7}.get(status, 2)
            if comments:
                payload["comments"] = comments
            if resolution:
                payload["resolution_notes"] = resolution

            url = f"{self.instance_url}/api/now/table/incident?sysparm_query=number={incident_number}"
            response = requests.patch(
                url,
                auth=(self.username, self.password),
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Updated ServiceNow incident: {incident_number}")
                return True
            else:
                logger.error(f"ServiceNow update error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to update ServiceNow incident: {str(e)}")
            return False


class DataDogIntegration:
    """DataDog metrics and events integration."""

    def __init__(self, api_key: str, app_key: str, site: str = "datadoghq.com"):
        """
        Initialize DataDog integration.

        Args:
            api_key: DataDog API key
            app_key: DataDog app key
            site: DataDog site (datadoghq.com or datadoghq.eu)
        """
        self.api_key = api_key
        self.app_key = app_key
        self.site = site
        self.api_url = f"https://api.{site}"

    def send_metric(
        self,
        metric_name: str,
        value: float,
        tags: Dict[str, str] = None
    ) -> bool:
        """
        Send a metric to DataDog.

        Args:
            metric_name: Metric name (e.g., governance.findings.count)
            value: Metric value
            tags: Optional tags (e.g., {'env': 'prod'})

        Returns:
            True if successful
        """
        try:
            url = f"{self.api_url}/api/v1/series"

            tags_list = [f"{k}:{v}" for k, v in (tags or {}).items()]

            payload = {
                "series": [
                    {
                        "metric": metric_name,
                        "points": [[int(datetime.utcnow().timestamp()), value]],
                        "type": "gauge",
                        "tags": tags_list
                    }
                ]
            }

            response = requests.post(
                url,
                headers={"DD-API-KEY": self.api_key},
                json=payload,
                timeout=10
            )

            if response.status_code == 202:
                logger.debug(f"Sent metric to DataDog: {metric_name}={value}")
                return True
            else:
                logger.error(f"DataDog metric error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to send DataDog metric: {str(e)}")
            return False

    def send_event(
        self,
        title: str,
        description: str,
        alert_type: str = "info",
        tags: Dict[str, str] = None
    ) -> bool:
        """
        Send an event to DataDog.

        Args:
            title: Event title
            description: Event description
            alert_type: Alert type (info, success, warning, error)
            tags: Optional tags

        Returns:
            True if successful
        """
        try:
            url = f"{self.api_url}/api/v1/events"

            tags_list = [f"{k}:{v}" for k, v in (tags or {}).items()]

            payload = {
                "title": title,
                "text": description,
                "alert_type": alert_type,
                "tags": tags_list,
                "source_type_name": "governance"
            }

            response = requests.post(
                url,
                headers={"DD-API-KEY": self.api_key},
                json=payload,
                timeout=10
            )

            if response.status_code == 202:
                logger.info(f"Sent event to DataDog: {title}")
                return True
            else:
                logger.error(f"DataDog event error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to send DataDog event: {str(e)}")
            return False


class SplunkIntegration:
    """Splunk logging and search integration."""

    def __init__(self, hec_url: str, hec_token: str):
        """
        Initialize Splunk integration via HTTP Event Collector.

        Args:
            hec_url: HEC URL (e.g., https://splunk.example.com:8088)
            hec_token: HEC authentication token
        """
        self.hec_url = hec_url
        self.hec_token = hec_token
        self.headers = {
            "Authorization": f"Splunk {hec_token}",
            "Content-Type": "application/json"
        }

    def send_event(
        self,
        event_data: Dict[str, Any],
        source: str = "snowflake_governance",
        sourcetype: str = "governance",
        index: str = "main"
    ) -> bool:
        """
        Send an event to Splunk.

        Args:
            event_data: Event data as dictionary
            source: Event source
            sourcetype: Event source type
            index: Splunk index

        Returns:
            True if successful
        """
        try:
            url = f"{self.hec_url}/services/collector"

            payload = {
                "event": event_data,
                "source": source,
                "sourcetype": sourcetype,
                "index": index,
                "time": datetime.utcnow().timestamp()
            }

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=10,
                verify=False  # Note: should be True in production
            )

            if response.status_code == 200:
                logger.debug(f"Sent event to Splunk: {sourcetype}")
                return True
            else:
                logger.error(f"Splunk HEC error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Splunk event: {str(e)}")
            return False

    def send_audit_log(
        self,
        audit_event: Dict[str, Any]
    ) -> bool:
        """
        Send an audit log entry to Splunk.

        Args:
            audit_event: Audit event data

        Returns:
            True if successful
        """
        return self.send_event(
            event_data=audit_event,
            source="snowflake_audit",
            sourcetype="audit",
            index="audit"
        )


class PagerDutyIntegration:
    """PagerDuty incident escalation integration."""

    def __init__(self, api_key: str, service_id: str):
        """
        Initialize PagerDuty integration.

        Args:
            api_key: PagerDuty API key
            service_id: PagerDuty service ID
        """
        self.api_key = api_key
        self.service_id = service_id
        self.api_url = "https://api.pagerduty.com"
        self.headers = {
            "Authorization": f"Token token={api_key}",
            "Content-Type": "application/json"
        }

    def create_incident(
        self,
        title: str,
        description: str,
        urgency: str = "high",
        assigned_to: str = None
    ) -> Optional[str]:
        """
        Create a PagerDuty incident.

        Args:
            title: Incident title
            description: Incident description
            urgency: Urgency (low, high)
            assigned_to: User ID to assign to

        Returns:
            Incident ID if successful
        """
        try:
            url = f"{self.api_url}/incidents"

            payload = {
                "incident": {
                    "type": "incident",
                    "title": title,
                    "body": {"type": "incident_body", "details": description},
                    "service": {"id": self.service_id, "type": "service_reference"},
                    "urgency": urgency
                }
            }

            if assigned_to:
                payload["incident"]["assignments"] = [
                    {"assignee": {"id": assigned_to, "type": "user_reference"}}
                ]

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 201:
                incident_data = response.json()
                incident_id = incident_data.get("incident", {}).get("id")
                logger.info(f"Created PagerDuty incident: {incident_id}")
                return incident_id
            else:
                logger.error(f"PagerDuty API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to create PagerDuty incident: {str(e)}")
            return None

    def trigger_alert(
        self,
        title: str,
        description: str,
        critical: bool = False
    ) -> bool:
        """
        Trigger a page to on-call team.

        Args:
            title: Alert title
            description: Alert description
            critical: Whether this is a critical alert

        Returns:
            True if successful
        """
        urgency = "high" if critical else "low"
        incident_id = self.create_incident(
            title=title,
            description=description,
            urgency=urgency
        )

        return incident_id is not None


class ExternalIntegrationsManager:
    """Manages all external integrations."""

    def __init__(self):
        """Initialize integrations manager."""
        self.servicenow = None
        self.datadog = None
        self.splunk = None
        self.pagerduty = None

    def configure_servicenow(self, instance_url: str, username: str, password: str) -> bool:
        """Configure ServiceNow integration."""
        try:
            self.servicenow = ServiceNowIntegration(instance_url, username, password)
            logger.info("ServiceNow integration configured")
            return True
        except Exception as e:
            logger.error(f"Failed to configure ServiceNow: {str(e)}")
            return False

    def configure_datadog(self, api_key: str, app_key: str, site: str = "datadoghq.com") -> bool:
        """Configure DataDog integration."""
        try:
            self.datadog = DataDogIntegration(api_key, app_key, site)
            logger.info("DataDog integration configured")
            return True
        except Exception as e:
            logger.error(f"Failed to configure DataDog: {str(e)}")
            return False

    def configure_splunk(self, hec_url: str, hec_token: str) -> bool:
        """Configure Splunk integration."""
        try:
            self.splunk = SplunkIntegration(hec_url, hec_token)
            logger.info("Splunk integration configured")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Splunk: {str(e)}")
            return False

    def configure_pagerduty(self, api_key: str, service_id: str) -> bool:
        """Configure PagerDuty integration."""
        try:
            self.pagerduty = PagerDutyIntegration(api_key, service_id)
            logger.info("PagerDuty integration configured")
            return True
        except Exception as e:
            logger.error(f"Failed to configure PagerDuty: {str(e)}")
            return False

    # ========================================================================
    # UNIFIED INTEGRATION METHODS
    # ========================================================================

    def report_finding(
        self,
        finding_id: str,
        title: str,
        description: str,
        severity: str,
        category: str
    ) -> Dict[str, bool]:
        """
        Report a finding to all configured external systems.

        Args:
            finding_id: Finding ID
            title: Finding title
            description: Finding description
            severity: Severity level
            category: Finding category

        Returns:
            Dictionary with success status for each integration
        """
        results = {}

        # ServiceNow: Create incident for critical findings
        if self.servicenow and severity in ["critical", "high"]:
            incident = self.servicenow.create_incident(
                title=title,
                description=description,
                severity=severity,
                category=category
            )
            results["servicenow"] = incident is not None

        # DataDog: Send event
        if self.datadog:
            success = self.datadog.send_event(
                title=title,
                description=description,
                alert_type=severity,
                tags={
                    "finding_id": finding_id,
                    "category": category
                }
            )
            results["datadog"] = success

        # Splunk: Send audit log
        if self.splunk:
            event = {
                "finding_id": finding_id,
                "title": title,
                "description": description,
                "severity": severity,
                "category": category,
                "timestamp": datetime.utcnow().isoformat()
            }
            success = self.splunk.send_event(event)
            results["splunk"] = success

        # PagerDuty: Critical findings trigger page
        if self.pagerduty and severity == "critical":
            success = self.pagerduty.trigger_alert(
                title=title,
                description=description,
                critical=True
            )
            results["pagerduty"] = success

        logger.info(f"Reported finding {finding_id} to external systems: {results}")
        return results

    def report_remediation(
        self,
        action_id: str,
        action_type: str,
        target: str,
        status: str,
        error_message: str = None
    ) -> Dict[str, bool]:
        """
        Report remediation action status to external systems.

        Args:
            action_id: Action ID
            action_type: Type of remediation
            target: Target resource
            status: Status (success, failed)
            error_message: Optional error message

        Returns:
            Dictionary with success status for each integration
        """
        results = {}

        event_data = {
            "action_id": action_id,
            "action_type": action_type,
            "target": target,
            "status": status,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Splunk: Always log
        if self.splunk:
            success = self.splunk.send_audit_log(event_data)
            results["splunk"] = success

        # DataDog: Send event for failures
        if self.datadog and status == "failed":
            success = self.datadog.send_event(
                title=f"Remediation failed: {action_type}",
                description=error_message or "Remediation action failed",
                alert_type="error",
                tags={"action_id": action_id}
            )
            results["datadog"] = success

        logger.info(f"Reported remediation {action_id} to external systems: {results}")
        return results

    def get_status(self) -> Dict[str, bool]:
        """Get status of all configured integrations."""
        return {
            "servicenow": self.servicenow is not None,
            "datadog": self.datadog is not None,
            "splunk": self.splunk is not None,
            "pagerduty": self.pagerduty is not None
        }
