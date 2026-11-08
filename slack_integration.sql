-- ============================================================================
-- SLACK INTEGRATION FOR CRITICAL INCIDENTS & ALERTS
-- ============================================================================

USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

-- ============================================================================
-- STEP 1: Create External Integration for Slack
-- ============================================================================

-- Execute this as ACCOUNTADMIN (one time only)
-- CREATE OR REPLACE NOTIFICATION INTEGRATION slack_notification
-- TYPE = SLACK
-- ENABLED = true
-- SLACK_API_WEBHOOK_URL = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL';

-- For now, we'll use Python UDF to call Slack webhook directly

-- ============================================================================
-- STEP 1A: Create Slack Alert Procedure
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.SEND_SLACK_ALERT(
    p_channel VARCHAR,
    p_severity VARCHAR,
    p_incident_type VARCHAR,
    p_message VARCHAR,
    p_details VARIANT
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('requests')
HANDLER = 'send_alert'
AS
$$
import requests
import json
from datetime import datetime

def send_alert(channel, severity, incident_type, message, details):
    # Replace with your actual Slack webhook URL
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

    # Color coding by severity
    severity_colors = {
        'critical': '#FF0000',  # Red
        'high': '#FF6600',      # Orange
        'medium': '#FFFF00',    # Yellow
        'low': '#00FF00'        # Green
    }

    color = severity_colors.get(severity.lower(), '#808080')

    # Build Slack message
    slack_message = {
        "channel": channel,
        "username": "Snowflake Governance",
        "icon_emoji": ":snowflake:",
        "attachments": [
            {
                "color": color,
                "title": f"🚨 {severity.upper()} - {incident_type}",
                "text": message,
                "fields": [
                    {
                        "title": "Timestamp",
                        "value": datetime.now().isoformat(),
                        "short": True
                    },
                    {
                        "title": "Details",
                        "value": json.dumps(details, indent=2),
                        "short": False
                    }
                ],
                "footer": "Snowflake Governance Agent"
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=slack_message)
        if response.status_code == 200:
            return f"Alert sent to Slack: {channel}"
        else:
            return f"Failed to send Slack alert: {response.text}"
    except Exception as e:
        return f"Error sending Slack alert: {str(e)}"
$$;

-- ============================================================================
-- STEP 1B: Create Trigger for Critical Incidents
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.MONITOR_CRITICAL_INCIDENTS()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Check for new critical incidents and send Slack alerts
  FOR record IN (
    SELECT
      INCIDENT_ID,
      SEVERITY,
      CATEGORY,
      DESCRIPTION,
      DETECTED_TIMESTAMP
    FROM GOVERNANCE.GOVERNANCE.INCIDENTS
    WHERE SEVERITY = 'critical'
      AND STATUS = 'open'
      AND DETECTED_TIMESTAMP >= CURRENT_TIMESTAMP() - INTERVAL '1 hour'
      AND INCIDENT_ID NOT IN (
        SELECT DISTINCT VALUE FROM GOVERNANCE.GOVERNANCE.NOTIFICATION_QUEUE
        WHERE NOTIFICATION_TYPE = 'slack_alert'
      )
  )
  DO
    BEGIN
      -- Call Slack alert
      CALL GOVERNANCE.GOVERNANCE.SEND_SLACK_ALERT(
        '#snowflake-governance-alerts',
        record.severity,
        record.category,
        record.description,
        OBJECT_CONSTRUCT(
          'incident_id', record.incident_id,
          'detected_at', record.detected_timestamp
        )
      );

      -- Mark as notified
      INSERT INTO GOVERNANCE.GOVERNANCE.NOTIFICATION_QUEUE (
        NOTIFICATION_ID, NOTIFICATION_TYPE, CONTENT, STATUS, CREATED_AT
      )
      VALUES (
        SUBSTRING(UUID_STRING(), 0, 36),
        'slack_alert',
        record.incident_id,
        'sent',
        CURRENT_TIMESTAMP()
      );
    EXCEPTION WHEN OTHER THEN
      NULL;
    END;
  END FOR;

  RETURN 'Critical incident alerts sent to Slack';
END;
$$;

-- ============================================================================
-- STEP 1C: Schedule Slack Alert Monitoring
-- ============================================================================

CREATE OR REPLACE TASK slack_alert_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 * * * * UTC'  -- Every hour
AS
  CALL GOVERNANCE.GOVERNANCE.MONITOR_CRITICAL_INCIDENTS();

ALTER TASK slack_alert_task RESUME;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SHOW TASKS IN SCHEMA GOVERNANCE LIKE 'slack%';
