# 🚀 Automated Deployment Guide
## Deploy Snowflake Governance System (All 5 Phases)

---

## Overview

This guide automates deploying all 5 phases of the Snowflake Governance System to your environment.

**Three Scripts Provided:**
1. `validate_deployment.py` - Pre & post-deployment validation
2. `deploy.py` - Main deployment orchestrator
3. `deployment_config.json` - Configuration file (customize for your environment)

---

## Prerequisites

### 1. Install Python Dependencies

```bash
pip install snowflake-connector-python numpy pyyaml requests fastapi uvicorn
```

### 2. Have Snowflake Credentials Ready

You'll need:
- Account ID (e.g., `xy12345.us-west-2`)
- Username
- Password
- Warehouse name (e.g., `COMPUTE_WH`)
- Database name for governance

### 3. Snowflake Role & Permissions

Your user should have:
- `SYSADMIN` role (or similar)
- Permission to create databases/schemas/tables
- Permission to create procedures/functions
- Warehouse access

---

## Step 1: Configure Deployment

### Edit `deployment_config.json`

```json
{
  "snowflake": {
    "account": "xy12345.us-west-2",      ← Your account ID
    "user": "your_username",              ← Your username
    "password": "your_password",          ← Your password
    "warehouse": "COMPUTE_WH",            ← Your warehouse
    "database": "GOVERNANCE",             ← New database name
    "schema": "PUBLIC",                   ← New schema name
    "role": "SYSADMIN"                    ← Your role
  },
  "deployment": {
    "phases": [1, 2, 3, 4, 5],           ← Which phases to deploy
    "dry_run": false,                     ← true = test only
    "backup_before_deploy": true,         ← Create backup first
    "skip_validation": false              ← Run validation checks
  },
  "integrations": {
    "slack": {"enabled": false},          ← Optional: enable if you have Slack bot
    "servicenow": {"enabled": false},     ← Optional integrations
    "datadog": {"enabled": false},
    ...
  }
}
```

### Configuration Details

