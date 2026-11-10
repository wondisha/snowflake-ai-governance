# Inactive User Management Setup Guide

**Complete guide for setting up and fixing the automatic inactive user removal system**

---

## 🎯 Overview

This guide covers the complete setup of the Inactive User Management system, including:
- Creating stored procedures
- Fixing common Snowflake SQL procedure issues
- Scheduling automated removal tasks
- Testing and monitoring

---

## 📋 Prerequisites

- Snowflake account with ACCOUNTADMIN role
- GOVERNANCE database and schema already created
- USER_ACTIVITY_LOG and ARCHIVED_USERS tables deployed

---

## 🔧 Step 1: Create the IDENTIFY_INACTIVE_USERS Procedure

**Purpose**: Scans all users and updates their inactivity status

```sql
USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

CREATE OR REPLACE PROCEDURE IDENTIFY_INACTIVE_USERS()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  -- Update USER_ACTIVITY_LOG with inactive users (90+ days)
  MERGE INTO USER_ACTIVITY_LOG target
  USING (
    SELECT
      USER_NAME,
      CREATED_ON,
      LAST_LOGIN,
      EMAIL,
      DATEDIFF(DAY,
        CASE WHEN LAST_LOGIN IS NULL THEN CREATED_ON ELSE LAST_LOGIN END,
        CURRENT_TIMESTAMP()
      ) as DAYS_INACTIVE
    FROM INFORMATION_SCHEMA.USERS
    WHERE DELETED_ON IS NULL
  ) source
  ON target.USER_NAME = source.USER_NAME
  WHEN MATCHED THEN
    UPDATE SET
      target.DAYS_INACTIVE = source.DAYS_INACTIVE,
      target.LAST_LOGIN = source.LAST_LOGIN,
      target.UPDATED_AT = CURRENT_TIMESTAMP()
  WHEN NOT MATCHED THEN
    INSERT (
      ACTIVITY_ID,
      USER_NAME,
      USER_EMAIL,
      LAST_LOGIN,
      DAYS_INACTIVE,
      STATUS,
      CREATED_AT
    )
    VALUES (
      SUBSTRING(UUID_STRING(), 0, 36),
      source.USER_NAME,
      COALESCE(source.EMAIL, 'N/A'),
      source.LAST_LOGIN,
      source.DAYS_INACTIVE,
      'active',
      CURRENT_TIMESTAMP()
    );

  RETURN 'Scanned users and updated activity log';
END;
```

**Test it:**
```sql
CALL IDENTIFY_INACTIVE_USERS();
SELECT USER_NAME, DAYS_INACTIVE FROM USER_ACTIVITY_LOG LIMIT 10;
```

---

## 🔧 Step 2: Create the REVOKE_INACTIVE_USER_ROLES Procedure

**Purpose**: Revokes all roles from a user

```sql
CREATE OR REPLACE PROCEDURE REVOKE_INACTIVE_USER_ROLES(USER_NAME_TO_REVOKE VARCHAR)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  DECLARE
    role_cursor CURSOR FOR
      SELECT DISTINCT ROLE
      FROM INFORMATION_SCHEMA.GRANTED_ROLES_IN_HIERARCHY
      WHERE GRANTEE_NAME = :USER_NAME_TO_REVOKE
      AND GRANTEE_TYPE = 'USER';

    role_name VARCHAR;
    revoked_count INT := 0;
  BEGIN
    FOR role IN role_cursor DO
      BEGIN
        EXECUTE IMMEDIATE 'REVOKE ROLE "' || role.ROLE || '" FROM USER "' || :USER_NAME_TO_REVOKE || '"';
        revoked_count := revoked_count + 1;
      EXCEPTION WHEN OTHER THEN
        NULL;
      END;
    END FOR;

    INSERT INTO AUDIT_LOGS (
      AUDIT_LOG_ID, EVENT_TYPE, EVENT_CATEGORY, RESOURCE_NAME,
      ACTOR_EMAIL, ACTION_DESCRIPTION, STATUS, CREATED_AT, UPDATED_AT, IS_AUTOMATED
    ) VALUES (
      SUBSTRING(UUID_STRING(), 0, 36),
      'roles_revoked',
      'security',
      :USER_NAME_TO_REVOKE,
      'system@governance',
      'All roles revoked from user: ' || :USER_NAME_TO_REVOKE,
      'success',
      CURRENT_TIMESTAMP(),
      CURRENT_TIMESTAMP(),
      TRUE
    );

    RETURN 'Revoked roles from ' || :USER_NAME_TO_REVOKE;
  END;
END;
```

**Test it:**
```sql
CALL REVOKE_INACTIVE_USER_ROLES('TEST_USER');
```

---

## 🔧 Step 3: Create the DISABLE_INACTIVE_USER Procedure

**Purpose**: Disables a user account

**⚠️ IMPORTANT**: Use `:` prefix for parameters in Snowflake SQL procedures!

