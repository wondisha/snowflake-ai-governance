-- ============================================================================
-- DAILY EMAIL REPORTS FOR GOVERNANCE SUMMARY
-- ============================================================================

USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

-- ============================================================================
-- STEP 3A: Create Daily Report Generation Procedure
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.GENERATE_DAILY_REPORT()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
  v_report_date DATE := CURRENT_DATE();
  v_report_id VARCHAR := SUBSTRING(UUID_STRING(), 0, 36);
BEGIN
  -- Create daily summary report
  INSERT INTO GOVERNANCE.GOVERNANCE.DAILY_REPORT
  SELECT
    v_report_id,
    v_report_date,
    -- Incident metrics
    (SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.INCIDENTS
     WHERE DATE(DETECTED_TIMESTAMP) = v_report_date) as total_incidents,
    (SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.INCIDENTS
     WHERE DATE(DETECTED_TIMESTAMP) = v_report_date AND STATUS = 'open') as open_incidents,
    (SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.INCIDENTS
     WHERE DATE(DETECTED_TIMESTAMP) = v_report_date AND SEVERITY = 'critical') as critical_incidents,
    -- Agent metrics
    (SELECT COUNT(DISTINCT AGENT_NAME) FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
     WHERE IS_ENABLED = TRUE) as active_agents,
    (SELECT SUM(ERROR_COUNT) FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
     WHERE IS_ENABLED = TRUE) as total_agent_errors,
    (SELECT AVG(ERROR_COUNT) FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
     WHERE IS_ENABLED = TRUE) as avg_agent_errors,
    -- Cost metrics
    (SELECT SUM(CREDITS_USED) FROM GOVERNANCE.GOVERNANCE.COST_TRACKING
     WHERE DATE(RECORDED_AT) = v_report_date) as credits_used_today,
    -- Security metrics
    (SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
     WHERE DATE(EVENT_TIMESTAMP) = v_report_date
     AND EVENT_CATEGORY = 'security') as security_events,
    -- Approval metrics
    (SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
     WHERE DATE(REQUEST_CREATED_AT) = v_report_date
     AND STATUS = 'pending') as pending_approvals,
    -- Generate report timestamp
    CURRENT_TIMESTAMP();

  -- Log report generation
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'daily_report_generated',
    'governance',
    'report',
    v_report_id,
    'system@governance',
    'Daily governance report generated for ' || v_report_date,
    NULL,
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;

  RETURN 'Daily report generated: ' || v_report_id;
END;
$$;

