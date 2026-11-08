-- ============================================================================
-- AUTOMATIC INACTIVE USER REMOVAL (NO APPROVAL REQUIRED)
-- ============================================================================
-- This script enables automatic removal of users inactive for 90+ days
-- without requiring manual approval. Runs weekly on Monday at midnight UTC.
--
-- CAUTION: This is FULLY AUTOMATIC - no approval workflow!
--
-- Execute this ONLY if you want users auto-removed (vs approval-based)
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

-- ============================================================================
-- OPTION 1: AUTOMATIC REMOVAL (NO APPROVAL)
-- ============================================================================

CREATE OR REPLACE TASK inactive_user_cleanup_task_auto
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 0 * * 1 UTC'  -- Weekly Monday midnight UTC
AS
BEGIN
  -- Step 1: Identify inactive users (90+ days)
  CALL GOVERNANCE.GOVERNANCE.IDENTIFY_INACTIVE_USERS();

  -- Step 2: Auto-remove each flagged user WITHOUT approval
  FOR record IN (
    SELECT USER_NAME, DAYS_INACTIVE
    FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
    WHERE DAYS_INACTIVE >= 90
      AND STATUS IN ('active', 'flagged')
  )
  DO
    BEGIN
      -- Log the auto-removal start
      INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
      SELECT
        SUBSTRING(UUID_STRING(), 0, 36),
        'auto_user_removal_started',
        'security',
        'user_management',
        record.USER_NAME,
        'system@governance',
        'Automatic removal initiated for inactive user (90+ days): ' || record.USER_NAME,
        TO_VARIANT(OBJECT_CONSTRUCT('days_inactive', record.DAYS_INACTIVE)),
        NULL,
        'in_progress',
        NULL,
        NULL,
        CURRENT_TIMESTAMP(),
        CURRENT_TIMESTAMP(),
        TRUE;

      -- Auto-remove without approval
      CALL GOVERNANCE.GOVERNANCE.REMOVE_INACTIVE_USER_COMPLETE(record.USER_NAME);

      -- Log completion
      INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
      SELECT
        SUBSTRING(UUID_STRING(), 0, 36),
        'auto_user_removal_completed',
        'security',
        'user_management',
        record.USER_NAME,
        'system@governance',
        'Automatic removal completed for inactive user: ' || record.USER_NAME,
        NULL,
        NULL,
        'success',
        NULL,
        NULL,
        CURRENT_TIMESTAMP(),
        CURRENT_TIMESTAMP(),
        TRUE;

    EXCEPTION WHEN OTHER THEN
      -- Log error but continue
      INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
      SELECT
        SUBSTRING(UUID_STRING(), 0, 36),
        'auto_user_removal_failed',
        'security',
        'user_management',
        record.USER_NAME,
        'system@governance',
        'Automatic removal FAILED for user: ' || record.USER_NAME,
        NULL,
        NULL,
        'error',
        NULL,
        NULL,
        CURRENT_TIMESTAMP(),
        CURRENT_TIMESTAMP(),
        TRUE;
    END;
  END FOR;

  -- Final log: Cleanup completed
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'weekly_inactive_user_cleanup_completed',
    'security',
    'batch_job',
    'cleanup',
    'system@governance',
    'Weekly automatic inactive user cleanup completed',
    TO_VARIANT(OBJECT_CONSTRUCT(
      'timestamp', CURRENT_TIMESTAMP(),
      'removed_count', (SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.ARCHIVED_USERS WHERE DATE(ARCHIVED_ON) = CURRENT_DATE())
    )),
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;
END;

-- Enable the automatic task
ALTER TASK inactive_user_cleanup_task_auto RESUME;

-- ============================================================================
-- VERIFICATION & MONITORING
-- ============================================================================

-- Check task status
SHOW TASKS LIKE 'inactive_user_cleanup_task_auto';

-- View task schedule
SELECT
    NAME,
    STATE,
    SCHEDULE,
    NEXT_SCHEDULED_TIME
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE NAME = 'INACTIVE_USER_CLEANUP_TASK_AUTO'
ORDER BY QUERY_START_TIME DESC
LIMIT 5;

-- ============================================================================
-- MONITORING QUERIES (Run these to check results)
-- ============================================================================

-- View recently archived users (auto-removed)
-- SELECT USER_NAME, USER_EMAIL, ARCHIVED_ON, METADATA
-- FROM GOVERNANCE.GOVERNANCE.ARCHIVED_USERS
-- WHERE ARCHIVED_ON >= CURRENT_DATE() - INTERVAL '7 days'
-- ORDER BY ARCHIVED_ON DESC;

-- View auto-removal audit logs
-- SELECT EVENT_TYPE, RESOURCE_NAME, ACTION_DESCRIPTION, STATUS, EVENT_TIMESTAMP
-- FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
-- WHERE EVENT_TYPE LIKE '%auto_user_removal%'
-- ORDER BY EVENT_TIMESTAMP DESC
-- LIMIT 20;

-- View inactive users still pending removal
-- SELECT USER_NAME, USER_EMAIL, DAYS_INACTIVE, STATUS
-- FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
-- WHERE DAYS_INACTIVE >= 90
// AND STATUS IN ('active', 'flagged')
// ORDER BY DAYS_INACTIVE DESC;

-- ============================================================================
-- OPTIONAL: DISABLE AUTO-REMOVAL (BACK TO APPROVAL-BASED)
-- ============================================================================

-- If you want to switch back to approval-based removal, run:
-- ALTER TASK inactive_user_cleanup_task_auto SUSPEND;
-- ALTER TASK inactive_user_cleanup_task RESUME;  -- The approval-based task

-- ============================================================================
-- WHAT HAPPENS EACH MONDAY AT MIDNIGHT UTC:
-- ============================================================================
-- 1. Scan for users inactive 90+ days
-- 2. For each inactive user:
--    a. Revoke all roles
--    b. Disable account
--    c. Archive user data
--    d. Log to audit trail
-- 3. Continue on errors (doesn't stop if one user fails)
-- 4. Complete summary logged
--
-- NO APPROVAL NEEDED - FULLY AUTOMATIC!
-- ============================================================================
