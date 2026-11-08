"""
Snowflake Governance Agents DAG
Orchestrates all governance agents using Apache Airflow
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.providers.snowflake.transfers.snowflake_to_slack import SnowflakeToSlackOperator
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import json

# Default arguments
default_args = {
    'owner': 'governance',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 11, 8),
    'email': ['admin@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}

# DAG definition
dag = DAG(
    dag_id='governance_agents_dag',
    description='Snowflake Governance Agents Orchestration',
    default_args=default_args,
    schedule_interval='0 * * * *',  # Every hour
    catchup=False,
    tags=['governance', 'snowflake'],
)

# ============================================================================
# TASK 1: Security Agent (Every 4 hours)
# ============================================================================
security_agent_task = SnowflakeOperator(
    task_id='run_security_agent',
    sql="""
        USE DATABASE GOVERNANCE;
        USE SCHEMA GOVERNANCE;

        -- Execute security agent
        CALL GOVERNANCE.GOVERNANCE.security_agent();

        -- Log execution
        INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
        VALUES (
            SUBSTRING(UUID_STRING(), 0, 36),
            'agent_execution',
            'security',
            'agent',
            'security_agent',
            'system@governance',
            'Security agent executed',
            NULL,
            NULL,
            'success',
            NULL,
            NULL,
            CURRENT_TIMESTAMP(),
            CURRENT_TIMESTAMP(),
            TRUE
        );
    """,
    snowflake_conn_id='snowflake_governance',
    dag=dag,
)

# ============================================================================
# TASK 2: Performance Agent (Every 2 hours)
# ============================================================================
performance_agent_task = SnowflakeOperator(
    task_id='run_performance_agent',
    sql="""
        USE DATABASE GOVERNANCE;
        USE SCHEMA GOVERNANCE;

        -- Execute performance agent
        CALL GOVERNANCE.GOVERNANCE.performance_agent();

        -- Log execution
        INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
        VALUES (
            SUBSTRING(UUID_STRING(), 0, 36),
            'agent_execution',
            'performance',
            'agent',
            'performance_agent',
            'system@governance',
            'Performance agent executed',
            NULL,
            NULL,
            'success',
            NULL,
            NULL,
            CURRENT_TIMESTAMP(),
            CURRENT_TIMESTAMP(),
            TRUE
        );
    """,
    snowflake_conn_id='snowflake_governance',
    dag=dag,
)

# ============================================================================
# TASK 3: Cost Agent (Daily at 6 AM)
# ============================================================================
cost_agent_task = SnowflakeOperator(
    task_id='run_cost_agent',
    sql="""
        USE DATABASE GOVERNANCE;
        USE SCHEMA GOVERNANCE;

        -- Execute cost agent
        CALL GOVERNANCE.GOVERNANCE.cost_agent();

        -- Log execution
        INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
        VALUES (
            SUBSTRING(UUID_STRING(), 0, 36),
            'agent_execution',
            'cost',
            'agent',
            'cost_agent',
            'system@governance',
            'Cost agent executed',
            NULL,
            NULL,
            'success',
            NULL,
            NULL,
            CURRENT_TIMESTAMP(),
            CURRENT_TIMESTAMP(),
            TRUE
        );
    """,
    snowflake_conn_id='snowflake_governance',
    dag=dag,
)

# ============================================================================
# TASK 4: Health Agent (Every 30 minutes)
# ============================================================================
health_agent_task = SnowflakeOperator(
    task_id='run_health_agent',
    sql="""
        USE DATABASE GOVERNANCE;
        USE SCHEMA GOVERNANCE;

        -- Execute health agent
        CALL GOVERNANCE.GOVERNANCE.health_agent();

        -- Log execution
        INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
        VALUES (
            SUBSTRING(UUID_STRING(), 0, 36),
            'agent_execution',
            'health',
            'agent',
            'health_agent',
            'system@governance',
            'Health agent executed',
            NULL,
            NULL,
            'success',
            NULL,
            NULL,
            CURRENT_TIMESTAMP(),
            CURRENT_TIMESTAMP(),
            TRUE
        );
    """,
    snowflake_conn_id='snowflake_governance',
    dag=dag,
)

# ============================================================================
# TASK 5: Spillage Prevention Agent (Every 4 hours)
# ============================================================================
spillage_agent_task = SnowflakeOperator(
    task_id='run_spillage_agent',
    sql="""
        USE DATABASE GOVERNANCE;
        USE SCHEMA GOVERNANCE;

        -- Execute spillage prevention agent
        CALL GOVERNANCE.GOVERNANCE.spillage_agent();

        -- Log execution
        INSERT INTO GOVERNANCE.GOVERNANCE.AUDIT_LOGS
        VALUES (
            SUBSTRING(UUID_STRING(), 0, 36),
            'agent_execution',
            'security',
            'agent',
            'spillage_agent',
            'system@governance',
            'Spillage prevention agent executed',
            NULL,
            NULL,
            'success',
            NULL,
            NULL,
            CURRENT_TIMESTAMP(),
            CURRENT_TIMESTAMP(),
            TRUE
        );
    """,
    snowflake_conn_id='snowflake_governance',
    dag=dag,
)

# ============================================================================
# TASK 6: Generate Daily Report
# ============================================================================
generate_report_task = SnowflakeOperator(
    task_id='generate_daily_report',
    sql="""
        USE DATABASE GOVERNANCE;
        USE SCHEMA GOVERNANCE;

        -- Generate daily governance report
        CREATE OR REPLACE TABLE GOVERNANCE.GOVERNANCE.DAILY_REPORT AS
        SELECT
            CURRENT_DATE as report_date,
            COUNT(DISTINCT INCIDENT_ID) as total_incidents,
            SUM(CASE WHEN STATUS = 'open' THEN 1 ELSE 0 END) as open_incidents,
            COUNT(DISTINCT AGENT_NAME) as active_agents,
            AVG(ERROR_COUNT) as avg_agent_errors
        FROM GOVERNANCE.GOVERNANCE.INCIDENTS
        CROSS JOIN GOVERNANCE.GOVERNANCE.AGENT_STATE
        WHERE DETECTED_TIMESTAMP >= CURRENT_DATE;
    """,
    snowflake_conn_id='snowflake_governance',
    dag=dag,
)

# ============================================================================
# TASK DEPENDENCIES
# ============================================================================
[security_agent_task, performance_agent_task, cost_agent_task,
 health_agent_task, spillage_agent_task] >> generate_report_task

# ============================================================================
# MONITORING: Python function to check agent health
# ============================================================================
def check_agent_health():
    """Check if all agents are healthy"""
    import logging
    logger = logging.getLogger(__name__)

    # This would connect to Snowflake and check agent status
    logger.info("Checking governance agent health...")
    # Implementation would query GOVERNANCE.AGENT_STATE

check_health_task = PythonOperator(
    task_id='check_agent_health',
    python_callable=check_agent_health,
    dag=dag,
)

generate_report_task >> check_health_task
