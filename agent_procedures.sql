-- Snowflake Governance Agents - Mock Procedures for Testing
-- These procedures log agent activity to the audit trail
-- Production procedures should replace these with real logic

USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

-- Create mock Security Agent procedure
CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.SECURITY_AGENT()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'security_check',
    'security',
    'agent',
    'security_agent',
    'system@governance',
    'Security agent check completed',
    NULL, NULL, 'success', NULL, NULL,
    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE;

  RETURN 'Security Agent completed';
END;
$$;

-- Create mock Performance Agent procedure
CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.PERFORMANCE_AGENT()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'performance_check',
    'performance',
    'agent',
    'performance_agent',
    'system@governance',
    'Performance agent check completed',
    NULL, NULL, 'success', NULL, NULL,
    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE;

  RETURN 'Performance Agent completed';
END;
$$;

-- Create mock Cost Agent procedure
CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.COST_AGENT()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'cost_check',
    'cost',
    'agent',
    'cost_agent',
    'system@governance',
    'Cost agent check completed',
    NULL, NULL, 'success', NULL, NULL,
    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE;

  RETURN 'Cost Agent completed';
END;
$$;

-- Create mock Health Agent procedure
CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.HEALTH_AGENT()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'health_check',
    'health',
    'agent',
    'health_agent',
    'system@governance',
    'Health agent check completed',
    NULL, NULL, 'success', NULL, NULL,
    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE;

  RETURN 'Health Agent completed';
END;
$$;

-- Create mock Spillage Agent procedure
CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.SPILLAGE_AGENT()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'spillage_check',
    'security',
    'agent',
    'spillage_agent',
    'system@governance',
    'Spillage prevention agent check completed',
    NULL, NULL, 'success', NULL, NULL,
    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE;

  RETURN 'Spillage Agent completed';
END;
$$;

-- Test all agents
-- CALL GOVERNANCE.GOVERNANCE.SECURITY_AGENT();
-- CALL GOVERNANCE.GOVERNANCE.PERFORMANCE_AGENT();
-- CALL GOVERNANCE.GOVERNANCE.COST_AGENT();
-- CALL GOVERNANCE.GOVERNANCE.HEALTH_AGENT();
-- CALL GOVERNANCE.GOVERNANCE.SPILLAGE_AGENT();

-- View results
-- SELECT EVENT_TYPE, EVENT_CATEGORY, STATUS, EVENT_TIMESTAMP
-- FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
-- WHERE EVENT_TYPE LIKE '%_check'
-- ORDER BY EVENT_TIMESTAMP DESC
-- LIMIT 10;
