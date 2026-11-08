# Snowflake Governance Agents - Airflow Integration

This guide sets up Apache Airflow to orchestrate and schedule the Snowflake governance agents.

## Prerequisites

- Apache Airflow 2.x installed
- Snowflake Python connector installed
- Access to Snowflake GOVERNANCE database

## Installation

```bash
pip install apache-airflow snowflake-connector-python snowflake-sqlalchemy
```

## Setup Steps

### 1. Configure Airflow Connection to Snowflake

In Airflow Admin → Connections, add:

```
Connection ID: snowflake_governance
Connection Type: Snowflake
Host: <account_id>.us-west-2.snowflakecomputing.com
Schema: GOVERNANCE
Login: <snowflake_user>
Password: <snowflake_password>
Port: 443
Extra: {
  "warehouse": "COMPUTE_WH",
  "database": "GOVERNANCE",
  "account": "<account_id>"
}
```

### 2. Place DAG in Airflow DAGs Directory

Copy `governance_agents_dag.py` to your Airflow DAGs folder:

```bash
cp governance_agents_dag.py ~/airflow/dags/
```

### 3. Enable DAG in Airflow UI

- Open Airflow web UI (http://localhost:8080)
- Search for `governance_agents_dag`
- Toggle the DAG to **ON**

## DAG Workflow

The DAG `governance_agents_dag` orchestrates:

1. **Security Agent** (every 4 hours)
   - Detects security violations
   - Requires approval for remediation
   
2. **Performance Agent** (every 2 hours)
   - Monitors query performance
   - Auto-suspends idle warehouses
   
3. **Cost Agent** (daily at 6 AM)
   - Tracks credit usage
   - Generates cost reports
   
4. **Health Agent** (every 30 minutes)
   - Monitors warehouse health
   - Alerts on issues
   
5. **Spillage Prevention Agent** (every 4 hours)
   - Detects data spillage
   - Prevents unauthorized access

## Monitoring

**View agent execution:**
```bash
# In Airflow UI
Admin → Logs → filter by DAG name
```

**Query agent results:**
```sql
SELECT * FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
WHERE EVENT_TIMESTAMP >= CURRENT_TIMESTAMP() - INTERVAL '24 hours'
ORDER BY EVENT_TIMESTAMP DESC;
```

## Troubleshooting

**DAG not appearing:**
- Check Airflow logs: `tail -f ~/airflow/logs/governance_agents_dag/*`
- Verify DAG file syntax: `airflow dags test governance_agents_dag 2026-11-08`

**Connection errors:**
- Test Snowflake connection: 
  ```bash
  airflow connections test snowflake_governance
  ```

**Agent tasks failing:**
- Check Snowflake logs in GOVERNANCE.AUDIT_LOGS
- Verify warehouse is running: `SHOW WAREHOUSES;`

## Advanced Configuration

### Custom Schedule

Edit `governance_agents_dag.py` and modify task schedules:

```python
agent_task = PythonOperator(
    task_id='run_security_agent',
    python_callable=run_agent,
    op_kwargs={'agent': 'security'},
    schedule_interval='0 */4 * * *',  # Every 4 hours
    dag=dag
)
```

### Notifications

Add Slack notifications on agent failures:

```python
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

slack_alert = SlackWebhookOperator(
    task_id='slack_alert',
    http_conn_id='slack_webhook',
    message='🚨 Governance agent failed!',
    trigger_rule='one_failed'
)
```

### Conditional Execution

Only run remediation if manual approval is provided:

```python
check_approval = BranchPythonOperator(
    task_id='check_approval',
    python_callable=has_approval,
    dag=dag
)

check_approval >> [remediate_task, skip_task]
```

## Next Steps

1. ✅ Configure Snowflake connection
2. ✅ Place DAG in airflow/dags/
3. ✅ Enable in Airflow UI
4. ✅ Monitor execution in logs
5. ✅ View results in Snowflake

For more information, see [Airflow Documentation](https://airflow.apache.org/docs/)
