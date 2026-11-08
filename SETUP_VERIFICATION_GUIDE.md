# ✅ SETUP VERIFICATION GUIDE
## Pre-Deployment Setup Check

This guide will verify your system is ready for deployment.

---

## 🚀 RUN VERIFICATION

**Step 1: Open Terminal**
```bash
cd /c/LabFiles/Snowflake-AI-Toolkit
```

**Step 2: Run Verification Script**
```bash
python verify_setup.py
```

**This checks:**
- ✅ Python version (3.8+)
- ✅ Project files exist
- ✅ Dependencies installed
- ✅ Configuration file present
- ✅ Snowflake credentials configured
- ✅ Snowflake connectivity works

---

## 📋 EXPECTED RESULTS

### ✅ Perfect Setup (All Green)

```
✅ PASS  OS
✅ PASS  Python
✅ PASS  Project Dir
✅ PASS  Files
✅ PASS  Dependencies
✅ PASS  Config
✅ PASS  Connectivity

✅ SETUP VERIFICATION PASSED!

You're ready to deploy. Run:
   python validate_deployment.py deployment_config.json
   python deploy.py deployment_config.json
```

**What this means:** Everything is ready! You can deploy immediately.

---

### ⚠️ Partial Setup (Some Fixes Needed)

If verification shows issues, you'll see:

```
✅ PASS  OS
✅ PASS  Python
❌ FAIL  Dependencies

🔴 ISSUES TO FIX:
   1. Missing dependency: snowflake-connector-python
   2. Missing dependency: numpy

❌ SETUP VERIFICATION FAILED!

Fix the issues above before deploying.
```

---

## 🔧 FIXING ISSUES

### Issue 1: Python Version

**Problem:**
```
❌ FAIL  Python (need 3.8+)
```

**Fix:**
1. Download Python 3.8+ from https://www.python.org/
2. Install with default options
3. Restart terminal
4. Run: `python --version` to verify

---

### Issue 2: Project Directory Not Found

**Problem:**
```
❌ FAIL  Project Dir
   Not found: /c/LabFiles/Snowflake-AI-Toolkit
```

**Fix:**
1. Navigate to correct directory:
```bash
cd /c/LabFiles/Snowflake-AI-Toolkit
```

2. Verify files exist:
```bash
ls -la deploy.py validate_deployment.py
```

---

### Issue 3: Missing Dependencies

**Problem:**
```
❌ FAIL  Dependencies
   Missing dependency: snowflake-connector-python
   Missing dependency: numpy
```

**Fix:**
```bash
# Install all dependencies at once
pip install snowflake-connector-python numpy pyyaml requests

# Verify installation
python -c "import snowflake.connector; print('OK')"
```

---

### Issue 4: Configuration Not Set

**Problem:**
```
⚠️  SKIP  Config
   Credentials need to be configured: account, user, password
```

**Fix:**

1. Open `deployment_config.json`:
```bash
# Windows
notepad deployment_config.json

# Mac
open -a TextEdit deployment_config.json

# Linux
nano deployment_config.json
```

2. Find this section:
```json
"snowflake": {
  "account": "YOUR_ACCOUNT_ID",
  "user": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD",
  "warehouse": "GOVERNANCE_WH",
  "database": "GOVERNANCE",
  "schema": "PUBLIC",
  "role": "SYSADMIN"
}
```

3. Replace with YOUR values:

**Get Account ID:**
- Log in to Snowflake: https://www.snowflake.com/
- Look at URL: `https://xy12345.us-west-2.snowflakecomputing.com`
- Account ID: `xy12345.us-west-2`

**Get Username:**
- Your Snowflake login username

**Get Password:**
- Your Snowflake login password

**Get Warehouse:**
- Use existing or create in Snowflake:
```sql
CREATE WAREHOUSE GOVERNANCE_WH WAREHOUSE_SIZE = 'MEDIUM';
```

**Get Database:**
- Use existing or create:
```sql
CREATE DATABASE GOVERNANCE;
```

**Get Role:**
- Usually `SYSADMIN`

4. Save the file (Ctrl+S or Cmd+S)

5. Run verification again:
```bash
python verify_setup.py
```

---

### Issue 5: Snowflake Connection Failed

**Problem:**
```
❌ FAIL  Connectivity
   Connection failed: 250001: Incorrect username or password
```

**Fix:**

**Check 1: Credentials**
- Double-check username and password
- Make sure no extra spaces
- Case-sensitive on password

