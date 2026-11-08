"""
Snowflake Governance Dashboard - Streamlit App
Runs natively in Snowsight with Inactive Users Management
"""

import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session

# Page config
st.set_page_config(
    page_title="Snowflake Governance Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# Header
st.title("🛡️ Snowflake Governance Dashboard")
st.markdown("**Real-time monitoring of governance, security, performance, and health**")

# Get session
try:
    session = get_active_session()
    session.sql("USE DATABASE GOVERNANCE").collect()
    session.sql("USE SCHEMA GOVERNANCE").collect()
    st.success("✅ Connected to GOVERNANCE.GOVERNANCE")
except Exception as e:
    st.error(f"Connection error: {str(e)}")
    st.stop()

# Sidebar navigation - Using selectbox for better visibility
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Select Page",
    ["Overview", "Security", "Performance", "Cost", "Health", "Incidents", "Agents", "Inactive Users"]
)

# ============================================================================
# OVERVIEW PAGE
# ============================================================================
if page == "Overview":
    st.header("System Overview")
    col1, col2, col3, col4 = st.columns(4)

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.POLICIES").collect()
        col1.metric("Active Policies", result[0]['COUNT'])
    except:
        col1.metric("Active Policies", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.SECURITY_RULES").collect()
        col2.metric("Security Rules", result[0]['COUNT'])
    except:
        col2.metric("Security Rules", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE STATUS IN ('open', 'in_progress')").collect()
        col3.metric("Open Incidents", result[0]['COUNT'])
    except:
        col3.metric("Open Incidents", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS WHERE STATUS = 'pending'").collect()
        col4.metric("Pending Approvals", result[0]['COUNT'])
    except:
        col4.metric("Pending Approvals", "—")

    st.divider()
    st.subheader("Recent Audit Logs")
    try:
        df = session.sql("""
            SELECT EVENT_TYPE, EVENT_CATEGORY, RESOURCE_NAME, ACTOR_EMAIL, EVENT_TIMESTAMP, STATUS
            FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
            ORDER BY EVENT_TIMESTAMP DESC LIMIT 10
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load audit logs")

# ============================================================================
# SECURITY PAGE
# ============================================================================
elif page == "Security":
    st.header("🔒 Security & Compliance")
    col1, col2, col3 = st.columns(3)

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.SECURITY_RULES WHERE ENABLED = TRUE").collect()
        col1.metric("Enabled Rules", result[0]['COUNT'])
    except:
        col1.metric("Enabled Rules", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.PII_DETECTIONS WHERE STATUS = 'detected'").collect()
        col2.metric("PII Detections", result[0]['COUNT'])
    except:
        col2.metric("PII Detections", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS WHERE EVENT_CATEGORY = 'security'").collect()
        col3.metric("Security Events", result[0]['COUNT'])
    except:
        col3.metric("Security Events", "—")

    st.divider()
    st.subheader("PII Detection Records")
    try:
        df = session.sql("""
            SELECT DATABASE_NAME, SCHEMA_NAME, TABLE_NAME, COLUMN_NAME, PII_TYPE, STATUS
            FROM GOVERNANCE.GOVERNANCE.PII_DETECTIONS
            ORDER BY DETECTED_AT DESC LIMIT 20
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load PII detections")

# ============================================================================
# PERFORMANCE PAGE
# ============================================================================
elif page == "Performance":
    st.header("⚡ Performance Optimization")
    col1, col2, col3 = st.columns(3)

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.QUERY_ANALYSIS WHERE IS_OPTIMIZABLE = TRUE").collect()
        col1.metric("Optimizable Queries", result[0]['COUNT'])
    except:
        col1.metric("Optimizable Queries", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.PERFORMANCE_THRESHOLDS WHERE ENABLED = TRUE").collect()
        col2.metric("Active Thresholds", result[0]['COUNT'])
    except:
        col2.metric("Active Thresholds", "—")

    try:
        result = session.sql("SELECT AVG(EXECUTION_TIME_SECONDS) as avg_time FROM GOVERNANCE.GOVERNANCE.QUERY_ANALYSIS").collect()
        avg_time = result[0]['AVG_TIME']
        col3.metric("Avg Query Time", f"{avg_time:.2f}s" if avg_time else "—")
    except:
        col3.metric("Avg Query Time", "—")

    st.divider()
    st.subheader("Query Performance Analysis")
    try:
        df = session.sql("""
            SELECT QUERY_ID, WAREHOUSE_NAME, USER_EMAIL, EXECUTION_TIME_SECONDS, DATA_SCANNED_GB, IS_OPTIMIZABLE
            FROM GOVERNANCE.GOVERNANCE.QUERY_ANALYSIS
            ORDER BY ANALYSIS_TIMESTAMP DESC LIMIT 20
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load query analysis")

# ============================================================================
# COST PAGE
# ============================================================================
elif page == "Cost":
    st.header("💰 Cost Tracking & Optimization")
    col1, col2, col3 = st.columns(3)

    try:
        result = session.sql("SELECT SUM(CREDITS_USED) as total FROM GOVERNANCE.GOVERNANCE.COST_TRACKING WHERE RECORDED_AT >= CURRENT_TIMESTAMP() - INTERVAL '7 days'").collect()
        total = result[0]['TOTAL']
        col1.metric("Credits (7 days)", f"{total:.2f}" if total else "—")
    except:
        col1.metric("Credits (7 days)", "—")

    try:
        result = session.sql("SELECT COUNT(DISTINCT WAREHOUSE_NAME) as count FROM GOVERNANCE.GOVERNANCE.COST_TRACKING").collect()
        col2.metric("Active Warehouses", result[0]['COUNT'])
    except:
        col2.metric("Active Warehouses", "—")

    try:
        result = session.sql("SELECT COUNT(DISTINCT USER_EMAIL) as count FROM GOVERNANCE.GOVERNANCE.COST_TRACKING").collect()
        col3.metric("Active Users", result[0]['COUNT'])
    except:
        col3.metric("Active Users", "—")

    st.divider()
    st.subheader("Cost Summary by Warehouse")
    try:
        df = session.sql("""
            SELECT WAREHOUSE_NAME, COUNT(*) as query_count, SUM(CREDITS_USED) as total_credits, AVG(EXECUTION_TIME_SECONDS) as avg_time
            FROM GOVERNANCE.GOVERNANCE.COST_TRACKING
            WHERE RECORDED_AT >= CURRENT_TIMESTAMP() - INTERVAL '30 days'
            GROUP BY WAREHOUSE_NAME
            ORDER BY TOTAL_CREDITS DESC
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load cost summary")

# ============================================================================
# HEALTH PAGE
# ============================================================================
elif page == "Health":
    st.header("❤️ Warehouse Health")
    try:
        df = session.sql("""
            SELECT WAREHOUSE_NAME, METRIC_TIMESTAMP, CPU_PERCENT, MEMORY_PERCENT, HEALTH_STATUS
            FROM GOVERNANCE.GOVERNANCE.WAREHOUSE_HEALTH
            ORDER BY METRIC_TIMESTAMP DESC LIMIT 20
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load warehouse health")

# ============================================================================
# INCIDENTS PAGE
# ============================================================================
elif page == "Incidents":
    st.header("🚨 Incidents & Issues")
    col1, col2, col3 = st.columns(3)

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE STATUS IN ('open', 'in_progress')").collect()
        col1.metric("Active Incidents", result[0]['COUNT'])
    except:
        col1.metric("Active Incidents", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE SEVERITY = 'critical'").collect()
        col2.metric("Critical", result[0]['COUNT'])
    except:
        col2.metric("Critical", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE STATUS = 'resolved'").collect()
        col3.metric("Resolved", result[0]['COUNT'])
    except:
        col3.metric("Resolved", "—")

    st.divider()
    st.subheader("Open Incidents")
    try:
        df = session.sql("""
            SELECT INCIDENT_ID, SEVERITY, CATEGORY, DESCRIPTION, DETECTED_TIMESTAMP, STATUS
            FROM GOVERNANCE.GOVERNANCE.INCIDENTS
            WHERE STATUS IN ('open', 'in_progress')
            ORDER BY DETECTED_TIMESTAMP DESC
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load incidents")

# ============================================================================
# AGENTS PAGE
# ============================================================================
elif page == "Agents":
    st.header("🤖 Governance Agents")
    st.subheader("Agent Status")
    try:
        df = session.sql("""
            SELECT AGENT_NAME, AGENT_TYPE, EXECUTION_STATUS, ERROR_COUNT, IS_ENABLED
            FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
            ORDER BY AGENT_TYPE, AGENT_NAME
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load agent status")

# ============================================================================
# INACTIVE USERS PAGE
# ============================================================================
elif page == "Inactive Users":
    st.header("👤 Inactive User Management (90+ Days)")

    col1, col2, col3 = st.columns(3)

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG WHERE DAYS_INACTIVE >= 90").collect()
        col1.metric("Inactive Users (90+)", result[0]['COUNT'])
    except:
        col1.metric("Inactive Users (90+)", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG WHERE STATUS = 'flagged'").collect()
        col2.metric("Flagged for Removal", result[0]['COUNT'])
    except:
        col2.metric("Flagged for Removal", "—")

    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.ARCHIVED_USERS").collect()
        col3.metric("Archived Users", result[0]['COUNT'])
    except:
        col3.metric("Archived Users", "—")

    st.divider()

    st.subheader("Inactive Users (90+ Days)")
    try:
        df = session.sql("""
            SELECT USER_NAME, USER_EMAIL, DAYS_INACTIVE, STATUS, FLAGGED_FOR_REMOVAL, LAST_LOGIN
            FROM GOVERNANCE.GOVERNANCE.USER_ACTIVITY_LOG
            WHERE DAYS_INACTIVE >= 90
            ORDER BY DAYS_INACTIVE DESC
        """).to_pandas()

        if len(df) > 0:
            st.dataframe(df, use_container_width=True)

            st.subheader("User Actions")
            selected_user = st.selectbox(
                "Select user to take action",
                df['USER_NAME'].tolist() if len(df) > 0 else [],
                key="inactive_user_select"
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🔴 Disable User", key="disable_btn"):
                    try:
                        session.sql(f"CALL GOVERNANCE.GOVERNANCE.DISABLE_INACTIVE_USER('{selected_user}', 'Manual disable via dashboard')").collect()
                        st.success(f"✅ User {selected_user} disabled")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")

            with col2:
                if st.button("🗑️ Revoke Roles", key="revoke_btn"):
                    try:
                        session.sql(f"CALL GOVERNANCE.GOVERNANCE.REVOKE_INACTIVE_USER_ROLES('{selected_user}')").collect()
                        st.success(f"✅ Roles revoked for {selected_user}")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")

            with col3:
                if st.button("⚙️ Archive & Remove", key="remove_btn"):
                    try:
                        session.sql(f"CALL GOVERNANCE.GOVERNANCE.REMOVE_INACTIVE_USER_COMPLETE('{selected_user}')").collect()
                        st.success(f"✅ User {selected_user} removed")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")
        else:
            st.info("✅ No inactive users found!")

    except Exception as e:
        st.warning(f"Could not load inactive users: {str(e)[:100]}")

    st.divider()

    st.subheader("Archived Users History")
    try:
        df = session.sql("""
            SELECT USER_NAME, USER_EMAIL, CREATED_ON, LAST_LOGIN, ARCHIVED_ON
            FROM GOVERNANCE.GOVERNANCE.ARCHIVED_USERS
            ORDER BY ARCHIVED_ON DESC
            LIMIT 20
        """).to_pandas()

        if len(df) > 0:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No archived users yet")

    except Exception as e:
        st.warning(f"Could not load archived users: {str(e)[:100]}")

# Footer
st.divider()
st.markdown("**Snowflake Governance Dashboard** | Real-time monitoring of governance, security, performance, and health")
