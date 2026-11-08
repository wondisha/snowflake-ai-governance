-- ============================================================================
-- MULTI-ENVIRONMENT DEPLOYMENT (DEV, STAGING, PRODUCTION)
-- ============================================================================

USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

-- ============================================================================
-- STEP 4A: Create Environment Configuration Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS GOVERNANCE.GOVERNANCE.ENVIRONMENT_CONFIG (
    CONFIG_ID STRING PRIMARY KEY,
    ENVIRONMENT_NAME STRING NOT NULL,  -- dev, staging, prod
    ACCOUNT_ID STRING NOT NULL,
    WAREHOUSE_NAME STRING NOT NULL,
    DATABASE_NAME STRING NOT NULL,
    ADMIN_EMAIL STRING,
    ALERT_EMAIL STRING,
    SLACK_CHANNEL STRING,
    COST_THRESHOLD_CRITICAL INT,        -- Credits per day
    COST_THRESHOLD_WARNING INT,         -- Credits per day
    APPROVAL_REQUIRED BOOLEAN,           -- Require approval for changes
    BACKUP_ENABLED BOOLEAN,
    RETENTION_DAYS INT,                 -- Data retention
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- STEP 4B: Insert Environment Configurations
-- ============================================================================

-- DEV Environment
INSERT INTO GOVERNANCE.GOVERNANCE.ENVIRONMENT_CONFIG (
    CONFIG_ID, ENVIRONMENT_NAME, ACCOUNT_ID, WAREHOUSE_NAME, DATABASE_NAME,
    ADMIN_EMAIL, ALERT_EMAIL, SLACK_CHANNEL,
    COST_THRESHOLD_CRITICAL, COST_THRESHOLD_WARNING,
    APPROVAL_REQUIRED, BACKUP_ENABLED, RETENTION_DAYS
) VALUES (
    SUBSTRING(UUID_STRING(), 0, 36),
    'dev',
    'DEV_ACCOUNT_ID',  -- Replace with actual account ID
    'DEV_COMPUTE_WH',
    'GOVERNANCE_DEV',
    'dev-admin@company.com',
    'dev-alerts@company.com',
    '#dev-alerts',
    100,   -- Critical threshold
    50,    -- Warning threshold
    FALSE, -- No approval required in dev
    TRUE,
    30
);

-- STAGING Environment
INSERT INTO GOVERNANCE.GOVERNANCE.ENVIRONMENT_CONFIG (
    CONFIG_ID, ENVIRONMENT_NAME, ACCOUNT_ID, WAREHOUSE_NAME, DATABASE_NAME,
    ADMIN_EMAIL, ALERT_EMAIL, SLACK_CHANNEL,
    COST_THRESHOLD_CRITICAL, COST_THRESHOLD_WARNING,
    APPROVAL_REQUIRED, BACKUP_ENABLED, RETENTION_DAYS
) VALUES (
    SUBSTRING(UUID_STRING(), 0, 36),
    'staging',
    'STAGING_ACCOUNT_ID',  -- Replace with actual account ID
    'STAGING_COMPUTE_WH',
    'GOVERNANCE_STAGING',
    'staging-admin@company.com',
    'staging-alerts@company.com',
    '#staging-alerts',
    200,   -- Critical threshold
    100,   -- Warning threshold
    TRUE,  -- Approval required in staging
    TRUE,
    30
);

-- PRODUCTION Environment (your current one)
INSERT INTO GOVERNANCE.GOVERNANCE.ENVIRONMENT_CONFIG (
    CONFIG_ID, ENVIRONMENT_NAME, ACCOUNT_ID, WAREHOUSE_NAME, DATABASE_NAME,
    ADMIN_EMAIL, ALERT_EMAIL, SLACK_CHANNEL,
    COST_THRESHOLD_CRITICAL, COST_THRESHOLD_WARNING,
    APPROVAL_REQUIRED, BACKUP_ENABLED, RETENTION_DAYS
) VALUES (
    SUBSTRING(UUID_STRING(), 0, 36),
    'production',
    'QZCIUOS-DB05264',     -- Your actual account ID
    'COMPUTE_WH',
    'GOVERNANCE',
    'admin@company.com',
    'governance-alerts@company.com',
    '#snowflake-governance-alerts',
    500,   -- Critical threshold
    250,   -- Warning threshold
    TRUE,  -- Approval required in production
    TRUE,
    90     -- 90-day retention in production
);

-- ============================================================================
-- STEP 4C: Create Deployment Procedure
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.DEPLOY_TO_ENVIRONMENT(
    p_environment VARCHAR,
    p_deployment_type VARCHAR  -- 'full', 'agents_only', 'schema_only'
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
  v_deployment_id VARCHAR := SUBSTRING(UUID_STRING(), 0, 36);
  v_env_config RECORD;
BEGIN
  -- Get environment configuration
  FOR v_env_config IN (
    SELECT * FROM GOVERNANCE.GOVERNANCE.ENVIRONMENT_CONFIG
    WHERE ENVIRONMENT_NAME = p_environment
  )
  DO
    -- Log deployment start
    INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
    SELECT
      SUBSTRING(UUID_STRING(), 0, 36),
      'deployment_started',
      'deployment',
      'environment',
      p_environment,
      'system@governance',
      'Deployment started for ' || p_environment || ': ' || p_deployment_type,
      TO_VARIANT(OBJECT_CONSTRUCT('deployment_id', v_deployment_id)),
      NULL,
      'in_progress',
      NULL,
      NULL,
      CURRENT_TIMESTAMP(),
      CURRENT_TIMESTAMP(),
      TRUE;

    -- Deployment logic would go here
    -- In production, this would execute remote procedures or API calls

    -- Log deployment completion
    INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
    SELECT
      SUBSTRING(UUID_STRING(), 0, 36),
      'deployment_completed',
      'deployment',
      'environment',
      p_environment,
      'system@governance',
      'Deployment completed successfully for ' || p_environment,
      TO_VARIANT(OBJECT_CONSTRUCT('deployment_id', v_deployment_id)),
      NULL,
      'success',
      NULL,
      NULL,
      CURRENT_TIMESTAMP(),
      CURRENT_TIMESTAMP(),
      TRUE;
  END FOR;

  RETURN 'Deployment initiated: ' || v_deployment_id;
END;
$$;

-- ============================================================================
-- STEP 4D: Create Environment-Specific Configuration Procedure
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.GET_ENVIRONMENT_CONFIG(
    p_environment VARCHAR
)
RETURNS OBJECT
LANGUAGE SQL
AS
$$
DECLARE
  v_config OBJECT;
BEGIN
  SELECT OBJECT_CONSTRUCT(
    'environment', ENVIRONMENT_NAME,
    'account', ACCOUNT_ID,
    'warehouse', WAREHOUSE_NAME,
    'database', DATABASE_NAME,
    'admin_email', ADMIN_EMAIL,
    'cost_critical_threshold', COST_THRESHOLD_CRITICAL,
    'cost_warning_threshold', COST_THRESHOLD_WARNING,
    'approval_required', APPROVAL_REQUIRED,
    'backup_enabled', BACKUP_ENABLED
  ) INTO v_config
  FROM GOVERNANCE.GOVERNANCE.ENVIRONMENT_CONFIG
  WHERE ENVIRONMENT_NAME = p_environment;

  RETURN v_config;
END;
$$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT * FROM GOVERNANCE.GOVERNANCE.ENVIRONMENT_CONFIG;