#### Snowflake Section
- **account**: Found in Snowflake URL (e.g., `https://xy12345.snowflakecomputing.com`)
- **user**: Your Snowflake username
- **password**: Your password
- **warehouse**: Name of compute warehouse (create if doesn't exist)
- **database**: Will be created if doesn't exist
- **schema**: Will be created if doesn't exist

#### Deployment Section
- **phases**: List of phases to deploy (1-5). Start with all: `[1, 2, 3, 4, 5]`
- **dry_run**: Set to `true` first to test without making changes
- **backup_before_deploy**: Creates backup before deployment (safe!)
- **skip_validation**: Set to `false` to run validation checks

#### Integration Section (Optional)
Only fill in if you have these services:
- Slack bot token (for notifications)
- ServiceNow instance URL
- DataDog API keys
- Splunk HEC token
- PagerDuty API key

---

## Step 2: Validate Pre-Deployment

Run validation to ensure everything is ready:

```bash
python validate_deployment.py deployment_config.json
```

**This checks:**
✅ Configuration file is valid  
✅ All required Python files exist  
✅ All dependencies installed  
✅ Snowflake connectivity works  

**Output:**
```
✅ CONFIG: PASS
✅ FILES: PASS
✅ DEPENDENCIES: PASS
✅ SNOWFLAKE: PASS

✅ Overall: READY
```

**If any check fails:**
1. Read the error message
2. Fix the issue
3. Run validation again

---

## Step 3: Deploy (Dry Run First)

### Option A: Dry Run (Recommended First)

Set `"dry_run": true` in config, then:

```bash
python deploy.py deployment_config.json
```

**Output:**
```
╔════════════════════════════════════════════════════════╗
║  SNOWFLAKE GOVERNANCE DEPLOYMENT - DRY RUN            ║
╚════════════════════════════════════════════════════════╝

✅ Connected to Snowflake
💾 Creating backup...
✅ Backup created: GOVERNANCE_backup_20261108_143022
📋 Deploying schema...
✅ Schema deployed
🤖 Deploying agents...
  ✓ Phase 1 agents (5/5)
  ✓ Phase 2 agents (6/6)
  ✓ Phase 3 agents (2/2)
  ✓ Phase 4 agents (2/2)
  ✓ Phase 5 agents (6/6)
🔍 Validating deployment...
✅ Schema exists
✅ 25+ tables created
✅ Agents deployed
✅ Deployment completed successfully!

Duration: 45.2 seconds
```

**Dry run result:**
- ✅ All steps validated
- ✅ No changes made to Snowflake
- ✅ Ready for real deployment

### Option B: Production Deployment

Update config:
```json
{
  "deployment": {
    "dry_run": false,          ← Changed to false
    "backup_before_deploy": true
  }
}
```

Then run:
```bash
python deploy.py deployment_config.json
```

**What happens:**
1. **Backup** - Creates backup schema before changes
2. **Schema** - Creates tables for governance
3. **Agents** - Deploys 13 agents across 5 phases
4. **Validation** - Verifies everything created correctly
5. **Report** - Generates deployment report

**Timeline:**
- Small deployment (dry run): ~30 seconds
- Full deployment: ~2-5 minutes

---

## Step 4: Post-Deployment Validation

After deployment, run post-deployment checks:

```bash
python validate_deployment.py --post deployment_config.json
```

**Checks:**
✅ Schema created  
✅ 25+ tables exist  
✅ Agents deployed  
✅ API health  
✅ Policies loaded  

---

## Deployment Reports

### During Deployment
Console output shows real-time progress:
```
✅ Connected to Snowflake
💾 Creating backup: GOVERNANCE_backup_20261108_143022
📋 Deploying schema...
  ✓ Loaded schema.sql
  ✓ Created 20+ tables
  ✓ Created indexes
🤖 Deploying agents...
  ✓ Phase 1: 5/5 agents
  ✓ Phase 2: 6/6 agents
  ✓ Phase 3: 2/2 agents
  ✓ Phase 4: 2/2 agents
  ✓ Phase 5: 6/6 agents
🔍 Validating...
  ✓ Schema exists
  ✓ Tables: 25+
  ✓ Agents: 13
```

### Saved Report
After deployment, file `deployment_report.txt` is created:

```
═══════════════════════════════════════════════════════
SNOWFLAKE GOVERNANCE DEPLOYMENT REPORT
═══════════════════════════════════════════════════════

Deployment Time: 2026-11-08T14:30:22.123456
Account: xy12345
Database: GOVERNANCE
Schema: PUBLIC

DEPLOYMENT LOG
═══════════════════════════════════════════════════════

✅ OK | 2026-11-08T14:30:22 | Connected to Snowflake
✅ OK | 2026-11-08T14:30:23 | Backup created
✅ OK | 2026-11-08T14:30:45 | Schema deployed
✅ OK | 2026-11-08T14:31:12 | Agents deployed
✅ OK | 2026-11-08T14:31:25 | Validation passed

Total Events: 5
Errors: 0
Status: ✅ SUCCESS
```

---

## Rollback (If Needed)

If deployment fails or you need to rollback:

### Option 1: Automatic Backup Restore

If `backup_before_deploy: true` was set:

```bash
# Snowflake console
ALTER SCHEMA GOVERNANCE RENAME TO GOVERNANCE_failed;
ALTER SCHEMA GOVERNANCE_backup_20261108_143022 RENAME TO GOVERNANCE;
```

### Option 2: Manual Rollback

```sql
-- In Snowflake
-- Drop failed schema
DROP SCHEMA GOVERNANCE;

-- Restore from backup
CREATE SCHEMA GOVERNANCE CLONE GOVERNANCE_backup_20261108_143022;
```

### Option 3: Fresh Start

```sql
-- Drop everything
DROP DATABASE GOVERNANCE;

-- Rerun deployment
```

---

## Troubleshooting

### Error: "Connection failed"
**Problem**: Can't connect to Snowflake

**Solution:**
1. Check account ID format: `xy12345.us-west-2` (not full URL)
2. Verify username and password
3. Ensure warehouse exists and is active
4. Check firewall/VPN access to Snowflake

```bash
# Test connection
python -c "import snowflake.connector; print('OK')"
```

### Error: "Permission denied"
**Problem**: User lacks required permissions

**Solution:**
1. Use SYSADMIN role (or higher)
2. Or grant explicit permissions:
```sql
GRANT CREATE DATABASE ON ACCOUNT TO ROLE YOUR_ROLE;
GRANT CREATE SCHEMA ON DATABASE GOVERNANCE TO ROLE YOUR_ROLE;
```

### Error: "File not found"
**Problem**: Source files missing

**Solution:**
1. Ensure you're in the `Snowflake-AI-Toolkit` directory
2. Check all Python files exist in `src/` directories
3. Run from project root:
```bash
cd /c/LabFiles/Snowflake-AI-Toolkit
python deploy.py
```

### Slow Deployment
**Problem**: Deployment taking too long

**Solution:**
1. Check Snowflake warehouse size (should be MEDIUM or larger)
2. Check network connectivity
3. Look at deployment logs for slow stages
4. Can run phases sequentially or in parallel (config option)

---

## Monitoring Deployment Progress

### Real-time Monitoring

```bash
# In separate terminal, watch deployment logs
tail -f deployment_report.txt

# Or watch Snowflake:
SELECT * FROM GOVERNANCE.GOVERNANCE.audit_logs 
ORDER BY created_at DESC LIMIT 100;
```

### Completion Signs

✅ All phases show "deployed"  
✅ No errors in deployment report  
✅ Post-deployment validation passes  
✅ Can query governance tables  

```sql
-- Verify deployment
SELECT * FROM GOVERNANCE.GOVERNANCE.agent_state;  -- Should have 13 agents
SELECT COUNT(*) FROM GOVERNANCE.GOVERNANCE.audit_logs;  -- Should have entries
```

---

## Next Steps After Deployment

### 1. Initial Configuration (30 min)
- [ ] Load policy templates
- [ ] Configure Slack bot (optional)
- [ ] Configure approval SLAs
- [ ] Enable autonomous execution (or start approval-only)

### 2. Testing (1 hour)
- [ ] Run agents manually
- [ ] Generate sample findings
- [ ] Test approval workflow
- [ ] Test Slack notifications

### 3. Training (1 day)
- [ ] Train team on dashboards
- [ ] Show policy as code
- [ ] Demo natural language queries
- [ ] Explain autonomous execution

### 4. Production Use (ongoing)
- [ ] Monitor metrics
- [ ] Tune thresholds
- [ ] Handle escalations
- [ ] Continuous improvement

---

## Configuration Examples

### Example 1: Minimal Deployment (Phase 1 Only)
```json
{
  "deployment": {
    "phases": [1],
    "backup_before_deploy": true,
    "skip_schema_creation": false
  }
}
```

### Example 2: Gradual Rollout (Phases 1-3, No Integrations)
```json
{
  "deployment": {
    "phases": [1, 2, 3]
  },
  "integrations": {
    "slack": {"enabled": false},
    "servicenow": {"enabled": false}
  }
}
```

### Example 3: Full Production (All 5 Phases + Integrations)
```json
{
  "deployment": {
    "phases": [1, 2, 3, 4, 5],
    "autonomous_execution": {
      "safe_actions_enabled": true,
      "moderate_actions_enabled": false
    }
  },
  "integrations": {
    "slack": {
      "enabled": true,
      "bot_token": "xoxb-YOUR-REAL-TOKEN",
      "channels": {
        "alerts": "#governance-alerts"
      }
    }
  }
}
```

---

## Support & Help

### Check Deployment Status

```bash
# View deployment report
cat deployment_report.txt

# Check log file
tail -100 deployment.log

# Query Snowflake
SELECT agent_name, status FROM GOVERNANCE.GOVERNANCE.agent_state;
```

### Common Commands

```bash
# Pre-deployment check
python validate_deployment.py deployment_config.json

# Dry run
python deploy.py deployment_config.json

# Production deployment
python deploy.py deployment_config.json

# Check phase 5 specifically
grep "Phase 5" deployment_report.txt

# Verify all tables
SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'GOVERNANCE';
```

---

## Deployment Checklist

```
PRE-DEPLOYMENT
[ ] Edit deployment_config.json with your Snowflake credentials
[ ] Run pre-deployment validation
[ ] All checks passing
[ ] Dry run completed successfully
[ ] Team informed of deployment

DEPLOYMENT
[ ] Backup created
[ ] Schema deployed
[ ] Agents deployed (13 total)
[ ] Validation passed
[ ] Report generated

POST-DEPLOYMENT
[ ] All tables created (25+)
[ ] All agents deployed (13)
[ ] Can query governance schema
[ ] No errors in log
[ ] Dashboards accessible

CONFIGURATION
[ ] Load policy templates
[ ] Configure integrations (optional)
[ ] Set approval SLAs
[ ] Configure thresholds

VALIDATION
[ ] Run post-deployment checks
[ ] All checks passing
[ ] System healthy
[ ] Ready for production
```

---

## Timeline

| Step | Time | Notes |
|------|------|-------|
| Pre-deployment validation | 2 min | Quick connectivity check |
| Dry run | 1-2 min | Test without changes |
| Backup creation | 1-2 min | Safety measure |
| Schema deployment | 2-3 min | Create tables/indexes |
| Agent deployment | 2-3 min | Copy agent files |
| Validation | 1-2 min | Verify everything |
| **Total** | **~10 min** | Fast & automated |

---

**Your automated deployment system is ready!** 🚀

Run: `python validate_deployment.py` → `python deploy.py`

Questions? Check the docs or deployment logs! 📖