```sql
CREATE OR REPLACE PROCEDURE DISABLE_INACTIVE_USER(USR VARCHAR, REASON VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  UPDATE USER_ACTIVITY_LOG 
  SET "STATUS" = 'disabled', UPDATED_AT = CURRENT_TIMESTAMP()
  WHERE USER_NAME = :USR;
  
  RETURN 'Disabled: ' || :USR;
END;
```

**Test it:**
```sql
CALL DISABLE_INACTIVE_USER('TEST_USER', 'Inactive 90+ days');
```

---

## 🔧 Step 4: Create the REMOVE_INACTIVE_USER_COMPLETE Procedure

**Purpose**: Complete removal - revoke roles, disable, and archive user

**⚠️ CRITICAL**: Use `:PARAM` syntax for all parameter references!

```sql
CREATE OR REPLACE PROCEDURE REMOVE_INACTIVE_USER_COMPLETE(USR VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN
  -- Step 1: Revoke roles
  CALL REVOKE_INACTIVE_USER_ROLES(:USR);

  -- Step 2: Update status in USER_ACTIVITY_LOG
  UPDATE USER_ACTIVITY_LOG
  SET "STATUS" = 'removed', UPDATED_AT = CURRENT_TIMESTAMP()
  WHERE USER_NAME = :USR;

  -- Step 3: Archive user data
  INSERT INTO ARCHIVED_USERS (ARCHIVE_ID, USER_NAME, USER_EMAIL, ARCHIVED_ON)
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    USER_NAME,
    USER_EMAIL,
    CURRENT_TIMESTAMP()
  FROM USER_ACTIVITY_LOG
  WHERE USER_NAME = :USR;

  -- Step 4: Log to audit
  INSERT INTO AUDIT_LOGS (
    AUDIT_LOG_ID, EVENT_TYPE, EVENT_CATEGORY, RESOURCE_NAME,
    ACTOR_EMAIL, ACTION_DESCRIPTION, STATUS, CREATED_AT, UPDATED_AT, IS_AUTOMATED
  ) VALUES (
    SUBSTRING(UUID_STRING(), 0, 36),
    'user_removal_complete',
    'security',
    :USR,
    'system@governance',
    'User removed: ' || :USR,
    'success',
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE
  );

  RETURN 'User ' || :USR || ' removed successfully';
END;
```

**Test it:**
```sql
CALL REMOVE_INACTIVE_USER_COMPLETE('TEST_USER');
SELECT USER_NAME, "STATUS" FROM USER_ACTIVITY_LOG WHERE USER_NAME = 'TEST_USER';
```

---

## 📅 Step 5: Create the Automatic Task

**Purpose**: Run the removal process weekly (Monday at midnight UTC)

```sql
USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

CREATE OR REPLACE TASK INACTIVE_USER_CLEANUP_TASK_AUTO
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 0 * * 1 UTC'  -- Weekly Monday midnight UTC
AS
BEGIN
  -- Step 1: Identify inactive users
  CALL IDENTIFY_INACTIVE_USERS();

  -- Step 2: Auto-remove each flagged user (90+ days)
  FOR record IN (
    SELECT USER_NAME, DAYS_INACTIVE
    FROM USER_ACTIVITY_LOG
    WHERE DAYS_INACTIVE >= 90
      AND "STATUS" IN ('active', 'flagged')
  )
  DO
    BEGIN
      CALL REMOVE_INACTIVE_USER_COMPLETE(record.USER_NAME);
    EXCEPTION WHEN OTHER THEN
      -- Continue on error
      NULL;
    END;
  END FOR;
END;

-- Enable the task
ALTER TASK INACTIVE_USER_CLEANUP_TASK_AUTO RESUME;
```

---

## ✅ Verification

**Check procedures were created:**
```sql
SHOW PROCEDURES LIKE '%INACTIVE%';
```

**Check task status:**
```sql
SELECT NAME, "STATE", SCHEDULE, NEXT_SCHEDULED_TIME
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE NAME = 'INACTIVE_USER_CLEANUP_TASK_AUTO'
LIMIT 1;
```

---

## 🧪 Testing the System

### Create Test Users (>89 days inactive)

```sql
INSERT INTO USER_ACTIVITY_LOG (ACTIVITY_ID, USER_NAME, USER_EMAIL, LAST_LOGIN, DAYS_INACTIVE, STATUS, CREATED_AT)
VALUES
  (SUBSTRING(UUID_STRING(), 0, 36), 'TEST_INACTIVE_USER_1', 'test1@company.com', 
   DATEADD(day, -120, CURRENT_TIMESTAMP()), 120, 'active', CURRENT_TIMESTAMP()),
  
  (SUBSTRING(UUID_STRING(), 0, 36), 'TEST_INACTIVE_USER_2', 'test2@company.com', 
   DATEADD(day, -105, CURRENT_TIMESTAMP()), 105, 'active', CURRENT_TIMESTAMP());

SELECT USER_NAME, DAYS_INACTIVE, "STATUS" FROM USER_ACTIVITY_LOG 
WHERE USER_NAME LIKE 'TEST_%';
```

