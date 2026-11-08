-- ============================================================================
-- INACTIVE USER REMOVAL (90+ DAYS INACTIVE)
-- ============================================================================

USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

-- ============================================================================
-- STEP 5A: Create User Activity Tracking Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG (
    ACTIVITY_ID STRING PRIMARY KEY,
    USER_NAME STRING NOT NULL,
    USER_EMAIL STRING,
    LAST_LOGIN TIMESTAMP,
    LAST_QUERY_TIME TIMESTAMP,
    QUERY_COUNT INT,
    DAYS_INACTIVE INT,
    FLAGGED_FOR_REMOVAL BOOLEAN DEFAULT FALSE,
    REMOVAL_SCHEDULED TIMESTAMP,
    STATUS STRING DEFAULT 'active',  -- active, inactive, flagged, removed
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- STEP 5B: Identify Inactive Users (90+ days)
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.IDENTIFY_INACTIVE_USERS()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Identify users inactive for 90+ days
  INSERT INTO GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG (
    ACTIVITY_ID,
    USER_NAME,
    USER_EMAIL,
    LAST_LOGIN,
    DAYS_INACTIVE,
    STATUS
  )
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    NAME,
    EMAIL,
    LAST_SUCCESS_LOGIN,
    DATEDIFF(day, LAST_SUCCESS_LOGIN, CURRENT_DATE()),
    CASE
      WHEN DATEDIFF(day, LAST_SUCCESS_LOGIN, CURRENT_DATE()) >= 90 THEN 'flagged'
      ELSE 'active'
    END
  FROM SNOWFLAKE.ACCOUNT_USAGE.USERS
  WHERE DATEDIFF(day, LAST_SUCCESS_LOGIN, CURRENT_DATE()) >= 90
    AND NOT (NAME LIKE '%@snowflake%' OR NAME LIKE 'SFSESSIONUSER%')  -- Exclude service accounts
    AND DELETED_ON IS NULL  -- Only active users
  ON CONFLICT (ACTIVITY_ID) DO UPDATE SET
    DAYS_INACTIVE = EXCLUDED.DAYS_INACTIVE,
    STATUS = EXCLUDED.STATUS,
    UPDATED_AT = CURRENT_TIMESTAMP();

  -- Log identification results
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'inactive_users_identified',
    'security',
    'user_management',
    'batch_identification',
    'system@governance',
    'Inactive users (90+ days) identified',
    TO_VARIANT(OBJECT_CONSTRUCT(
      'inactive_user_count', (SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG WHERE STATUS = 'flagged')
    )),
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;

  RETURN 'Inactive users identified';
END;
$$;

-- ============================================================================
-- STEP 5C: Create Removal Approval Request
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.REQUEST_INACTIVE_USER_REMOVAL(
    p_user_name VARCHAR,
    p_days_inactive INT
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Create approval request for user removal
  CALL GOVERNANCE.GOVERNANCE.CREATE_APPROVAL_REQUEST(
    'user_removal',
    p_user_name,
    'Remove inactive user after ' || p_days_inactive || ' days of inactivity',
    'high',  -- Risk level: high
    'system@governance',
    ARRAY_CONSTRUCT('admin@company.com', 'security@company.com')  -- Required approvers
  );

  -- Mark user as flagged
  UPDATE GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
  SET
    STATUS = 'flagged',
    FLAGGED_FOR_REMOVAL = TRUE,
    REMOVAL_SCHEDULED = CURRENT_TIMESTAMP()
  WHERE USER_NAME = p_user_name;

  RETURN 'Removal request created for user: ' || p_user_name;
END;
$$;

-- ============================================================================
-- STEP 5D: Disable Inactive User Account (Auto-disable after approval)
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.DISABLE_INACTIVE_USER(
    p_user_name VARCHAR,
    p_reason VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Disable the user account
  EXECUTE IMMEDIATE 'ALTER USER "' || p_user_name || '" SET DISABLED = TRUE';

  -- Update status
  UPDATE GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
  SET STATUS = 'disabled'
  WHERE USER_NAME = p_user_name;

  -- Log the action
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'user_disabled',
    'security',
    'user_management',
    p_user_name,
    'system@governance',
    'User account disabled: ' || p_reason,
    TO_VARIANT(OBJECT_CONSTRUCT('reason', p_reason)),
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;

  RETURN 'User disabled: ' || p_user_name;
END;
$$;

-- ============================================================================
-- STEP 5E: Remove Inactive User Role Grants
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.REVOKE_INACTIVE_USER_ROLES(
    p_user_name VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Get all granted roles
  FOR record IN (
    SELECT ROLE FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_USERS
    WHERE GRANTEE_NAME = p_user_name
  )
  DO
    BEGIN
      EXECUTE IMMEDIATE 'REVOKE ROLE "' || record.role || '" FROM USER "' || p_user_name || '"';
    EXCEPTION WHEN OTHER THEN
      NULL;  -- Continue on error
    END;
  END FOR;

  -- Log revocation
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'user_roles_revoked',
    'security',
    'user_management',
    p_user_name,
    'system@governance',
    'All roles revoked from inactive user',
    NULL,
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;

  RETURN 'Roles revoked for: ' || p_user_name;
END;
$$;

-- ============================================================================
-- STEP 5F: Archive Inactive User Data & Sessions
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.ARCHIVE_INACTIVE_USER_DATA(
    p_user_name VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Insert into archive table
  INSERT INTO GOVERNANCE.GOVERNANCE.ARCHIVED_USERS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    NAME,
    EMAIL,
    CREATED_ON,
    LAST_SUCCESS_LOGIN,
    CURRENT_TIMESTAMP(),
    TO_VARIANT(OBJECT_CONSTRUCT(
      'reason', 'Archived due to 90+ days inactivity',
      'archived_by', 'system@governance'
    ))
  FROM SNOWFLAKE.ACCOUNT_USAGE.USERS
  WHERE NAME = p_user_name;

  -- Log archival
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'user_archived',
    'security',
    'user_management',
    p_user_name,
    'system@governance',
    'Inactive user data archived',
    NULL,
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;

  RETURN 'User data archived: ' || p_user_name;
END;
$$;

-- ============================================================================
-- STEP 5G: Complete Inactive User Removal Workflow
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.REMOVE_INACTIVE_USER_COMPLETE(
    p_user_name VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Step 1: Revoke all roles
  CALL GOVERNANCE.GOVERNANCE.REVOKE_INACTIVE_USER_ROLES(p_user_name);

  -- Step 2: Archive user data
  CALL GOVERNANCE.GOVERNANCE.ARCHIVE_INACTIVE_USER_DATA(p_user_name);

  -- Step 3: Disable user account
  CALL GOVERNANCE.GOVERNANCE.DISABLE_INACTIVE_USER(
    p_user_name,
    'Inactive for 90+ days - auto-removal'
  );

  -- Step 4: Update final status
  UPDATE GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
  SET STATUS = 'removed'
  WHERE USER_NAME = p_user_name;

  -- Step 5: Log completion
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'user_removal_completed',
    'security',
    'user_management',
    p_user_name,
    'system@governance',
    'Inactive user removal completed',
    NULL,
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;

  RETURN 'User removal completed: ' || p_user_name;
END;
$$;

-- ============================================================================
-- STEP 5H: Weekly Inactive User Cleanup Task
-- ============================================================================

CREATE OR REPLACE TASK inactive_user_cleanup_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 0 * * 1 UTC'  -- Weekly on Monday at midnight UTC
AS
BEGIN
  -- Identify inactive users
  CALL GOVERNANCE.GOVERNANCE.IDENTIFY_INACTIVE_USERS();

  -- For each flagged user, create removal request (requires approval)
  FOR record IN (
    SELECT USER_NAME, DAYS_INACTIVE
    FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
    WHERE STATUS = 'flagged'
      AND DAYS_INACTIVE >= 90
      AND REMOVAL_SCHEDULED IS NULL
  )
  DO
    BEGIN
      CALL GOVERNANCE.GOVERNANCE.REQUEST_INACTIVE_USER_REMOVAL(
        record.USER_NAME,
        record.DAYS_INACTIVE
      );
    EXCEPTION WHEN OTHER THEN
      NULL;
    END;
  END FOR;
END;

ALTER TASK inactive_user_cleanup_task RESUME;

-- ============================================================================
-- STEP 5I: Create Archived Users Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS GOVERNANCE.GOVERNANCE.ARCHIVED_USERS (
    ARCHIVE_ID STRING PRIMARY KEY,
    USER_NAME STRING NOT NULL,
    USER_EMAIL STRING,
    CREATED_ON TIMESTAMP,
    LAST_LOGIN TIMESTAMP,
    ARCHIVED_ON TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    METADATA VARIANT,
    INDEX idx_archived_username (USER_NAME)
);

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- View inactive users
-- SELECT USER_NAME, USER_EMAIL, DAYS_INACTIVE, STATUS, FLAGGED_FOR_REMOVAL
-- FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
-- WHERE DAYS_INACTIVE >= 90
-- ORDER BY DAYS_INACTIVE DESC;

-- View removal requests
-- SELECT REQUEST_ID, RESOURCE_NAME, STATUS, RISK_LEVEL, REQUEST_CREATED_AT
-- FROM GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
-- WHERE REQUEST_TYPE = 'user_removal'
-- ORDER BY REQUEST_CREATED_AT DESC;

-- View archived users
-- SELECT USER_NAME, ARCHIVED_ON, METADATA
-- FROM GOVERNANCE.GOVERNANCE.ARCHIVED_USERS
-- ORDER BY ARCHIVED_ON DESC;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SHOW TABLES LIKE 'USER_ACTIVITY%';
SHOW TABLES LIKE 'ARCHIVED_USERS';
SHOW TASKS IN SCHEMA GOVERNANCE LIKE 'inactive%';
