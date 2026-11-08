#!/bin/bash

# Snowflake Governance System - Deployment Execution Script
# This script guides you through deploying to your Snowflake account

set -e  # Exit on error

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
}

print_step() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

pause_for_user() {
    echo ""
    read -p "Press ENTER to continue..."
    echo ""
}

# Start
clear
print_header "SNOWFLAKE GOVERNANCE SYSTEM - DEPLOYMENT EXECUTION"

echo "This script will guide you through deploying to your Snowflake account."
echo ""
echo "Prerequisites:"
echo "  • Python 3.8+"
echo "  • snowflake-connector-python installed"
echo "  • Snowflake account credentials"
echo "  • SYSADMIN role or equivalent permissions"
echo ""

pause_for_user

# Step 1: Validate Python environment
print_header "STEP 1: Validate Python Environment"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_step "Python found: $PYTHON_VERSION"
else
    print_error "Python3 not found"
    echo "Install Python 3.8+ from https://www.python.org/"
    exit 1
fi

# Check dependencies
echo "Checking dependencies..."

REQUIRED_PACKAGES=("snowflake-connector-python" "numpy" "pyyaml")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package//-/_}" 2>/dev/null; then
        print_step "$package installed"
    else
        print_warning "$package NOT installed"
        echo "Install with: pip install $package"
        exit 1
    fi
done

pause_for_user

# Step 2: Prepare Snowflake environment
print_header "STEP 2: Prepare Snowflake Environment"

echo "Before deployment, you need to:"
echo ""
echo "1. Create a compute warehouse (or use existing):"
echo "   CREATE WAREHOUSE GOVERNANCE_WH WAREHOUSE_SIZE = 'MEDIUM';"
echo ""
echo "2. Create a database for governance:"
echo "   CREATE DATABASE GOVERNANCE;"
echo ""
echo "3. Ensure your user has SYSADMIN role"
echo ""
echo "Actions to take in Snowflake:"
echo "  → Log in to Snowflake web UI"
echo "  → Go to Worksheets"
echo "  → Run the SQL above"
echo "  → Verify they complete successfully"
echo ""

pause_for_user

# Step 3: Configuration
print_header "STEP 3: Configure Deployment"

echo "You need to customize deployment_config.json"
echo ""
echo "Required fields to update:"
echo "  • account: Your account ID (from Snowflake URL)"
echo "  • user: Your Snowflake username"
echo "  • password: Your Snowflake password"
echo "  • warehouse: Name of warehouse you created (GOVERNANCE_WH)"
echo "  • database: GOVERNANCE (or custom name)"
echo ""
echo "Example account ID: xy12345.us-west-2"
echo "(Find yours in Snowflake URL: https://xy12345.us-west-2.snowflakecomputing.com)"
echo ""

if [ -f "deployment_config.json" ]; then
    print_step "deployment_config.json found"
    echo ""
    echo "Edit now? (y/n)"
    read -r response

    if [ "$response" = "y" ]; then
        if command -v nano &> /dev/null; then
            nano deployment_config.json
        elif command -v vi &> /dev/null; then
            vi deployment_config.json
        else
            print_warning "Please edit deployment_config.json manually"
        fi
    fi
else
    print_error "deployment_config.json not found"
    echo "Creating default config..."
    cat > deployment_config.json << 'EOF'
{
  "snowflake": {
    "account": "YOUR_ACCOUNT_ID",
    "user": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD",
    "warehouse": "GOVERNANCE_WH",
    "database": "GOVERNANCE",
    "schema": "PUBLIC",
    "role": "SYSADMIN"
  },
  "deployment": {
    "phases": [1, 2, 3, 4, 5],
    "dry_run": true,
    "backup_before_deploy": true,
    "skip_validation": false
  }
}
EOF
    echo "Created deployment_config.json - please edit with your credentials"
    exit 1
fi

pause_for_user

# Step 4: Pre-deployment validation
print_header "STEP 4: Pre-Deployment Validation"

echo "Running validation checks..."
echo ""

if python3 validate_deployment.py deployment_config.json; then
    print_step "Pre-deployment validation PASSED"
else
    print_error "Pre-deployment validation FAILED"
    echo "Fix issues and run again"
    exit 1
fi

pause_for_user

# Step 5: Dry run
print_header "STEP 5: Dry Run (Test Mode)"

echo "About to run deployment in DRY RUN mode"
echo "This will NOT make changes to Snowflake"
echo "It will test and validate the deployment process"
echo ""