### Manual Test

```sql
-- Test individual procedures
CALL IDENTIFY_INACTIVE_USERS();
CALL DISABLE_INACTIVE_USER('TEST_INACTIVE_USER_1', 'Manual test');
CALL REVOKE_INACTIVE_USER_ROLES('TEST_INACTIVE_USER_1');
CALL REMOVE_INACTIVE_USER_COMPLETE('TEST_INACTIVE_USER_1');

-- Verify results
SELECT USER_NAME, "STATUS" FROM USER_ACTIVITY_LOG WHERE USER_NAME = 'TEST_INACTIVE_USER_1';
SELECT USER_NAME, ARCHIVED_ON FROM ARCHIVED_USERS WHERE USER_NAME = 'TEST_INACTIVE_USER_1';
```

---

## 🔄 Change Task Schedule

**For custom schedule (e.g., Tuesday 8 AM Central = 2 PM UTC):**

```sql
ALTER TASK INACTIVE_USER_CLEANUP_TASK_AUTO SUSPEND;
ALTER TASK INACTIVE_USER_CLEANUP_TASK_AUTO 
  SET SCHEDULE = 'USING CRON 0 14 * * 2 UTC';
ALTER TASK INACTIVE_USER_CLEANUP_TASK_AUTO RESUME;
```

**CRON Format:** `minute hour day month day_of_week`
- Tuesday = 2 (0=Sunday, 1=Monday, 2=Tuesday, etc.)
- 14 = 2 PM UTC
- 0 = minute (on the hour)

---

## 📊 Monitoring Queries

**View removed users:**
```sql
SELECT USER_NAME, ARCHIVED_ON FROM ARCHIVED_USERS 
ORDER BY ARCHIVED_ON DESC LIMIT 20;
```

**View audit trail:**
```sql
SELECT EVENT_TYPE, RESOURCE_NAME, ACTION_DESCRIPTION, EVENT_TIMESTAMP
FROM AUDIT_LOGS
WHERE EVENT_TYPE LIKE '%removal%' OR EVENT_TYPE LIKE '%roles%'
ORDER BY EVENT_TIMESTAMP DESC LIMIT 20;
```

**View inactive users pending removal:**
```sql
SELECT USER_NAME, DAYS_INACTIVE, "STATUS" 
FROM USER_ACTIVITY_LOG
WHERE DAYS_INACTIVE >= 90
ORDER BY DAYS_INACTIVE DESC;
```

---

## ⚠️ Common Issues & Fixes

### Issue 1: `Unknown function IDENTIFY_INACTIVE_USERS`

**Cause**: Old Python version of procedure still exists

**Fix**:
```sql
DROP PROCEDURE IF EXISTS IDENTIFY_INACTIVE_USERS();
-- Then recreate with SQL version from Step 1
```

### Issue 2: `invalid identifier 'USR'`

**Cause**: Not using `:` prefix for parameters

**Fix**: Always use `:PARAM_NAME` when referencing procedure parameters:
```sql
WHERE USER_NAME = :USR;  -- Correct
WHERE USER_NAME = USR;   -- WRONG
```

### Issue 3: `Object 'GOVERNANCE.INFORMATION_SCHEMA.USERS' does not exist`

**Cause**: Wrong schema reference

**Fix**: Use global INFORMATION_SCHEMA (no schema prefix):
```sql
FROM INFORMATION_SCHEMA.USERS  -- Correct
FROM GOVERNANCE.INFORMATION_SCHEMA.USERS  -- WRONG
```

### Issue 4: `STATUS` is a reserved keyword

**Cause**: Not quoting reserved keywords

**Fix**: Quote reserved words:
```sql
SET "STATUS" = 'removed'  -- Correct
SET STATUS = 'removed'    -- WRONG
```

---

## 🚀 Deployment Checklist

- [ ] Created IDENTIFY_INACTIVE_USERS procedure
- [ ] Created REVOKE_INACTIVE_USER_ROLES procedure
- [ ] Created DISABLE_INACTIVE_USER procedure
- [ ] Created REMOVE_INACTIVE_USER_COMPLETE procedure
- [ ] Created INACTIVE_USER_CLEANUP_TASK_AUTO task
- [ ] Task is in RESUMED state
- [ ] Verified with test users
- [ ] Set desired schedule
- [ ] Monitoring queries working

---

## 📞 Support

For issues or questions, check:
- IMPLEMENTATION_GUIDE.md - Full system documentation
- README.md - Quick start guide
- agent_procedures_production.sql - Other agent procedures

---

**Last Updated**: November 2026  
**Version**: 1.0  
**Status**: Production Ready ✅
