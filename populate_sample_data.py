#!/usr/bin/env python3
"""
Populate Snowflake Governance Tables with Sample Data
Run this to load demo data into the governance system
"""

from snowflake.snowpark.session import Session
import json

print("Loading configuration...")
with open('deployment_config.json', 'r') as f:
    config = json.load(f)

sf_config = config['snowflake']
print(f"Connecting to {sf_config['account']}...")

session = Session.builder.configs({
    "account": sf_config['account'],
    "user": sf_config['user'],
    "password": sf_config['password'],
    "warehouse": sf_config['warehouse'],
    "database": "GOVERNANCE"
}).create()

session.sql("USE DATABASE GOVERNANCE").collect()
session.sql("USE SCHEMA GOVERNANCE").collect()

print("✅ Connected!\n")
print("🔄 Populating governance tables with sample data...\n")

# 1. Insert Policies
print("📋 Adding policies...")
session.sql("""
INSERT INTO GOVERNANCE.GOVERNANCE.POLICIES VALUES
('POL001', 'Security Policy', 'security', 'Enterprise security standards', NULL, TRUE, 'admin@company.com', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), NULL),
('POL002', 'Performance Policy', 'performance', 'Query optimization standards', NULL, TRUE, 'admin@company.com', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), NULL),
('POL003', 'Cost Policy', 'cost', 'Cost control guidelines', NULL, TRUE, 'admin@company.com', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), NULL)
""").collect()

# 2. Insert Security Rules
print("🔒 Adding security rules...")
session.sql("""
INSERT INTO GOVERNANCE.GOVERNANCE.SECURITY_RULES VALUES
('RULE001', 'MFA Enforcement', 'access_control', 'Require MFA for all users', NULL, 'critical', TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('RULE002', 'Data Classification', 'data_classification', 'PII must be tagged', NULL, 'high', TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('RULE003', 'RBAC Enforcement', 'rbac', 'Least privilege access model', NULL, 'high', TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
""").collect()

# 3. Insert Warehouse Health
print("❤️ Adding warehouse health data...")
session.sql("""
INSERT INTO GOVERNANCE.GOVERNANCE.WAREHOUSE_HEALTH VALUES
('HEALTH001', 'COMPUTE_WH', CURRENT_TIMESTAMP(), 45.5, 62.3, 256, 5, 2.5, 8, 0, 3, 'healthy', 'Optimal performance'),
('HEALTH002', 'ANALYTICS_WH', CURRENT_TIMESTAMP(), 78.2, 85.1, 512, 12, 5.8, 15, 2, 8, 'warning', 'High resource utilization'),
('HEALTH003', 'REPORTING_WH', CURRENT_TIMESTAMP(), 32.1, 48.0, 128, 2, 1.2, 3, 0, 1, 'healthy', 'Normal operation')
""").collect()

# 4. Insert Agent State
print("🤖 Adding agent states...")
session.sql("""
INSERT INTO GOVERNANCE.GOVERNANCE.AGENT_STATE VALUES
('AG001', 'Security Agent', 'security', CURRENT_TIMESTAMP() - INTERVAL '10 minutes', CURRENT_TIMESTAMP() - INTERVAL '10 minutes', 'idle', 25, 24, 0, NULL, CURRENT_TIMESTAMP() + INTERVAL '5 minutes', TRUE, CURRENT_TIMESTAMP()),
('AG002', 'Performance Agent', 'performance', CURRENT_TIMESTAMP() - INTERVAL '5 minutes', CURRENT_TIMESTAMP() - INTERVAL '5 minutes', 'idle', 18, 17, 0, NULL, CURRENT_TIMESTAMP() + INTERVAL '5 minutes', TRUE, CURRENT_TIMESTAMP()),
('AG003', 'Cost Agent', 'cost', CURRENT_TIMESTAMP() - INTERVAL '15 minutes', CURRENT_TIMESTAMP() - INTERVAL '15 minutes', 'idle', 42, 40, 1, 'Timeout on query', CURRENT_TIMESTAMP() + INTERVAL '10 minutes', TRUE, CURRENT_TIMESTAMP()),
('AG004', 'Health Agent', 'health', CURRENT_TIMESTAMP() - INTERVAL '3 minutes', CURRENT_TIMESTAMP() - INTERVAL '3 minutes', 'idle', 15, 15, 0, NULL, CURRENT_TIMESTAMP() + INTERVAL '5 minutes', TRUE, CURRENT_TIMESTAMP()),
('AG005', 'Spillage Prevention', 'spillage', CURRENT_TIMESTAMP() - INTERVAL '8 minutes', CURRENT_TIMESTAMP() - INTERVAL '8 minutes', 'idle', 5, 4, 0, NULL, CURRENT_TIMESTAMP() + INTERVAL '5 minutes', TRUE, CURRENT_TIMESTAMP())
""").collect()

