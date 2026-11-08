-- ============================================================================
-- APPROVAL WORKFLOW FOR HIGH-RISK CHANGES
-- ============================================================================

USE DATABASE GOVERNANCE;
USE SCHEMA GOVERNANCE;

-- ============================================================================
-- STEP 2A: Create Approval Request Procedure
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.CREATE_APPROVAL_REQUEST(
    p_request_type VARCHAR,
    p_resource_name VARCHAR,
    p_description VARCHAR,
    p_risk_level VARCHAR,
    p_requestor_email VARCHAR,
    p_required_approvers ARRAY
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
  v_request_id VARCHAR;
  v_sla_hours INT;
  v_expires_at TIMESTAMP;
BEGIN
  -- Determine SLA based on risk level
  v_sla_hours := CASE
    WHEN p_risk_level = 'critical' THEN 2
    WHEN p_risk_level = 'high' THEN 4
    WHEN p_risk_level = 'medium' THEN 8
    ELSE 24
  END;

  v_expires_at := CURRENT_TIMESTAMP() + INTERVAL 'h hour'(v_sla_hours);
  v_request_id := SUBSTRING(UUID_STRING(), 0, 36);

  -- Create approval request
  INSERT INTO GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS (
    REQUEST_ID,
    REQUEST_TYPE,
    RESOURCE_NAME,
    DESCRIPTION,
    RISK_LEVEL,
    REQUESTOR_EMAIL,
    STATUS,
    REQUEST_CREATED_AT,
    REQUEST_EXPIRES_AT,
    APPROVAL_NEEDED_COUNT,
    APPROVALS_RECEIVED_COUNT
  )
  VALUES (
    v_request_id,
    p_request_type,
    p_resource_name,
    p_description,
    p_risk_level,
    p_requestor_email,
    'pending',
    CURRENT_TIMESTAMP(),
    v_expires_at,
    ARRAY_SIZE(p_required_approvers),
    0
  );

  -- Log audit entry
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'approval_requested',
    'governance',
    'request',
    v_request_id,
    p_requestor_email,
    'Approval requested for: ' || p_description,
    TO_VARIANT(OBJECT_CONSTRUCT(
      'risk_level', p_risk_level,
      'sla_hours', v_sla_hours,
      'required_approvers', ARRAY_SIZE(p_required_approvers)
    )),
    NULL,
    'success',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE;

  RETURN 'Approval request created: ' || v_request_id;
END;
$$;

-- ============================================================================
-- STEP 2B: Create Approval Handler
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.APPROVE_REQUEST(
    p_request_id VARCHAR,
    p_approver_email VARCHAR,
    p_approved BOOLEAN,
    p_comments VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
  v_current_approvals INT;
  v_needed_approvals INT;
  v_request_record RECORD;
BEGIN
  -- Get current request status
  FOR v_request_record IN (
    SELECT REQUEST_ID, STATUS, APPROVALS_RECEIVED_COUNT, APPROVAL_NEEDED_COUNT
    FROM GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
    WHERE REQUEST_ID = p_request_id
  )
  DO
    v_current_approvals := v_request_record.APPROVALS_RECEIVED_COUNT;
    v_needed_approvals := v_request_record.APPROVAL_NEEDED_COUNT;

    IF p_approved THEN
      -- Increment approval count
      UPDATE GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
      SET APPROVALS_RECEIVED_COUNT = APPROVALS_RECEIVED_COUNT + 1
      WHERE REQUEST_ID = p_request_id;

      -- Check if all approvals received
      IF (v_current_approvals + 1) >= v_needed_approvals THEN
        UPDATE GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
        SET STATUS = 'approved'
        WHERE REQUEST_ID = p_request_id;
      END IF;
    ELSE
      -- Reject the request
      UPDATE GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
      SET STATUS = 'rejected',
          REJECTION_REASON = p_comments
      WHERE REQUEST_ID = p_request_id;
    END IF;

    -- Log approval
    INSERT INTO GOVERNANCE.GOVERNANCE.APPROVAL_HISTORY (
      APPROVAL_ID, REQUEST_ID, APPROVER_EMAIL, APPROVED, COMMENTS, APPROVAL_TIMESTAMP
    )
    VALUES (
      SUBSTRING(UUID_STRING(), 0, 36),
      p_request_id,
      p_approver_email,
      p_approved,
      p_comments,
      CURRENT_TIMESTAMP()
    );

    -- Log audit entry
    INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
    SELECT
      SUBSTRING(UUID_STRING(), 0, 36),
      CASE WHEN p_approved THEN 'approval_approved' ELSE 'approval_rejected' END,
      'governance',
      'request',
      p_request_id,
      p_approver_email,
      CASE WHEN p_approved THEN 'Request approved' ELSE 'Request rejected' END || ': ' || p_comments,
      NULL,
      NULL,
      'success',
      NULL,
      NULL,
      CURRENT_TIMESTAMP(),
      CURRENT_TIMESTAMP(),
      TRUE;
  END FOR;

  RETURN 'Approval processed';
END;
$$;

-- ============================================================================
-- STEP 2C: Monitor Pending Approvals & Auto-Reject Expired
-- ============================================================================

CREATE OR REPLACE PROCEDURE GOVERNANCE.GOVERNANCE.CHECK_APPROVAL_SLA()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
  -- Auto-reject expired approvals
  UPDATE GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
  SET STATUS = 'expired',
      REJECTION_REASON = 'SLA timeout - no approval received'
  WHERE STATUS = 'pending'
    AND REQUEST_EXPIRES_AT < CURRENT_TIMESTAMP();

  -- Log SLA breaches
  INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
  SELECT
    SUBSTRING(UUID_STRING(), 0, 36),
    'sla_breached',
    'governance',
    'request',
    REQUEST_ID,
    'system@governance',
    'Approval SLA expired for request: ' || REQUEST_ID,
    TO_VARIANT(OBJECT_CONSTRUCT(
      'expired_at', REQUEST_EXPIRES_AT,
      'risk_level', RISK_LEVEL
    )),
    NULL,
    'warning',
    NULL,
    NULL,
    CURRENT_TIMESTAMP(),
    CURRENT_TIMESTAMP(),
    TRUE
  FROM GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS
  WHERE STATUS = 'expired'
    AND REQUEST_EXPIRES_AT >= CURRENT_TIMESTAMP() - INTERVAL '1 hour';

  RETURN 'SLA check completed';
END;
$$;

-- ============================================================================
-- STEP 2D: Schedule SLA Monitoring
-- ============================================================================

CREATE OR REPLACE TASK approval_sla_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 * * * * UTC'  -- Every hour
AS
  CALL GOVERNANCE.GOVERNANCE.CHECK_APPROVAL_SLA();

ALTER TASK approval_sla_task RESUME;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SHOW TASKS IN SCHEMA GOVERNANCE LIKE 'approval%';