-- ============================================================================
-- STEP 3B: Create Email Report Formatter
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.FORMAT_EMAIL_REPORT()
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('requests')
HANDLER = 'format_email'
AS
$$
def format_email(session):
    import json
    from datetime import date

    report_date = date.today()

    # Query the daily report
    result = session.sql(f"""
        SELECT
            TOTAL_INCIDENTS,
            OPEN_INCIDENTS,
            CRITICAL_INCIDENTS,
            ACTIVE_AGENTS,
            TOTAL_AGENT_ERRORS,
            CREDITS_USED_TODAY,
            SECURITY_EVENTS,
            PENDING_APPROVALS
        FROM GOVERNANCE.GOVERNANCE.DAILY_REPORT
        WHERE REPORT_DATE = '{report_date}'
        ORDER BY REPORT_TIMESTAMP DESC
        LIMIT 1
    """).collect()

    if not result:
        return "No report data available"

    data = result[0]

    # Format HTML email
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #0066cc; color: white; padding: 20px; }}
            .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #0066cc; }}
            .metric {{ display: inline-block; margin: 10px 20px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .alert {{ background-color: #fff3cd; padding: 10px; margin: 10px 0; border-radius: 4px; }}
            .success {{ background-color: #d4edda; padding: 10px; margin: 10px 0; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>❄️ Snowflake Governance Daily Report</h1>
            <p>Report Date: {report_date}</p>
        </div>

        <div class="section">
            <h2>📊 Incidents</h2>
            <div class="metric">
                <div class="metric-value">{data['TOTAL_INCIDENTS']}</div>
                <div class="metric-label">Total Incidents</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data['OPEN_INCIDENTS']}</div>
                <div class="metric-label">Open Incidents</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data['CRITICAL_INCIDENTS']}</div>
                <div class="metric-label">Critical Incidents</div>
            </div>
        </div>

        <div class="section">
            <h2>🤖 Agent Status</h2>
            <div class="metric">
                <div class="metric-value">{data['ACTIVE_AGENTS']}</div>
                <div class="metric-label">Active Agents</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data['TOTAL_AGENT_ERRORS']}</div>
                <div class="metric-label">Total Errors</div>
            </div>
        </div>

        <div class="section">
            <h2>💰 Cost</h2>
            <div class="metric">
                <div class="metric-value">{data['CREDITS_USED_TODAY']:.2f}</div>
                <div class="metric-label">Credits Used Today</div>
            </div>
        </div>

        <div class="section">
            <h2>🔒 Security</h2>
            <div class="metric">
                <div class="metric-value">{data['SECURITY_EVENTS']}</div>
                <div class="metric-label">Security Events</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data['PENDING_APPROVALS']}</div>
                <div class="metric-label">Pending Approvals</div>
            </div>
        </div>

        <div class="section">
            <p>📈 View full dashboard: <a href="https://your-snowsight-url">Snowflake Governance Dashboard</a></p>
        </div>
    </body>
    </html>
    """

    return html_body
$$;

-- ============================================================================
-- STEP 3C: Send Email Report via Stored Procedure
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.SEND_EMAIL_REPORT(
    p_recipient_email VARCHAR
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('requests')
HANDLER = 'send_email'
AS
$$
def send_email(session, recipient_email):
    import requests
    import json
    from datetime import date

    report_date = date.today()

    # Get email content (you would call the format procedure)
    result = session.sql(f"""
        SELECT
            TOTAL_INCIDENTS,
            OPEN_INCIDENTS,
            CRITICAL_INCIDENTS,
            ACTIVE_AGENTS,
            CREDITS_USED_TODAY,
            SECURITY_EVENTS,
            PENDING_APPROVALS
        FROM GOVERNANCE.GOVERNANCE.DAILY_REPORT
        WHERE REPORT_DATE = '{report_date}'
        ORDER BY REPORT_TIMESTAMP DESC
        LIMIT 1
    """).collect()

    if not result:
        return "No report data to send"

    data = result[0]

    # Email via SendGrid, AWS SES, or your email service
    # This is a template - configure with your actual email service
    email_payload = {
        "personalizations": [{
            "to": [{"email": recipient_email}],
            "subject": f"Snowflake Governance Report - {report_date}"
        }],
        "from": {"email": "governance@company.com"},
        "content": [{
            "type": "text/html",
            "value": f"""
            <h2>Snowflake Governance Daily Report - {report_date}</h2>
            <p><strong>Incidents:</strong> {data['TOTAL_INCIDENTS']} total, {data['OPEN_INCIDENTS']} open, {data['CRITICAL_INCIDENTS']} critical</p>
            <p><strong>Agents:</strong> {data['ACTIVE_AGENTS']} active</p>
            <p><strong>Cost:</strong> {data['CREDITS_USED_TODAY']:.2f} credits used</p>
            <p><strong>Security:</strong> {data['SECURITY_EVENTS']} events, {data['PENDING_APPROVALS']} pending approvals</p>
            """
        }]
    }

    # Send via your email service (example: SendGrid)
    # headers = {"Authorization": "Bearer YOUR_SENDGRID_API_KEY"}
    # response = requests.post("https://api.sendgrid.com/v3/mail/send", json=email_payload, headers=headers)

    return f"Email report queued for {recipient_email}"
$$;

-- ============================================================================
-- STEP 3D: Schedule Daily Report Generation & Email
-- ============================================================================

CREATE OR REPLACE TASK daily_report_generation_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 6 * * * UTC'  -- Daily at 6 AM UTC
AS
  CALL GOVERNANCE.GOVERNANCE.GENERATE_DAILY_REPORT();

ALTER TASK daily_report_generation_task RESUME;

-- ============================================================================
-- STEP 3E: Send reports to stakeholders (schedule separately)
-- ============================================================================

CREATE OR REPLACE TASK send_email_reports_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 7 * * * UTC'  -- Daily at 7 AM UTC (after report generation)
AS
  CALL GOVERNANCE.GOVERNANCE.SEND_EMAIL_REPORT('admin@company.com');

ALTER TASK send_email_reports_task RESUME;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SHOW TABLES LIKE 'DAILY_REPORT';
SHOW TASKS IN SCHEMA GOVERNANCE LIKE 'report%';