# Ensure dry_run is true
python3 << 'PYTHON_SCRIPT'
import json

with open('deployment_config.json', 'r') as f:
    config = json.load(f)

config['deployment']['dry_run'] = True

with open('deployment_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Dry run mode enabled")
PYTHON_SCRIPT

echo ""
echo "Starting dry run..."
echo ""

if python3 deploy.py deployment_config.json; then
    print_step "Dry run COMPLETED SUCCESSFULLY"
    echo ""
    echo "Review the output above. If everything looks good,"
    echo "we'll proceed to production deployment."
else
    print_error "Dry run FAILED"
    echo "Review errors and fix before proceeding"
    exit 1
fi

pause_for_user

# Step 6: Production deployment confirmation
print_header "STEP 6: Production Deployment"

echo "Ready for production deployment!"
echo ""
echo "This will:"
echo "  ✓ Create backup schema"
echo "  ✓ Deploy database schema (20+ tables)"
echo "  ✓ Deploy 13 agents across 5 phases"
echo "  ✓ Run validation checks"
echo "  ✓ Generate deployment report"
echo ""
echo "Timeline: ~5-10 minutes"
echo ""
echo "Continue with production deployment? (yes/no)"
read -r response

if [ "$response" != "yes" ]; then
    print_warning "Deployment cancelled"
    exit 0
fi

# Enable production mode
python3 << 'PYTHON_SCRIPT'
import json

with open('deployment_config.json', 'r') as f:
    config = json.load(f)

config['deployment']['dry_run'] = False

with open('deployment_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Production mode enabled")
PYTHON_SCRIPT

echo ""
print_header "STEP 7: Executing Production Deployment"

echo "Starting deployment..."
echo ""

if python3 deploy.py deployment_config.json; then
    print_step "DEPLOYMENT COMPLETED SUCCESSFULLY"
    echo ""
    echo "Your Snowflake Governance System is now deployed!"
else
    print_error "DEPLOYMENT FAILED"
    echo "Check deployment_report.txt for details"
    exit 1
fi

pause_for_user

# Step 8: Post-deployment validation
print_header "STEP 8: Post-Deployment Validation"

echo "Running post-deployment checks..."
echo ""

python3 validate_deployment.py deployment_config.json --post

pause_for_user

# Step 9: Verify in Snowflake
print_header "STEP 9: Verify in Snowflake"

echo "Verify deployment by running these queries in Snowflake:"
echo ""
echo "1. Check tables were created:"
echo "   SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES"
echo "   WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_DATABASE = 'GOVERNANCE';"
echo ""
echo "2. Check agents:"
echo "   SELECT agent_name, status FROM GOVERNANCE.PUBLIC.agent_state;"
echo ""
echo "3. Check audit logs:"
echo "   SELECT * FROM GOVERNANCE.PUBLIC.audit_logs LIMIT 10;"
echo ""

pause_for_user

# Step 10: Next steps
print_header "STEP 10: Next Steps"

echo "Deployment complete! Here's what to do next:"
echo ""
echo "1. CONFIGURE (30 minutes)"
echo "   • Load policy templates"
echo "   • Configure Slack bot (optional)"
echo "   • Set approval SLAs"
echo "   • Configure autonomous execution thresholds"
echo ""
echo "2. TEST (1 hour)"
echo "   • Run agents manually"
echo "   • Generate sample findings"
echo "   • Test approval workflow"
echo "   • Test notifications"
echo ""
echo "3. TRAIN (1 day)"
echo "   • Onboard your team"
echo "   • Show dashboards"
echo "   • Explain policy as code"
echo "   • Demo natural language queries"
echo ""
echo "4. MONITOR (ongoing)"
echo "   • Set up monitoring dashboards"
echo "   • Review daily reports"
echo "   • Tune thresholds based on results"
echo ""

echo "Documentation:"
echo "  • Phase 5 README: PHASE_5_README.md"
echo "  • Integration Guide: PHASE_5_INTEGRATION_GUIDE.md"
echo "  • Deployment Report: deployment_report.txt"
echo ""

echo "Files created:"
echo "  ✓ deployment_config.json (your configuration)"
echo "  ✓ deployment_report.txt (what was deployed)"
echo "  ✓ deployment.log (detailed log)"
echo ""

print_header "🎉 DEPLOYMENT COMPLETE!"

echo "Your Snowflake Governance System (Phases 1-5) is now live!"
echo ""
echo "Need help? Check the documentation or review the deployment report."
echo ""
