-- Snowflake Governance & Health Control Agent - Database Schema
-- Phase 1: Core Tables for Foundation

-- Create governance schema
CREATE SCHEMA IF NOT EXISTS governance;
-- Note: Not using USE SCHEMA since context doesn't persist across individual execute() calls

-- ============================================================================
-- CORE POLICY & RULE DEFINITIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.policies (
    policy_id VARCHAR PRIMARY KEY,
    policy_name VARCHAR NOT NULL,
    policy_type VARCHAR NOT NULL,  -- 'security', 'performance', 'cost', 'health'
    description VARCHAR,
    rules VARIANT,  -- JSON array of rule definitions
    enabled BOOLEAN DEFAULT TRUE,
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_by VARCHAR
);

CREATE TABLE IF NOT EXISTS governance.security_rules (
    rule_id VARCHAR PRIMARY KEY,
    rule_name VARCHAR NOT NULL,
    rule_type VARCHAR NOT NULL,  -- 'rbac', 'data_classification', 'access_control'
    description VARCHAR,
    rule_definition VARIANT,  -- JSON with rule logic
    severity_level VARCHAR,  -- 'critical', 'high', 'medium', 'low'
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS governance.performance_thresholds (
    threshold_id VARCHAR PRIMARY KEY,
    metric_name VARCHAR NOT NULL,  -- 'query_execution_time', 'resource_contention', 'spill_to_disk'
    warehouse_name VARCHAR,  -- NULL for account-level thresholds
    warning_threshold FLOAT NOT NULL,
    critical_threshold FLOAT NOT NULL,
    unit VARCHAR,  -- 'seconds', 'MB', 'percentage'
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- APPROVAL & WORKFLOW MANAGEMENT
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.approval_requests (
    request_id VARCHAR PRIMARY KEY,
    request_type VARCHAR NOT NULL,  -- 'permission_grant', 'permission_revoke', 'config_change', 'remediation'
    source_agent VARCHAR NOT NULL,  -- which agent created this
    requestor_email VARCHAR NOT NULL,
    approver_email VARCHAR NOT NULL,
    request_context VARIANT NOT NULL,  -- Full context as JSON
    request_title VARCHAR NOT NULL,
    request_description TEXT,
    status VARCHAR DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'expired'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    request_expires_at TIMESTAMP,  -- Auto-reject after N hours
    approved_at TIMESTAMP NULL,
    approved_by VARCHAR NULL,
    rejection_reason VARCHAR NULL,
    approval_comments VARCHAR NULL,
    sla_hours INT DEFAULT 24,
    priority VARCHAR DEFAULT 'medium'  -- 'critical', 'high', 'medium', 'low'
);

CREATE TABLE IF NOT EXISTS governance.approval_history (
    history_id VARCHAR PRIMARY KEY,
    request_id VARCHAR NOT NULL REFERENCES governance.approval_requests(request_id),
    action VARCHAR NOT NULL,  -- 'requested', 'approved', 'rejected', 'escalated'
    actor_email VARCHAR NOT NULL,
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    notes VARCHAR,
    FOREIGN KEY (request_id) REFERENCES governance.approval_requests(request_id)
);

-- ============================================================================
-- AUDIT & COMPLIANCE LOGGING
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.audit_logs (
    audit_id VARCHAR PRIMARY KEY,
    event_type VARCHAR NOT NULL,  -- 'permission_granted', 'permission_revoked', 'config_changed', 'policy_violated'
    event_category VARCHAR NOT NULL,  -- 'security', 'performance', 'cost', 'health'
    resource_type VARCHAR,  -- 'warehouse', 'database', 'table', 'user', 'role'
    resource_name VARCHAR,
    actor_email VARCHAR,  -- Who performed the action
    action_description VARCHAR NOT NULL,
    before_state VARIANT,  -- Previous state (for config changes)
    after_state VARIANT,  -- New state (for config changes)
    status VARCHAR,  -- 'success', 'failed', 'pending'
    error_message VARCHAR,
    approval_request_id VARCHAR,  -- Link to approval if applicable
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    -- Immutability fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    is_immutable BOOLEAN DEFAULT TRUE
);

-- Snowflake uses clustering keys instead of traditional indexes
-- Cluster by event_timestamp for better query performance on audit logs
ALTER TABLE governance.audit_logs CLUSTER BY (event_timestamp);
ALTER TABLE governance.audit_logs CLUSTER BY (event_type);

-- ============================================================================
-- SECURITY & COMPLIANCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.pii_detections (
    detection_id VARCHAR PRIMARY KEY,
    database_name VARCHAR NOT NULL,
    schema_name VARCHAR NOT NULL,
    table_name VARCHAR NOT NULL,
    column_name VARCHAR NOT NULL,
    pii_type VARCHAR NOT NULL,  -- 'email', 'phone', 'ssn', 'credit_card', 'ipv4', 'ipv6', 'custom'
    confidence_score FLOAT,  -- 0.0 to 1.0
    sample_value VARCHAR,  -- Anonymized sample
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR DEFAULT 'detected',  -- 'detected', 'reviewed', 'masked', 'archived'
    action_taken VARCHAR,
    masked_at TIMESTAMP NULL,
    masked_by VARCHAR
);

-- ============================================================================
-- WAREHOUSE HEALTH & METRICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.warehouse_health (
    health_id VARCHAR PRIMARY KEY,
    warehouse_name VARCHAR NOT NULL,
    metric_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    cpu_percent FLOAT,
    memory_percent FLOAT,
    storage_used_gb BIGINT,
    query_queue_depth INT,
    avg_query_wait_seconds FLOAT,
    active_queries INT,
    failed_queries INT,
    queued_queries INT,
    health_status VARCHAR,  -- 'healthy', 'warning', 'critical'
    notes VARCHAR
);

-- Create time-series index
-- Snowflake clustering keys for performance (replaces traditional indexes) idx_warehouse_health_timestamp

-- ============================================================================
-- COST TRACKING & OPTIMIZATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.cost_tracking (
    cost_id VARCHAR PRIMARY KEY,
    warehouse_name VARCHAR NOT NULL,
    query_id VARCHAR,
    user_email VARCHAR,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    credits_used FLOAT NOT NULL,
    data_scanned_gb BIGINT,
    rows_produced BIGINT,
    execution_time_seconds FLOAT,
    is_cached BOOLEAN,
    cost_category VARCHAR,  -- 'compute', 'storage', 'transfer'
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Create index for cost analysis
-- Snowflake clustering keys for performance (replaces traditional indexes) idx_cost_tracking_warehouse
-- Snowflake clustering keys for performance (replaces traditional indexes) idx_cost_tracking_user

-- ============================================================================
-- QUERY ANALYSIS & PERFORMANCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.query_analysis (
    analysis_id VARCHAR PRIMARY KEY,
    query_id VARCHAR NOT NULL,
    warehouse_name VARCHAR NOT NULL,
    user_email VARCHAR,
    query_text VARCHAR,  -- First 500 chars for reference
    execution_time_seconds FLOAT NOT NULL,
    data_scanned_gb BIGINT,
    rows_produced BIGINT,
    bytes_spilled_to_disk BIGINT,
    is_optimizable BOOLEAN,
    optimization_recommendations VARIANT,  -- JSON array
    clustering_key_suggestions VARIANT,
    materialized_view_suggestions VARIANT,
    performance_score INT,  -- 0-100
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Create index for performance analysis
-- Snowflake clustering keys for performance (replaces traditional indexes) idx_query_analysis_warehouse

-- ============================================================================
-- REMEDIATION & INCIDENT TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.remediation_actions (
    action_id VARCHAR PRIMARY KEY,
    incident_id VARCHAR,
    action_type VARCHAR NOT NULL,  -- 'query_abort', 'warehouse_suspend', 'role_revoke', 'config_change'
    target_resource VARCHAR NOT NULL,  -- warehouse name, query ID, user, etc.
    agent_name VARCHAR,
    before_state VARIANT,  -- previous configuration/state
    after_state VARIANT,   -- new configuration/state
    approval_request_id VARCHAR,
    executed_by VARCHAR,  -- agent or approver name
    execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR,  -- 'pending', 'executing', 'success', 'failed', 'rolled_back'
    error_message VARCHAR,
    rollback_timestamp TIMESTAMP NULL,
    audit_log_id VARCHAR
);

CREATE TABLE IF NOT EXISTS governance.incidents (
    incident_id VARCHAR PRIMARY KEY,
    severity VARCHAR,  -- 'critical', 'high', 'medium', 'low'
    category VARCHAR,  -- 'performance', 'security', 'cost', 'health'
    description TEXT NOT NULL,
    detected_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    resolved_timestamp TIMESTAMP NULL,
    assigned_to VARCHAR,
    status VARCHAR,  -- 'open', 'in_progress', 'resolved', 'wont_fix'
    related_audit_logs ARRAY,
    related_actions ARRAY,
    escalation_count INT DEFAULT 0,
    escalation_timestamp TIMESTAMP NULL,
    resolution_notes VARCHAR
);

-- Create index for incident tracking
-- Snowflake clustering keys for performance (replaces traditional indexes) idx_incidents_status
-- Snowflake clustering keys for performance (replaces traditional indexes) idx_incidents_severity

-- ============================================================================
-- AGENT STATE & HEALTH
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.agent_state (
    agent_id VARCHAR PRIMARY KEY,
    agent_name VARCHAR NOT NULL,
    agent_type VARCHAR NOT NULL,  -- 'security', 'performance', 'cost', 'health', 'spillage'
    last_execution_timestamp TIMESTAMP,
    last_successful_execution TIMESTAMP,
    execution_status VARCHAR,  -- 'running', 'idle', 'failed', 'disabled'
    items_detected INT DEFAULT 0,
    items_processed INT DEFAULT 0,
    error_count INT DEFAULT 0,
    last_error_message VARCHAR,
    next_scheduled_run TIMESTAMP,
    is_enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- NOTIFICATION QUEUE
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.notification_queue (
    notification_id VARCHAR PRIMARY KEY,
    recipient_email VARCHAR NOT NULL,
    notification_type VARCHAR,  -- 'approval_request', 'alert', 'recommendation', 'incident'
    channel VARCHAR,  -- 'email', 'slack', 'in_app'
    subject VARCHAR,
    message TEXT NOT NULL,
    action_url VARCHAR,
    payload VARIANT,  -- Additional context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    sent_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,
    status VARCHAR DEFAULT 'pending'  -- 'pending', 'sent', 'failed', 'read'
);

-- Create index for notification processing
-- Snowflake clustering keys for performance (replaces traditional indexes) idx_notification_queue_status

-- ============================================================================
-- CONFIGURATION & SETTINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance.system_config (
    config_key VARCHAR PRIMARY KEY,
    config_value VARCHAR NOT NULL,
    config_type VARCHAR,  -- 'string', 'int', 'float', 'boolean', 'json'
    description VARCHAR,
    is_sensitive BOOLEAN DEFAULT FALSE,  -- For passwords, keys, etc.
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_by VARCHAR
);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Pending approvals view
CREATE OR REPLACE VIEW governance.v_pending_approvals AS
SELECT
    request_id,
    request_type,
    request_title,
    requestor_email,
    approver_email,
    created_at,
    request_expires_at,
    DATEDIFF(hour, CURRENT_TIMESTAMP(), request_expires_at) as hours_until_expiry,
    priority,
    status
FROM governance.approval_requests
WHERE status = 'pending'
ORDER BY priority DESC, created_at ASC;

-- Recent violations view
CREATE OR REPLACE VIEW governance.v_recent_violations AS
SELECT
    audit_id,
    event_type,
    event_category,
    resource_type,
    resource_name,
    actor_email,
    event_timestamp,
    status,
    error_message
FROM governance.audit_logs
WHERE event_timestamp >= CURRENT_TIMESTAMP() - INTERVAL '7 days'
    AND status = 'success'
ORDER BY event_timestamp DESC;

-- Active incidents view
CREATE OR REPLACE VIEW governance.v_active_incidents AS
SELECT
    incident_id,
    severity,
    category,
    description,
    detected_timestamp,
    assigned_to,
    status,
    DATEDIFF(hour, detected_timestamp, CURRENT_TIMESTAMP()) as hours_open,
    escalation_count
FROM governance.incidents
WHERE status IN ('open', 'in_progress')
ORDER BY severity DESC, detected_timestamp ASC;

-- Agent health view
CREATE OR REPLACE VIEW governance.v_agent_health AS
SELECT
    agent_name,
    agent_type,
    last_successful_execution,
    DATEDIFF(hour, last_successful_execution, CURRENT_TIMESTAMP()) as hours_since_success,
    execution_status,
    error_count,
    is_enabled,
    next_scheduled_run
FROM governance.agent_state
ORDER BY last_successful_execution DESC;

-- Cost summary view
CREATE OR REPLACE VIEW governance.v_cost_summary_daily AS
SELECT
    DATE(recorded_at) as cost_date,
    warehouse_name,
    COUNT(*) as query_count,
    SUM(credits_used) as total_credits,
    AVG(execution_time_seconds) as avg_execution_seconds,
    SUM(data_scanned_gb) as total_data_scanned_gb
FROM governance.cost_tracking
GROUP BY DATE(recorded_at), warehouse_name
ORDER BY cost_date DESC, total_credits DESC;

-- ============================================================================
-- GRANTS & PERMISSIONS (if using Snowflake RBAC)
-- ============================================================================

-- These will be set up after agent service account creation
-- GRANT SELECT ON SCHEMA governance TO ROLE "governance_reader";
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA governance TO ROLE "governance_admin";
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA governance TO ROLE "governance_agent";

GRANT ALL ON SCHEMA governance TO ROLE accountadmin;
