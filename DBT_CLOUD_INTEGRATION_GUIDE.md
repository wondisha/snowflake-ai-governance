# Snowflake Governance Agents - dbt Cloud Integration

This guide sets up dbt Cloud to orchestrate and schedule the Snowflake governance agents.

## Prerequisites

- dbt Cloud account (https://cloud.getdbt.com)
- dbt project connected to Snowflake
- Access to GOVERNANCE database

## Setup Steps

### 1. Create dbt Project Structure

```bash
dbt init governance_agents
cd governance_agents
```

### 2. Configure dbt_project.yml

Add to `dbt_project.yml`:

```yaml
name: 'governance_agents'
version: '1.0.0'
config-version: 2

profile: 'governance'

model-paths: ["models"]
analysis-paths: ["analyses"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]
target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

# Governance agent models
models:
  governance_agents:
    materialized: view
    database: GOVERNANCE
    schema: governance
    pre-hook: "{{ run_governance_agents() }}"
```

### 3. Create Governance Agent Macros

Create `macros/governance_agents.sql`:

```sql
{% macro run_governance_agents() %}
    -- Security Agent
    {% if execute %}
        {% set security_result = run_query("CALL GOVERNANCE.GOVERNANCE.security_agent()") %}
        {{ log("Security Agent executed", info=true) }}
    {% endif %}

    -- Performance Agent
    {% if execute %}
        {% set perf_result = run_query("CALL GOVERNANCE.GOVERNANCE.performance_agent()") %}
        {{ log("Performance Agent executed", info=true) }}
    {% endif %}

    -- Health Agent
    {% if execute %}
        {% set health_result = run_query("CALL GOVERNANCE.GOVERNANCE.health_agent()") %}
        {{ log("Health Agent executed", info=true) }}
    {% endif %}

    -- Cost Agent
    {% if execute %}
        {% set cost_result = run_query("CALL GOVERNANCE.GOVERNANCE.cost_agent()") %}
        {{ log("Cost Agent executed", info=true) }}
    {% endif %}

    -- Spillage Agent
    {% if execute %}
        {% set spillage_result = run_query("CALL GOVERNANCE.GOVERNANCE.spillage_agent()") %}
        {{ log("Spillage Agent executed", info=true) }}
    {% endif %}
{% endmacro %}

{% macro run_governance_agents_scheduled() %}
    -- Execute all agents
    {{ run_governance_agents() }}
{% endmacro %}
```

### 4. Create dbt Models for Agent Monitoring

Create `models/governance/agent_monitoring.sql`:

```sql
SELECT
    AGENT_NAME,
    AGENT_TYPE,
    EXECUTION_STATUS,
    LAST_SUCCESSFUL_EXECUTION,
    ERROR_COUNT,
    IS_ENABLED,
    CURRENT_TIMESTAMP() as checked_at
FROM {{ source('governance', 'agent_state') }}
WHERE IS_ENABLED = TRUE
ORDER BY LAST_SUCCESSFUL_EXECUTION DESC
```

Create `models/sources.yml`:

```yaml
version: 2

sources:
  - name: governance
    database: GOVERNANCE
    schema: GOVERNANCE
    tables:
      - name: agent_state
        columns:
          - name: agent_id
            description: Unique agent identifier
      - name: audit_logs
        description: Governance audit trail
      - name: incidents
        description: Governance incidents
```

### 5. Set Up dbt Cloud Job

In dbt Cloud Console:

1. **Navigate to:** Jobs → Create Job
2. **Configure:**
   - Job name: `governance_agents_daily`
   - Command: `dbt run --models governance_agents`
   - Schedule: Daily at 6 AM UTC
   - Run on: Production environment

3. **Add Notifications:**
   - Slack webhook on failure
   - Email notifications

### 6. Create Scheduled Job

```bash
dbt cloud job create \
  --account-id <account_id> \
  --project-id <project_id> \
  --job-name governance_agents_daily \
  --environment-id <env_id> \
  --dbt-command "dbt run --models governance_agents" \
  --schedule "0 6 * * *"
```

## Job Execution Flow

```
dbt Cloud Job Trigger
    ↓
Run dbt Models
    ↓
Execute Pre-hooks (Agents)
    ↓
Generate Agent Reports
    ↓
Update Audit Logs
    ↓
Notification (Slack/Email)
```

## Monitoring Agent Execution

### View dbt Cloud Job Runs

```bash
# List recent runs
dbt cloud job list-runs --job-id <job_id> --limit 10

# Get run details
dbt cloud run get --run-id <run_id>
```

### Query Agent Execution History

```sql
-- Last 10 agent executions
SELECT
    EVENT_TIMESTAMP,
    EVENT_TYPE,
    EVENT_CATEGORY,
    ACTOR_EMAIL,
    STATUS,
    ERROR_MESSAGE
FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
WHERE EVENT_CATEGORY = 'governance'
ORDER BY EVENT_TIMESTAMP DESC
LIMIT 10;
```

## Integration with dbt Tests

Add data quality tests in `tests/governance_tests.sql`:

```sql
-- Test 1: Verify agents are executing
SELECT COUNT(*) as agent_count
FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
WHERE IS_ENABLED = TRUE
  AND LAST_SUCCESSFUL_EXECUTION >= CURRENT_TIMESTAMP() - INTERVAL '24 hours'
HAVING COUNT(*) < 3  -- Alert if < 3 agents ran successfully
```

## CI/CD Integration

### GitHub Actions + dbt Cloud

Create `.github/workflows/governance-dbt.yml`:

```yaml
name: Governance dbt Job
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:

jobs:
  dbt-run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run dbt Cloud Job
        run: |
          curl -X POST https://cloud.getdbt.com/api/v2/accounts/
          {account_id}/runs/ \
            -H "Authorization: Bearer ${{ secrets.DBT_CLOUD_API_TOKEN }}" \
            -d '{"job_definition_id": "'"$DBT_JOB_ID"'", "cause": "GitHub Actions"}'
        env:
          DBT_CLOUD_API_TOKEN: ${{ secrets.DBT_CLOUD_API_TOKEN }}
          DBT_JOB_ID: ${{ secrets.DBT_JOB_ID }}
```

## Troubleshooting

**Job fails to run:**
1. Check dbt Cloud logs
2. Verify Snowflake connection
3. Test macro manually: `dbt run-operation run_governance_agents_scheduled`

**Agents not executing:**
1. Verify agent procedures exist in Snowflake
2. Check agent permissions
3. Review AUDIT_LOGS for errors

**Notifications not sending:**
1. Test Slack webhook
2. Verify email configuration
3. Check dbt Cloud notification settings

## Advanced: Custom dbt Models for Agents

Create governance metric models in `models/governance/metrics.sql`:

```sql
-- Agent Performance Metrics
SELECT
    DATE(LAST_SUCCESSFUL_EXECUTION) as execution_date,
    AGENT_TYPE,
    COUNT(*) as executions,
    AVG(ERROR_COUNT) as avg_errors,
    MAX(ITEMS_DETECTED) as max_items_detected
FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
GROUP BY DATE(LAST_SUCCESSFUL_EXECUTION), AGENT_TYPE
ORDER BY execution_date DESC
```

## Next Steps

1. ✅ Set up dbt Cloud project
2. ✅ Create agent macros
3. ✅ Configure scheduled job
4. ✅ Set up notifications
5. ✅ Monitor executions
6. ✅ Add data quality tests

For more information, see [dbt Cloud Documentation](https://docs.getdbt.com/docs/dbt-cloud/cloud-quickstart)