**Check 2: Account ID**
- Should be: `xy12345.us-west-2` (with region)
- NOT: `xy12345` (without region)
- NOT: Full URL

**Check 3: Account Exists**
- Log in to Snowflake web UI
- If you can't log in, credentials are wrong

**Check 4: Warehouse**
- Make sure warehouse name is correct
- Make sure warehouse exists
- Create if needed:
```sql
CREATE WAREHOUSE GOVERNANCE_WH WAREHOUSE_SIZE = 'MEDIUM';
```

**Check 5: Database**
- Make sure database exists
- Create if needed:
```sql
CREATE DATABASE GOVERNANCE;
```

---

## ✅ STEP-BY-STEP VERIFICATION

### **Manual Setup Check** (if you prefer)

**1. Check Python**
```bash
python --version
# Should show: Python 3.8.0 or higher
```

**2. Check Project**
```bash
cd /c/LabFiles/Snowflake-AI-Toolkit
ls -la deploy.py validate_deployment.py
# Both files should exist
```

**3. Check Dependencies**
```bash
python -c "import snowflake.connector; print('✅ Snowflake')"
python -c "import numpy; print('✅ NumPy')"
python -c "import yaml; print('✅ PyYAML')"
python -c "import requests; print('✅ Requests')"
# All should print ✅
```

**4. Check Configuration**
```bash
cat deployment_config.json | grep account
# Should show your account ID (not "YOUR_ACCOUNT_ID")
```

**5. Check Snowflake Connection**
```bash
python -c "
import snowflake.connector
import json
with open('deployment_config.json') as f:
    config = json.load(f)
conn = snowflake.connector.connect(**config['snowflake'])
cursor = conn.cursor()
cursor.execute('SELECT CURRENT_USER()')
print('✅ Connected as:', cursor.fetchone()[0])
"
# Should print: ✅ Connected as: your_username
```

---

## 📊 VERIFICATION CHECKLIST

**Before running verification script:**

- [ ] Python 3.8+ installed
- [ ] In project directory: `/c/LabFiles/Snowflake-AI-Toolkit/`
- [ ] `deploy.py` file exists
- [ ] `validate_deployment.py` file exists
- [ ] `deployment_config.json` file exists

**Snowflake prerequisites:**

- [ ] Snowflake account (free trial OK)
- [ ] Account ID (e.g., `xy12345.us-west-2`)
- [ ] Username
- [ ] Password
- [ ] Warehouse exists (or name chosen for creation)
- [ ] Database name decided

**Dependencies:**

- [ ] `snowflake-connector-python` installed
- [ ] `numpy` installed
- [ ] `pyyaml` installed
- [ ] `requests` installed

---

## 🚀 READY?

**Run verification:**
```bash
python verify_setup.py
```

**If all ✅:**
```bash
# Next step
python validate_deployment.py deployment_config.json
```

**If issues ❌:**
- Follow fix instructions above
- Run verification again
- Repeat until all ✅

---

## 💡 COMMON ISSUES & QUICK FIXES

| Issue | Quick Fix |
|-------|-----------|
| Python not found | Install Python 3.8+ |
| Files not found | Run from `/c/LabFiles/Snowflake-AI-Toolkit/` |
| Dependencies missing | Run: `pip install snowflake-connector-python numpy pyyaml requests` |
| Config not found | Create with: `python deploy.py` (will create default) |
| Credentials wrong | Edit `deployment_config.json` with correct values |
| Can't connect to Snowflake | Check username/password, try Snowflake web UI |
| Warehouse doesn't exist | Create: `CREATE WAREHOUSE GOVERNANCE_WH` in Snowflake |

---

## ✨ NEXT STEPS

### **If verification ✅ passes:**
```bash
python validate_deployment.py deployment_config.json
```

### **If verification ❌ fails:**
1. Read the error message
2. Find the issue above
3. Follow the fix
4. Run verification again
5. Repeat until ✅

### **Questions?**
- Ask me for help
- I can guide you through any fix
- Ready to help troubleshoot

---

## 🎯 DEPLOYMENT FLOW

```
verify_setup.py ← YOU ARE HERE
        ↓
Verify all prerequisites
        ↓ (if all ✅)
validate_deployment.py
        ↓
Pre-deployment checks
        ↓ (if all ✅)
deploy.py
        ↓
System deployed to Snowflake ✅
```

---

**Ready? Run:**
```bash
python verify_setup.py
```

**Tell me the results and I'll help if anything needs fixing!** 🚀
