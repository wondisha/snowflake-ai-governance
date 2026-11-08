"""
Snowflake Snowpark Client - Core connector for all Snowflake operations.
Provides session management, query execution, and common operations.
"""

from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, count, sum as snowpark_sum
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType
from snowflake.connector import connect
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration."""
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: Optional[str] = None


class SnowparkClient:
    """
    Snowflake Snowpark client for governance agent operations.
    Handles session management, query execution, and data operations.
    """

    def __init__(self, config: SnowflakeConfig):
        """Initialize Snowpark client with connection config."""
        self.config = config
        self.session = None
        self.connect()

    def connect(self) -> None:
        """Establish Snowflake session."""
        try:
            self.session = Session.builder.configs({
                "account": self.config.account,
                "user": self.config.user,
                "password": self.config.password,
                "warehouse": self.config.warehouse,
                "database": self.config.database,
                "schema": self.config.schema,
                "role": self.config.role or "accountadmin"
            }).create()
            logger.info(f"Connected to Snowflake account: {self.config.account}")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise

    def close(self) -> None:
        """Close Snowflake session."""
        if self.session:
            self.session.close()
            logger.info("Closed Snowflake session")

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dicts.

        Args:
            sql: SQL query string

        Returns:
            List of result rows as dictionaries
        """
        try:
            result = self.session.sql(sql).collect()
            return [row.as_dict() for row in result]
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

    def execute_query_dataframe(self, sql: str):
        """Execute SQL query and return Snowpark DataFrame."""
        try:
            return self.session.sql(sql)
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

    # ========================================================================
    # WAREHOUSE OPERATIONS
    # ========================================================================

    def get_warehouse_metrics(self, warehouse_name: str) -> Dict[str, Any]:
        """Get current warehouse metrics (CPU, memory, storage, queue)."""
        sql = f"""
        SELECT
            warehouse_name,
            warehouse_size,
            state,
            running,
            queued,
            created_on,
            updated_on
        FROM information_schema.warehouses
        WHERE warehouse_name = '{warehouse_name}'
        """
        result = self.execute_query(sql)
        return result[0] if result else {}

    def list_warehouses(self) -> List[Dict[str, Any]]:
        """List all warehouses in account."""
        sql = """
        SELECT warehouse_name, warehouse_size, state, created_on
        FROM information_schema.warehouses
        ORDER BY warehouse_name
        """
        return self.execute_query(sql)

    def suspend_warehouse(self, warehouse_name: str) -> bool:
        """Suspend a warehouse."""
        try:
            self.session.sql(f"ALTER WAREHOUSE {warehouse_name} SUSPEND").collect()
            logger.info(f"Suspended warehouse: {warehouse_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to suspend warehouse {warehouse_name}: {str(e)}")
            return False

    def resume_warehouse(self, warehouse_name: str) -> bool:
        """Resume a warehouse."""
        try:
            self.session.sql(f"ALTER WAREHOUSE {warehouse_name} RESUME").collect()
            logger.info(f"Resumed warehouse: {warehouse_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume warehouse {warehouse_name}: {str(e)}")
            return False

    def set_warehouse_auto_suspend(self, warehouse_name: str, minutes: int) -> bool:
        """Set warehouse auto-suspend timeout."""
        try:
            self.session.sql(f"ALTER WAREHOUSE {warehouse_name} SET AUTO_SUSPEND = {minutes}").collect()
            logger.info(f"Set {warehouse_name} auto-suspend to {minutes} minutes")
            return True
        except Exception as e:
            logger.error(f"Failed to set auto-suspend: {str(e)}")
            return False

    def scale_warehouse(self, warehouse_name: str, size: str) -> bool:
        """Scale warehouse to new size (XS, S, M, L, XL, etc.)."""
        try:
            self.session.sql(f"ALTER WAREHOUSE {warehouse_name} SET WAREHOUSE_SIZE = '{size}'").collect()
            logger.info(f"Scaled {warehouse_name} to size {size}")
            return True
        except Exception as e:
            logger.error(f"Failed to scale warehouse: {str(e)}")
            return False

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    def get_query_history(self, warehouse_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get query execution history for warehouse."""
        sql = f"""
        SELECT
            query_id,
            query_text,
            database_name,
            schema_name,
            user_name,
            warehouse_name,
            execution_status,
            error_message,
            start_time,
            end_time,
            total_elapsed_time,
            rows_produced,
            bytes_scanned
        FROM snowflake.account_usage.query_history
        WHERE warehouse_name = '{warehouse_name}'
            AND start_time >= CURRENT_TIMESTAMP() - INTERVAL '{hours} hours'
        ORDER BY start_time DESC
        LIMIT 1000
        """
        return self.execute_query(sql)

    def get_slow_queries(self, threshold_seconds: int = 30, hours: int = 24) -> List[Dict[str, Any]]:
        """Get queries that exceeded execution time threshold."""
        sql = f"""
        SELECT
            query_id,
            query_text,
            user_name,
            warehouse_name,
            database_name,
            execution_status,
            start_time,
            TIMESTAMPDIFF(second, start_time, end_time) as execution_seconds,
            rows_produced,
            bytes_scanned,
            bytes_spilled_to_local_storage,
            bytes_spilled_to_remote_storage
        FROM snowflake.account_usage.query_history
        WHERE TIMESTAMPDIFF(second, start_time, end_time) > {threshold_seconds}
            AND start_time >= CURRENT_TIMESTAMP() - INTERVAL '{hours} hours'
        ORDER BY execution_seconds DESC
        LIMIT 100
        """
        return self.execute_query(sql)

    def get_query_profile(self, query_id: str) -> Dict[str, Any]:
        """Get detailed query execution profile."""
        sql = f"""
        SELECT
            query_id,
            user_name,
            warehouse_name,
            warehouse_size,
            execution_time,
            queued_provisioning_time,
            queued_repair_time,
            list_external_files_time,
            compilation_time,
            bytes_read_from_result_cache,
            bytes_read_from_cache,
            bytes_read_from_storage,
            bytes_sent_over_the_network,
            compilation_time,
            data_scanned_in_bytes,
            data_written_to_result,
            rows_produced,
            rows_inserted,
            rows_deleted,
            rows_unloaded,
            bytes_deleted,
            bytes_written_to_stages
        FROM snowflake.account_usage.query_history
        WHERE query_id = '{query_id}'
        """
        result = self.execute_query(sql)
        return result[0] if result else {}

    def abort_query(self, query_id: str) -> bool:
        """Abort a running query."""
        try:
            self.session.sql(f"SELECT SYSTEM$CANCEL_QUERY('{query_id}')").collect()
            logger.info(f"Aborted query: {query_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to abort query {query_id}: {str(e)}")
            return False

    # ========================================================================
    # SECURITY & PERMISSIONS
    # ========================================================================

    def list_users(self) -> List[Dict[str, Any]]:
        """List all users in account."""
        sql = """
        SELECT
            name as user_name,
            created_on,
            disabled,
            email,
            display_name,
            last_success_login
        FROM snowflake.account_usage.users
        ORDER BY created_on DESC
        """
        return self.execute_query(sql)

    def list_roles(self) -> List[Dict[str, Any]]:
        """List all roles in account."""
        sql = """
        SELECT
            name as role_name,
            created_on,
            comment
        FROM information_schema.roles
        WHERE name NOT IN ('ACCOUNTADMIN', 'SECURITYADMIN', 'USERADMIN', 'SYSADMIN', 'PUBLIC')
        ORDER BY created_on DESC
        """
        return self.execute_query(sql)

    def get_user_permissions(self, user_name: str) -> List[Dict[str, Any]]:
        """Get roles and permissions for a user."""
        sql = f"""
        SELECT
            role_name,
            granted_on,
            privilege
        FROM information_schema.role_grants
        WHERE grantee_name = '{user_name}'
        ORDER BY role_name
        """
        return self.execute_query(sql)

    def grant_role_to_user(self, user_name: str, role_name: str) -> bool:
        """Grant role to user."""
        try:
            self.session.sql(f"GRANT ROLE {role_name} TO USER {user_name}").collect()
            logger.info(f"Granted {role_name} to {user_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to grant role: {str(e)}")
            return False

    def revoke_role_from_user(self, user_name: str, role_name: str) -> bool:
        """Revoke role from user."""
        try:
            self.session.sql(f"REVOKE ROLE {role_name} FROM USER {user_name}").collect()
            logger.info(f"Revoked {role_name} from {user_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke role: {str(e)}")
            return False

    # ========================================================================
    # DATA OPERATIONS
    # ========================================================================

    def get_table_schema(self, database_name: str, schema_name: str, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema (columns, types)."""
        sql = f"""
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_catalog = '{database_name}'
            AND table_schema = '{schema_name}'
            AND table_name = '{table_name}'
        ORDER BY ordinal_position
        """
        return self.execute_query(sql)

    def get_table_size(self, database_name: str, schema_name: str, table_name: str) -> Dict[str, Any]:
        """Get table statistics (row count, size)."""
        sql = f"""
        SELECT
            table_catalog,
            table_schema,
            table_name,
            row_count,
            bytes as size_bytes,
            ROUND(bytes / (1024.0 * 1024 * 1024), 2) as size_gb
        FROM snowflake.account_usage.table_storage_metrics
        WHERE table_catalog = '{database_name}'
            AND table_schema = '{schema_name}'
            AND table_name = '{table_name}'
        """
        result = self.execute_query(sql)
        return result[0] if result else {}

    def sample_table_data(self, database_name: str, schema_name: str, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Sample data from a table."""
        sql = f"SELECT * FROM {database_name}.{schema_name}.{table_name} LIMIT {limit}"
        return self.execute_query(sql)

    # ========================================================================
    # COST & USAGE
    # ========================================================================

    def get_warehouse_costs(self, warehouse_name: str, days: int = 7) -> Dict[str, Any]:
        """Get cost information for warehouse."""
        sql = f"""
        SELECT
            warehouse_name,
            DATE(start_time) as cost_date,
            SUM(credits_used) as daily_credits
        FROM snowflake.account_usage.warehouse_metering_history
        WHERE warehouse_name = '{warehouse_name}'
            AND start_time >= CURRENT_TIMESTAMP() - INTERVAL '{days} days'
        GROUP BY warehouse_name, DATE(start_time)
        ORDER BY cost_date DESC
        """
        return self.execute_query(sql)

    def get_total_account_costs(self, days: int = 30) -> Dict[str, Any]:
        """Get total credit consumption for account."""
        sql = f"""
        SELECT
            SUM(credits_used) as total_credits,
            AVG(credits_used) as avg_daily_credits,
            MAX(credits_used) as peak_daily_credits
        FROM snowflake.account_usage.warehouse_metering_history
        WHERE start_time >= CURRENT_TIMESTAMP() - INTERVAL '{days} days'
        """
        result = self.execute_query(sql)
        return result[0] if result else {}

    # ========================================================================
    # GOVERNANCE SCHEMA OPERATIONS
    # ========================================================================

    def insert_audit_log(self, audit_data: Dict[str, Any]) -> bool:
        """Insert audit log entry into governance schema."""
        try:
            columns = ', '.join(audit_data.keys())
            values = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in audit_data.values()])
            sql = f"INSERT INTO governance.audit_logs ({columns}) VALUES ({values})"
            self.session.sql(sql).collect()
            logger.info(f"Inserted audit log: {audit_data.get('event_type')}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert audit log: {str(e)}")
            return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get pending approval requests."""
        sql = """
        SELECT *
        FROM governance.approval_requests
        WHERE status = 'pending'
        ORDER BY priority DESC, created_at ASC
        """
        return self.execute_query(sql)

    def update_approval_status(self, request_id: str, status: str, approver_email: str, comments: str = "") -> bool:
        """Update approval request status."""
        try:
            sql = f"""
            UPDATE governance.approval_requests
            SET status = '{status}',
                approved_by = '{approver_email}',
                approval_comments = '{comments}',
                approved_at = CURRENT_TIMESTAMP()
            WHERE request_id = '{request_id}'
            """
            self.session.sql(sql).collect()
            logger.info(f"Updated approval {request_id} to {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update approval: {str(e)}")
            return False

    def get_agent_state(self, agent_name: str) -> Dict[str, Any]:
        """Get current agent state and health."""
        sql = f"""
        SELECT *
        FROM governance.agent_state
        WHERE agent_name = '{agent_name}'
        """
        result = self.execute_query(sql)
        return result[0] if result else {}

    def update_agent_state(self, agent_name: str, state_data: Dict[str, Any]) -> bool:
        """Update agent state and health metrics."""
        try:
            set_clauses = ', '.join([f"{k} = {v if isinstance(v, (int, float)) else f\"'{v}'\""} for k, v in state_data.items()])
            sql = f"""
            UPDATE governance.agent_state
            SET {set_clauses}, updated_at = CURRENT_TIMESTAMP()
            WHERE agent_name = '{agent_name}'
            """
            self.session.sql(sql).collect()
            logger.info(f"Updated agent state for {agent_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update agent state: {str(e)}")
            return False