# 5. Insert Cost Tracking
print("💰 Adding cost tracking data...")
session.sql("""
INSERT INTO GOVERNANCE.GOVERNANCE.COST_TRACKING VALUES
('COST001', 'COMPUTE_WH', 'QRY001', 'analyst@company.com', CURRENT_TIMESTAMP() - INTERVAL '1 day', CURRENT_TIMESTAMP() - INTERVAL '1 day' + INTERVAL '5 minutes', 2.5, 45, 1250, 300, FALSE, 'compute', CURRENT_TIMESTAMP()),
('COST002', 'ANALYTICS_WH', 'QRY002', 'scientist@company.com', CURRENT_TIMESTAMP() - INTERVAL '2 days', CURRENT_TIMESTAMP() - INTERVAL '2 days' + INTERVAL '45 minutes', 8.3, 250, 45000, 2700, FALSE, 'compute', CURRENT_TIMESTAMP()),
('COST003', 'COMPUTE_WH', 'QRY003', 'analyst@company.com', CURRENT_TIMESTAMP() - INTERVAL '3 days', CURRENT_TIMESTAMP() - INTERVAL '3 days' + INTERVAL '12 minutes', 1.8, 30, 850, 720, TRUE, 'compute', CURRENT_TIMESTAMP())
""").collect()

# 6. Insert Incidents
print("🚨 Adding incidents...")
session.sql("""
INSERT INTO GOVERNANCE.GOVERNANCE.INCIDENTS VALUES
('INC001', 'high', 'performance', 'Query running >5 min on ANALYTICS_WH', CURRENT_TIMESTAMP() - INTERVAL '2 hours', NULL, 'dba@company.com', 'in_progress', NULL, NULL, 1, NULL, 'Investigating slow query'),
('INC002', 'medium', 'cost', 'Unusually high credits usage in REPORTING_WH', CURRENT_TIMESTAMP() - INTERVAL '4 hours', CURRENT_TIMESTAMP() - INTERVAL '1 hour', 'analyst@company.com', 'resolved', NULL, NULL, 0, NULL, 'Fixed inefficient joins')
""").collect()

# 7. Insert Approval Requests
print("✅ Adding approval requests...")
session.sql("""
INSERT INTO GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS VALUES
('APP001', 'permission_grant', 'Security Agent', 'user@company.com', 'manager@company.com', '{}', 'Grant access to customer_data', 'User needs access for analysis', 'pending', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP() + INTERVAL '24 hours', NULL, NULL, NULL, NULL, 24, 'high'),
('APP002', 'config_change', 'Performance Agent', 'dba@company.com', 'admin@company.com', '{}', 'Increase COMPUTE_WH size', 'Performance improvement needed', 'approved', CURRENT_TIMESTAMP() - INTERVAL '1 day', CURRENT_TIMESTAMP() - INTERVAL '1 day' + INTERVAL '2 hours', CURRENT_TIMESTAMP() - INTERVAL '1 day' + INTERVAL '30 minutes', 'admin@company.com', NULL, 'Approved - scaling up', 24, 'medium')
""").collect()

print("\n✅ Sample data loaded successfully!")
print("\n📊 Dashboard is now ready with demo data!")
print("   ✓ 5 Governance Agents")
print("   ✓ 3 Warehouses with health data")
print("   ✓ Sample incidents, costs, and policies")
print("   ✓ Approval requests")
print("\n🔄 Refresh your Snowsight dashboard to see the data!\n")

session.close()
