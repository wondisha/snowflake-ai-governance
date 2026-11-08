"""
Snowflake Governance Dashboard - Streamlit App
Runs natively in Snowsight
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

# Get session - Snowsight handles this automatically
try:
    session = get_active_session()
    # Set database and schema context
    session.sql("USE DATABASE GOVERNANCE").collect()
    session.sql("USE SCHEMA GOVERNANCE").collect()
    st.success("✅ Connected to GOVERNANCE.GOVERNANCE")
except Exception as e:
    st.error(f"Connection error: {str(e)}")
    st.stop()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Dashboard",
    ["Overview", "Security", "Performance", "Cost", "Health", "Incidents", "Agents"]
)

# ============================================================================
# OVERVIEW PAGE
# ============================================================================
if page == "Overview":
    st.header("System Overview")

    col1, col2, col3, col4 = st.columns(4)

    try:
        # Total policies
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.GOVERNANCE.POLICIES").collect()
        col1.metric("Active Policies", result[0]['COUNT'])
    except:
        col1.metric("Active Policies", "—")

    try:
        # Security rules
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.SECURITY_RULES").collect()
        col2.metric("Security Rules", result[0]['COUNT'])
    except:
        col2.metric("Security Rules", "—")

    try:
        # Open incidents
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE STATUS IN ('open', 'in_progress')").collect()
        col3.metric("Open Incidents", result[0]['COUNT'])
    except:
        col3.metric("Open Incidents", "—")

    try:
        # Pending approvals
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS WHERE STATUS = 'pending'").collect()
        col4.metric("Pending Approvals", result[0]['COUNT'])
    except:
        col4.metric("Pending Approvals", "—")

    st.divider()

    # Recent audit logs
    st.subheader("Recent Audit Logs")
    try:
        df = session.sql("""
            SELECT
                EVENT_TYPE,
                EVENT_CATEGORY,
                RESOURCE_TYPE,
                RESOURCE_NAME,
                ACTOR_EMAIL,
                EVENT_TIMESTAMP,
                STATUS
            FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
            ORDER BY EVENT_TIMESTAMP DESC
            LIMIT 10
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load audit logs")

    # Agent health
    st.subheader("Agent Health Status")
    try:
        df = session.sql("""
            SELECT
                AGENT_NAME,
                AGENT_TYPE,
                EXECUTION_STATUS,
                LAST_SUCCESSFUL_EXECUTION,
                ERROR_COUNT,
                IS_ENABLED
            FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
            ORDER BY LAST_SUCCESSFUL_EXECUTION DESC
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load agent health")

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
            SELECT
                DATABASE_NAME,
                SCHEMA_NAME,
                TABLE_NAME,
                COLUMN_NAME,
                PII_TYPE,
                CONFIDENCE_SCORE,
                STATUS
            FROM GOVERNANCE.GOVERNANCE.PII_DETECTIONS
            ORDER BY DETECTED_AT DESC
            LIMIT 20
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
            SELECT
                QUERY_ID,
                WAREHOUSE_NAME,
                USER_EMAIL,
                EXECUTION_TIME_SECONDS,
                DATA_SCANNED_GB,
                PERFORMANCE_SCORE,
                IS_OPTIMIZABLE
            FROM GOVERNANCE.GOVERNANCE.QUERY_ANALYSIS
            ORDER BY ANALYSIS_TIMESTAMP DESC
            LIMIT 20
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
            SELECT
                WAREHOUSE_NAME,
                COUNT(*) as query_count,
                SUM(CREDITS_USED) as total_credits,
                AVG(EXECUTION_TIME_SECONDS) as avg_time
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
            SELECT
                WAREHOUSE_NAME,
                METRIC_TIMESTAMP,
                CPU_PERCENT,
                MEMORY_PERCENT,
                HEALTH_STATUS
            FROM GOVERNANCE.GOVERNANCE.WAREHOUSE_HEALTH
            ORDER BY METRIC_TIMESTAMP DESC
            LIMIT 20
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
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.REMEDIATION_ACTIONS WHERE STATUS = 'success'").collect()
        col3.metric("Resolved", result[0]['COUNT'])
    except:
        col3.metric("Resolved", "—")

    st.divider()

    st.subheader("Open Incidents")
    try:
        df = session.sql("""
            SELECT
                INCIDENT_ID,
                SEVERITY,
                CATEGORY,
                DESCRIPTION,
                DETECTED_TIMESTAMP,
                STATUS
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
            SELECT
                AGENT_NAME,
                AGENT_TYPE,
                EXECUTION_STATUS,
                ERROR_COUNT,
                IS_ENABLED
            FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
            ORDER BY AGENT_TYPE, AGENT_NAME
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("Could not load agent status")

st.divider()
st.markdown("**Snowflake Governance Dashboard** | Real-time monitoring")

# ============================================================================
# OVERVIEW PAGE
# ============================================================================
if page == "Overview":
    st.header("System Overview")

    col1, col2, col3, col4 = st.columns(4)

    # Total policies
    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.POLICIES").collect()
        with col1:
            st.metric("Active Policies", result[0]['COUNT'])
    except:
        col1.metric("Active Policies", "—")

    # Security rules
    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.SECURITY_RULES").collect()
        with col2:
            st.metric("Security Rules", result[0]['COUNT'])
    except:
        col2.metric("Security Rules", "—")

    # Open incidents
    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE STATUS IN ('open', 'in_progress')").collect()
        with col3:
            st.metric("Open Incidents", result[0]['COUNT'])
    except:
        col3.metric("Open Incidents", "—")

    # Pending approvals
    try:
        result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.APPROVAL_REQUESTS WHERE STATUS = 'pending'").collect()
        with col4:
            st.metric("Pending Approvals", result[0]['COUNT'])
    except:
        col4.metric("Pending Approvals", "—")

    st.divider()

    # Recent audit logs
    st.subheader("Recent Audit Logs")
    try:
        df = session.sql("""
            SELECT
                EVENT_TYPE,
                EVENT_CATEGORY,
                RESOURCE_TYPE,
                RESOURCE_NAME,
                ACTOR_EMAIL,
                EVENT_TIMESTAMP,
                STATUS
            FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS
            ORDER BY EVENT_TIMESTAMP DESC
            LIMIT 10
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load audit logs: {str(e)[:100]}")

    # Agent health
    st.subheader("Agent Health Status")
    try:
        df = session.sql("""
            SELECT
                AGENT_NAME,
                AGENT_TYPE,
                EXECUTION_STATUS,
                LAST_SUCCESSFUL_EXECUTION,
                ERROR_COUNT,
                IS_ENABLED
            FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
            ORDER BY LAST_SUCCESSFUL_EXECUTION DESC
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load agent health: {str(e)[:100]}")

# ============================================================================
# SECURITY PAGE
# ============================================================================
elif page == "Security":
    st.header("🔒 Security & Compliance")

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.SECURITY_RULES WHERE ENABLED = TRUE").collect()
            st.metric("Enabled Rules", result[0]['COUNT'])
        except:
            st.metric("Enabled Rules", "—")

    with col2:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.PII_DETECTIONS WHERE STATUS = 'detected'").collect()
            st.metric("PII Detections", result[0]['COUNT'])
        except:
            st.metric("PII Detections", "—")

    with col3:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.AUDIT_LOGS WHERE EVENT_CATEGORY = 'security'").collect()
            st.metric("Security Events", result[0]['COUNT'])
        except:
            st.metric("Security Events", "—")

    st.divider()

    st.subheader("PII Detection Records")
    try:
        df = session.sql("""
            SELECT
                DATABASE_NAME,
                SCHEMA_NAME,
                TABLE_NAME,
                COLUMN_NAME,
                PII_TYPE,
                CONFIDENCE_SCORE,
                STATUS
            FROM GOVERNANCE.GOVERNANCE.PII_DETECTIONS
            ORDER BY DETECTED_AT DESC
            LIMIT 20
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load PII detections: {str(e)[:100]}")

# ============================================================================
# PERFORMANCE PAGE
# ============================================================================
elif page == "Performance":
    st.header("⚡ Performance Optimization")

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.QUERY_ANALYSIS WHERE IS_OPTIMIZABLE = TRUE").collect()
            st.metric("Optimizable Queries", result[0]['COUNT'])
        except:
            st.metric("Optimizable Queries", "—")

    with col2:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.PERFORMANCE_THRESHOLDS WHERE ENABLED = TRUE").collect()
            st.metric("Active Thresholds", result[0]['COUNT'])
        except:
            st.metric("Active Thresholds", "—")

    with col3:
        try:
            result = session.sql("SELECT AVG(EXECUTION_TIME_SECONDS) as avg_time FROM GOVERNANCE.GOVERNANCE.QUERY_ANALYSIS").collect()
            avg_time = result[0]['AVG_TIME']
            st.metric("Avg Query Time", f"{avg_time:.2f}s" if avg_time else "—")
        except:
            st.metric("Avg Query Time", "—")

    st.divider()

    st.subheader("Query Performance Analysis")
    try:
        df = session.sql("""
            SELECT
                QUERY_ID,
                WAREHOUSE_NAME,
                USER_EMAIL,
                EXECUTION_TIME_SECONDS,
                DATA_SCANNED_GB,
                PERFORMANCE_SCORE,
                IS_OPTIMIZABLE
            FROM GOVERNANCE.GOVERNANCE.QUERY_ANALYSIS
            WHERE ANALYSIS_TIMESTAMP >= CURRENT_TIMESTAMP() - INTERVAL '7 days'
            ORDER BY ANALYSIS_TIMESTAMP DESC
            LIMIT 20
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load query analysis: {str(e)[:100]}")

# ============================================================================
# COST PAGE
# ============================================================================
elif page == "Cost":
    st.header("💰 Cost Tracking & Optimization")

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            result = session.sql("SELECT SUM(CREDITS_USED) as total FROM GOVERNANCE.GOVERNANCE.COST_TRACKING WHERE RECORDED_AT >= CURRENT_TIMESTAMP() - INTERVAL '7 days'").collect()
            total = result[0]['TOTAL']
            st.metric("Credits (7 days)", f"{total:.2f}" if total else "—")
        except:
            st.metric("Credits (7 days)", "—")

    with col2:
        try:
            result = session.sql("SELECT COUNT(DISTINCT WAREHOUSE_NAME) as count FROM GOVERNANCE.GOVERNANCE.COST_TRACKING").collect()
            st.metric("Active Warehouses", result[0]['COUNT'])
        except:
            st.metric("Active Warehouses", "—")

    with col3:
        try:
            result = session.sql("SELECT COUNT(DISTINCT USER_EMAIL) as count FROM GOVERNANCE.GOVERNANCE.COST_TRACKING").collect()
            st.metric("Active Users", result[0]['COUNT'])
        except:
            st.metric("Active Users", "—")

    st.divider()

    st.subheader("Cost Summary by Warehouse")
    try:
        df = session.sql("""
            SELECT
                WAREHOUSE_NAME,
                COUNT(*) as query_count,
                SUM(CREDITS_USED) as total_credits,
                AVG(EXECUTION_TIME_SECONDS) as avg_time,
                SUM(DATA_SCANNED_GB) as total_data_scanned
            FROM GOVERNANCE.GOVERNANCE.COST_TRACKING
            WHERE RECORDED_AT >= CURRENT_TIMESTAMP() - INTERVAL '30 days'
            GROUP BY WAREHOUSE_NAME
            ORDER BY TOTAL_CREDITS DESC
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load cost summary: {str(e)[:100]}")

# ============================================================================
# HEALTH PAGE
# ============================================================================
elif page == "Health":
    st.header("❤️ Warehouse Health")

    try:
        df = session.sql("""
            SELECT
                WAREHOUSE_NAME,
                METRIC_TIMESTAMP,
                CPU_PERCENT,
                MEMORY_PERCENT,
                STORAGE_USED_GB,
                ACTIVE_QUERIES,
                FAILED_QUERIES,
                HEALTH_STATUS,
                NOTES
            FROM GOVERNANCE.GOVERNANCE.WAREHOUSE_HEALTH
            ORDER BY METRIC_TIMESTAMP DESC
            LIMIT 20
        """).to_pandas()

        # Color code health status
        def color_health(status):
            if status == "healthy":
                return "🟢"
            elif status == "warning":
                return "🟡"
            else:
                return "🔴"

        df['Status'] = df['HEALTH_STATUS'].apply(color_health) + " " + df['HEALTH_STATUS'].astype(str)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load warehouse health: {str(e)[:100]}")

# ============================================================================
# INCIDENTS PAGE
# ============================================================================
elif page == "Incidents":
    st.header("🚨 Incidents & Issues")

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE STATUS IN ('open', 'in_progress')").collect()
            st.metric("Active Incidents", result[0]['COUNT'])
        except:
            st.metric("Active Incidents", "—")

    with col2:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.INCIDENTS WHERE SEVERITY = 'critical'").collect()
            st.metric("Critical", result[0]['COUNT'])
        except:
            st.metric("Critical", "—")

    with col3:
        try:
            result = session.sql("SELECT COUNT(*) as count FROM GOVERNANCE.GOVERNANCE.REMEDIATION_ACTIONS WHERE STATUS = 'success'").collect()
            st.metric("Resolved", result[0]['COUNT'])
        except:
            st.metric("Resolved", "—")

    st.divider()

    st.subheader("Open Incidents")
    try:
        df = session.sql("""
            SELECT
                INCIDENT_ID,
                SEVERITY,
                CATEGORY,
                DESCRIPTION,
                DETECTED_TIMESTAMP,
                ASSIGNED_TO,
                STATUS,
                ESCALATION_COUNT
            FROM GOVERNANCE.GOVERNANCE.INCIDENTS
            WHERE STATUS IN ('open', 'in_progress')
            ORDER BY DETECTED_TIMESTAMP DESC
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load incidents: {str(e)[:100]}")

# ============================================================================
# AGENTS PAGE
# ============================================================================
elif page == "Agents":
    st.header("🤖 Governance Agents")

    st.subheader("Agent Status")
    try:
        df = session.sql("""
            SELECT
                AGENT_NAME,
                AGENT_TYPE,
                EXECUTION_STATUS,
                ITEMS_DETECTED,
                ITEMS_PROCESSED,
                ERROR_COUNT,
                LAST_ERROR_MESSAGE,
                IS_ENABLED
            FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
            ORDER BY AGENT_TYPE, AGENT_NAME
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load agent status: {str(e)[:100]}")

    st.divider()

    st.subheader("Agent Performance")
    try:
        df = session.sql("""
            SELECT
                AGENT_NAME,
                LAST_SUCCESSFUL_EXECUTION,
                NEXT_SCHEDULED_RUN,
                ERROR_COUNT,
                DATEDIFF(hour, LAST_SUCCESSFUL_EXECUTION, CURRENT_TIMESTAMP()) as hours_since_success
            FROM GOVERNANCE.GOVERNANCE.AGENT_STATE
            ORDER BY LAST_SUCCESSFUL_EXECUTION DESC
        """).to_pandas()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load agent performance: {str(e)[:100]}")

# Footer
st.divider()
st.markdown("""
**Snowflake Governance Dashboard** | Real-time monitoring of governance, security, performance, and health
""")
