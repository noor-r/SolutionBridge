"""SolutionBridge — Product Integration & ML-Assisted Troubleshooting Platform.

Enterprise Streamlit Dashboard for Product Solutions Engineers.
"""

import sys
from pathlib import Path

# Ensure project root directory is prioritized over dashboard directory
# to prevent 'dashboard/app.py' from colliding with the top-level 'app' package.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
_DASHBOARD_DIR = str(Path(__file__).resolve().parent)
while _DASHBOARD_DIR in sys.path:
    sys.path.remove(_DASHBOARD_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import json
from datetime import datetime, timedelta, timezone
import altair as alt
import pandas as pd
import requests
import streamlit as st

from app.db.database import SessionLocal
from app.services.sql_validation_service import SQLValidationService
from app.services.anomaly_service import AnomalyDetectionService
from app.services.classification_service import IncidentClassificationService
from app.services.similarity_service import IncidentSimilarityService

# Configure Page
st.set_page_config(
    page_title="SolutionBridge — Solutions Engineering Platform",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-passed {
        background-color: #dcfce7;
        color: #15803d;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-failed {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .evidence-box {
        background-color: #f1f5f9;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 0 6px 6px 0;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# Application Configuration
BACKEND_URL = "http://127.0.0.1:8000"


def api_get(endpoint: str, params: dict = None):
    try:
        resp = requests.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def api_post(endpoint: str, json_data: dict = None, params: dict = None):
    try:
        resp = requests.post(f"{BACKEND_URL}{endpoint}", json=json_data, params=params, timeout=10.0)
        return resp.status_code, resp.json() if resp.status_code < 500 else {"detail": resp.text}
    except Exception as exc:
        return 500, {"detail": str(exc)}


def api_patch(endpoint: str, json_data: dict = None):
    try:
        resp = requests.patch(f"{BACKEND_URL}{endpoint}", json=json_data, timeout=5.0)
        return resp.status_code, resp.json()
    except Exception as exc:
        return 500, {"detail": str(exc)}


# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/fluency/96/network-bridge.png", width=64)
st.sidebar.title("SolutionBridge")
st.sidebar.caption("Product Solutions Engineer Platform")

navigation = st.sidebar.radio(
    "Navigation",
    [
        "📊 Overview",
        "👥 Customers",
        "🧪 API Test Center",
        "🚨 Incident Center",
        "📜 Log Explorer",
        "🔍 SQL Validation",
        "🤖 ML Diagnostics",
        "📑 Incident Details",
        "📈 System Health",
    ],
    key="portal_sidebar_navigation",
)

st.sidebar.divider()
st.sidebar.caption(f"Backend Gateway: `{BACKEND_URL}`")

# Quick Demo Trigger in Sidebar
st.sidebar.subheader("⚡ Failure Simulator")
sim_scenario = st.sidebar.selectbox(
    "Select Fault Injection Scenario",
    [
        "database_timeout",
        "invalid_authentication",
        "slow_sql_query",
        "503_service_unavailable",
        "missing_order_record",
        "invalid_request_payload",
        "500_application_exception",
        "high_cpu_memory",
        "webhook_failure",
        "data_inconsistency",
    ],
    key="portal_sidebar_sim_scenario",
)
sim_cust = st.sidebar.selectbox("Target Customer", [1, 2, 3], format_func=lambda x: f"Customer #{x}")

if st.sidebar.button("Inject Fault Scenario", type="primary", use_container_width=True):
    status_code, res = api_post("/api/v1/demo/scenario", json_data={"scenario": sim_scenario, "customer_id": sim_cust})
    if status_code == 200:
        st.sidebar.success(f"Fault Triggered: {res.get('scenario')}")
        st.sidebar.info(f"Request ID: `{res.get('request_id')}`")
        st.session_state["last_sim_req"] = res.get("request_id")
    else:
        st.sidebar.error(f"Error {status_code}: {res.get('detail')}")

# ===================================================================
# 1. OVERVIEW PAGE
# ===================================================================
if navigation == "📊 Overview":
    st.markdown('<div class="main-header">Solutions Engineering Operations Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live integration health, active partner incidents, and telemetry trends</div>', unsafe_allow_html=True)

    summary = api_get("/api/v1/tests/summary") or {}
    incidents = api_get("/api/v1/incidents") or []
    metrics = api_get("/api/v1/metrics", params={"limit": 60}) or []

    open_incidents = [i for i in incidents if i.get("status") == "OPEN"]
    pass_rate = summary.get("pass_rate", 94.5)
    avg_latency = summary.get("avg_response_time_ms", 125.0)

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Integration Pass Rate", f"{pass_rate}%", delta="+0.8%" if pass_rate >= 90 else "-3.2%")
    with col2:
        st.metric("Open Partner Incidents", len(open_incidents), delta=f"{len(open_incidents)} needing triage", delta_color="inverse")
    with col3:
        st.metric("Average API Latency", f"{avg_latency} ms", delta="-12ms" if avg_latency < 300 else "+140ms")
    with col4:
        db_lat = metrics[0].get("db_latency_ms", 6.5) if metrics else 6.5
        st.metric("Current DB Latency", f"{db_lat:.1f} ms", delta="Normal" if db_lat < 25.0 else "ELEVATED", delta_color="inverse" if db_lat >= 25 else "normal")

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("System Telemetry Trend (Last 30 Observations)")
        if metrics:
            df_metrics = pd.DataFrame(metrics)
            df_metrics["timestamp"] = pd.to_datetime(df_metrics["timestamp"])
            df_metrics = df_metrics.sort_values("timestamp")

            chart_data = df_metrics[["timestamp", "cpu_percent", "memory_percent", "db_latency_ms"]].melt(
                id_vars=["timestamp"], var_name="Metric", value_name="Value"
            )

            chart = alt.Chart(chart_data).mark_line().encode(
                x="timestamp:T",
                y="Value:Q",
                color=alt.Color("Metric:N", scale=alt.Scale(range=["#3b82f6", "#10b981", "#f59e0b"])),
                tooltip=["timestamp:T", "Metric:N", "Value:Q"],
            ).properties(height=280)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No telemetry observations found.")

    with col_right:
        st.subheader("Incidents by Category")
        if incidents:
            df_inc = pd.DataFrame(incidents)
            cat_counts = df_inc["category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]

            bar_chart = alt.Chart(cat_counts).mark_bar().encode(
                x="Count:Q",
                y=alt.Y("Category:N", sort="-x"),
                color=alt.Color("Category:N", legend=None),
                tooltip=["Category", "Count"],
            ).properties(height=280)
            st.altair_chart(bar_chart, use_container_width=True)
        else:
            st.info("No incidents logged.")

    st.subheader("Recent Integration Incidents Feed")
    if incidents:
        df_display = pd.DataFrame(incidents)[["id", "request_id", "title", "category", "severity", "status", "created_at"]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No incidents logged.")

# ===================================================================
# 2. CUSTOMERS PAGE
# ===================================================================
elif navigation == "👥 Customers":
    st.markdown('<div class="main-header">Customer Integration Accounts</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage client integration environments, test credentials, and partner SLAs</div>', unsafe_allow_html=True)

    customers = api_get("/api/v1/customers") or []

    if customers:
        cols = st.columns(len(customers))
        for idx, cust in enumerate(customers):
            with cols[idx]:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style="margin:0; font-size:18px;">{cust['name']}</h3>
                    <p style="color:#64748b; font-size:12px; margin:2px 0 8px 0;">{cust['email']}</p>
                    <p><strong>Environment:</strong> <code>{cust['environment']}</code></p>
                    <p><strong>Masked Key:</strong> <code>{cust['masked_api_key']}</code></p>
                    <p><strong>Status:</strong> <span class="badge-passed">{cust['status'].upper()}</span></p>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # Customer Integration Health Scorecard (Query 10)
    st.subheader("Partner Health Scorecard (Forensic SQL Inspection)")
    selected_cust_id = st.selectbox("Select Partner Account", [c["id"] for c in customers], format_func=lambda cid: next((c["name"] for c in customers if c["id"] == cid), str(cid)))

    # Use direct query 10 logic via API or database
    orders = api_get(f"/api/v1/customers/{selected_cust_id}/orders") or []
    st.write(f"**Total Recent Orders:** {len(orders)}")
    if orders:
        df_ord = pd.DataFrame(orders)[["id", "external_order_id", "status", "amount", "created_at"]]
        st.dataframe(df_ord.head(10), use_container_width=True, hide_index=True)

# ===================================================================
# 3. API TEST CENTER
# ===================================================================
elif navigation == "🧪 API Test Center":
    st.markdown('<div class="main-header">API Integration Test Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Run automated regression tests and Newman Postman suites against endpoints</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 3])
    with c1:
        test_cust = st.selectbox("Execute as Customer", [1, 2, 3], format_func=lambda x: f"Customer #{x}")
        if st.button("🚀 Run Live Test Suite", type="primary", use_container_width=True):
            with st.spinner("Executing API test suite across all registered endpoints..."):
                status_code, test_run_data = api_post("/api/v1/tests/run", params={"customer_id": test_cust})
                if status_code == 200:
                    st.success(f"Completed {test_run_data.get('total_tests')} tests! Pass rate: {test_run_data.get('pass_rate_percent')}%")
                else:
                    st.error(f"Test run failed: {test_run_data}")

    with c2:
        st.info("💡 **Newman Integration**: You can also run the full Newman Postman test collection via CLI:\n`npx --yes newman run postman/SolutionBridge.postman_collection.json -e postman/SolutionBridge.postman_environment.json`")

    st.divider()
    st.subheader("Recent API Test Executions")
    test_results = api_get("/api/v1/tests/results", params={"limit": 25}) or []
    if test_results:
        df_tests = pd.DataFrame(test_results)[["id", "endpoint_id", "request_id", "status_code", "response_time_ms", "test_status", "error_message", "created_at"]]
        st.dataframe(df_tests, use_container_width=True, hide_index=True)
    else:
        st.info("No test run records found.")

# ===================================================================
# 4. INCIDENT CENTER
# ===================================================================
elif navigation == "🚨 Incident Center":
    st.markdown('<div class="main-header">Incident Management Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Triage, investigate, and analyze partner integration failures in real time</div>', unsafe_allow_html=True)

    # Trigger Instant Investigation
    st.subheader("🔍 Investigate Request ID")
    investigate_col1, investigate_col2 = st.columns([3, 1])
    with investigate_col1:
        default_req = st.session_state.get("last_sim_req", "")
        req_input = st.text_input("Enter Request ID to Investigate (e.g., REQ-XXXX or from simulator):", value=default_req)
    with investigate_col2:
        st.write("")
        st.write("")
        trigger_btn = st.button("Run Full Forensic Analysis", type="primary", use_container_width=True)

    if trigger_btn and req_input:
        with st.spinner(f"Running multi-source analysis for {req_input}..."):
            status_code, diag = api_post(f"/api/v1/incidents/analyze/{req_input.strip()}")
            if status_code == 200:
                st.success(f"Incident Analysis Complete! Category: **{diag.get('category')}** (Confidence: {diag.get('confidence')*100:.1f}%)")
                st.info(f"Probable Cause: {diag.get('predicted_root_cause')}")
                st.markdown("#### Deterministic & ML Evidence:")
                for ev in diag.get("deterministic_evidence", []):
                    st.markdown(f"<div class='evidence-box'>{ev}</div>", unsafe_allow_html=True)
            else:
                st.error(f"Analysis failed: {diag.get('detail')}")

    st.divider()
    st.subheader("All Tracked Incidents")
    incidents = api_get("/api/v1/incidents") or []
    if incidents:
        st.dataframe(pd.DataFrame(incidents)[["id", "customer_id", "request_id", "category", "severity", "confidence", "status", "created_at"]], use_container_width=True, hide_index=True)
    else:
        st.info("No incidents found.")

# ===================================================================
# 5. LOG EXPLORER
# ===================================================================
elif navigation == "📜 Log Explorer":
    st.markdown('<div class="main-header">Structured Log Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Search, correlate, and inspect JSON structured logs across distributed services</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        filter_req = st.text_input("Filter by Request ID", value=st.session_state.get("last_sim_req", ""))
    with c2:
        filter_level = st.selectbox("Filter by Level", ["ALL", "INFO", "WARNING", "ERROR", "CRITICAL"])
    with c3:
        filter_service = st.selectbox("Filter by Service", ["ALL", "order-service", "gateway-service", "auth-service", "product-service", "database-cluster"])

    params = {"limit": 100}
    if filter_req:
        params["request_id"] = filter_req.strip()
    if filter_level != "ALL":
        params["level"] = filter_level
    if filter_service != "ALL":
        params["service"] = filter_service

    logs = api_get("/api/v1/logs", params=params) or []

    st.write(f"**Found {len(logs)} structured log records:**")
    if logs:
        df_logs = pd.DataFrame(logs)[["id", "timestamp", "level", "service", "customer_id", "request_id", "endpoint", "status_code", "error_code", "response_time_ms", "message"]]
        st.dataframe(df_logs, use_container_width=True, hide_index=True)

        # JSON Inspector
        selected_log_id = st.selectbox("Select Log ID to inspect JSON payload", [l["id"] for l in logs])
        selected_log = next((l for l in logs if l["id"] == selected_log_id), None)
        if selected_log:
            st.json(selected_log)
    else:
        st.info("No logs matched the current filters.")

# ===================================================================
# 6. SQL VALIDATION
# ===================================================================
elif navigation == "🔍 SQL Validation":
    st.markdown('<div class="main-header">Forensic SQL Validation Layer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Direct, parameterized raw SQL diagnostic queries for Product Solutions Engineers</div>', unsafe_allow_html=True)
    st.info("🔒 **Controlled Access**: Arbitrary SQL execution is strictly disabled. Predefined, parameterized diagnostic tools prevent data corruption.")

    # Use SQL Validation Service directly for high-performance parameterized query execution
    db_session = SessionLocal()
    sql_svc = SQLValidationService(db_session)

    query_choice = st.selectbox(
        "Select Forensic SQL Diagnostic Query",
        [
            "Query 01: Verify Order Persistence in Database",
            "Query 02: Detect Duplicate External Order Submissions",
            "Query 03: Endpoint Latency Statistics & SLA Percentiles",
            "Query 04: Aggregate Error Codes by Request ID",
            "Query 05: Customer-Specific Failure Rate Analysis",
            "Query 06: Detect Stalled / Incomplete Order Transactions",
            "Query 07: Database Latency & Connection Spikes",
            "Query 08: Find Unhandled 5xx Server Exceptions",
            "Query 09: Detect Silent Order Rollbacks (Data Inconsistency)",
            "Query 10: Customer Integration Health Scorecard",
            "Query 11: Top Failing API Endpoints",
        ],
    )

    st.divider()

    try:
        if "Query 01:" in query_choice:
            st.markdown("### Query 01: Verify Order Persistence")
            st.caption("Verifies whether an order acknowledged via API actually reached and committed to the database.")
            c1, c2 = st.columns(2)
            with c1:
                q_cid = st.number_input("Customer ID", min_value=1, max_value=10, value=1)
            with c2:
                q_oid = st.text_input("External Order ID", value="ORD-EXT-1001")
            res = sql_svc.validate_order_persistence(q_cid, q_oid)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["rows"]:
                st.dataframe(pd.DataFrame(res["rows"]), use_container_width=True)

        elif "Query 02:" in query_choice:
            st.markdown("### Query 02: Detect Duplicate Order Submissions")
            st.caption("Identifies duplicate orders created due to missing client idempotency headers.")
            c1, c2 = st.columns(2)
            with c1:
                q_cid = st.number_input("Customer ID", min_value=1, max_value=10, value=1)
            with c2:
                q_oid = st.text_input("External Order ID", value="ORD-EXT-1001")
            res = sql_svc.check_duplicate_orders(q_cid, q_oid)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["rows"]:
                st.dataframe(pd.DataFrame(res["rows"]), use_container_width=True)

        elif "Query 03:" in query_choice:
            st.markdown("### Query 03: Endpoint Latency Statistics")
            st.caption("Calculates average, minimum, and maximum response times for an endpoint.")
            c1, c2 = st.columns(2)
            with c1:
                ep_id = st.number_input("Endpoint ID", min_value=1, max_value=15, value=7)
            with c2:
                hrs = st.number_input("Window (Hours)", min_value=1, max_value=168, value=24)
            res = sql_svc.inspect_endpoint_latency_stats(ep_id, hrs)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["stats"]:
                st.json(res["stats"])

        elif "Query 04:" in query_choice:
            st.markdown("### Query 04: Aggregate Error Codes by Request ID")
            st.caption("Correlates all error codes logged for a single transaction.")
            r_id = st.text_input("Request ID", value=st.session_state.get("last_sim_req", "REQ-LOG-20005"))
            res = sql_svc.aggregate_error_codes_by_request(r_id)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["error_summary"]:
                st.dataframe(pd.DataFrame(res["error_summary"]), use_container_width=True)

        elif "Query 05:" in query_choice:
            st.markdown("### Query 05: Customer Failure Rate Analysis")
            st.caption("Quantifies whether an issue is customer-specific or platform-wide.")
            c1, c2 = st.columns(2)
            with c1:
                q_cid = st.number_input("Customer ID", min_value=1, max_value=10, value=1)
            with c2:
                hrs = st.number_input("Time Window (Hours)", min_value=1, max_value=168, value=24)
            res = sql_svc.check_customer_failure_rate(q_cid, hrs)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["metrics"]:
                st.json(res["metrics"])

        elif "Query 06:" in query_choice:
            st.markdown("### Query 06: Detect Stalled Orders")
            st.caption("Discovers orders stuck in PENDING or PROCESSING states.")
            h_thresh = st.slider("Stalled Threshold (Hours)", min_value=1, max_value=48, value=2)
            res = sql_svc.detect_status_mismatches(h_thresh)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["rows"]:
                st.dataframe(pd.DataFrame(res["rows"]), use_container_width=True)

        elif "Query 07:" in query_choice:
            st.markdown("### Query 07: Database Latency & Connection Spikes")
            st.caption("Forensic inspection of DB resource contention.")
            lat_thresh = st.slider("DB Latency Threshold (ms)", min_value=10.0, max_value=200.0, value=40.0)
            res = sql_svc.inspect_db_contention_metrics(lat_thresh)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["rows"]:
                st.dataframe(pd.DataFrame(res["rows"]), use_container_width=True)

        elif "Query 08:" in query_choice:
            st.markdown("### Query 08: Unhandled 5xx Server Exceptions")
            st.caption("Filters raw application error logs.")
            h_win = st.slider("Lookback Hours", min_value=1, max_value=72, value=12)
            res = sql_svc.find_unhandled_exceptions(h_win)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["rows"]:
                st.dataframe(pd.DataFrame(res["rows"]), use_container_width=True)

        elif "Query 09:" in query_choice:
            st.markdown("### Query 09: Detect Silent Order Rollbacks")
            st.caption("Reconciles HTTP 201 log acknowledgments against actual database rows.")
            r_id = st.text_input("Request ID", value=st.session_state.get("last_sim_req", ""))
            res = sql_svc.detect_silent_order_rollbacks(r_id)
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["log_entries"]:
                st.write("Correlated Log Entries:")
                st.dataframe(pd.DataFrame(res["log_entries"]), use_container_width=True)

        elif "Query 10:" in query_choice:
            st.markdown("### Query 10: Customer Integration Health Scorecard")
            st.caption("Generates volume, order count, and pass-rate summary for customer reviews.")
            q_cid = st.number_input("Customer ID", min_value=1, max_value=10, value=1)
            res = sql_svc.inspect_customer_integration_health(q_cid)
            st.info(f"**Diagnostic Finding:** {res.get('diagnostic_finding')}")
            if res.get("data"):
                st.json(res["data"])

        elif "Query 11:" in query_choice:
            st.markdown("### Query 11: Top Failing Endpoints")
            st.caption("Ranks endpoints with the highest failure rates across test runs.")
            res = sql_svc.get_top_failing_endpoints()
            st.info(f"**Diagnostic Finding:** {res['diagnostic_finding']}")
            if res["endpoints"]:
                st.dataframe(pd.DataFrame(res["endpoints"]), use_container_width=True)

    finally:
        db_session.close()

# ===================================================================
# 7. ML DIAGNOSTICS
# ===================================================================
elif navigation == "🤖 ML Diagnostics":
    st.markdown('<div class="main-header">Machine Learning Intelligence Layer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Interactive inference testing and evaluation metrics for Anomaly Detection, Classification, and FAISS Similarity</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "🌲 Isolation Forest Anomaly Detector",
        "🎯 TF-IDF + Logistic Regression Classifier",
        "🔎 Sentence-Transformers + FAISS Retrieval",
    ])

    with tab1:
        st.subheader("Telemetry Anomaly Detection (Isolation Forest)")
        st.caption("Evaluate real-time system metrics against trained normal baseline.")

        anom_svc = AnomalyDetectionService()

        col1, col2, col3 = st.columns(3)
        with col1:
            test_rt = st.slider("Response Time (ms)", 10.0, 5000.0, 85.0, key="ml_slider_rt")
            test_db = st.slider("DB Latency (ms)", 1.0, 500.0, 6.5, key="ml_slider_db")
        with col2:
            test_cpu = st.slider("CPU Utilization (%)", 5.0, 100.0, 32.0, key="ml_slider_cpu")
            test_mem = st.slider("Memory (%)", 10.0, 100.0, 48.0, key="ml_slider_mem")
        with col3:
            test_req_rate = st.slider("Request Rate (req/s)", 10.0, 2000.0, 180.0, key="ml_slider_req_rate")
            test_err_rate = st.slider("Error Rate (%)", 0.0, 100.0, 0.4, key="ml_slider_err_rate")
            test_conns = st.slider("Active Connections", 5, 150, 25, key="ml_slider_conns")

        vector = {
            "response_time_ms": test_rt,
            "db_latency_ms": test_db,
            "cpu_percent": test_cpu,
            "memory_percent": test_mem,
            "request_rate": test_req_rate,
            "error_rate": test_err_rate,
            "active_connections": float(test_conns),
        }

        anom_res = anom_svc.detect_anomaly(vector)
        if anom_res.get("is_anomaly"):
            st.error(f"🚨 **ANOMALY DETECTED** (Score: {anom_res.get('anomaly_score')})")
            st.write(anom_res.get("explanation"))
        else:
            st.success(f"✅ **NORMAL TELEMETRY** (Score: {anom_res.get('anomaly_score')})")
            st.write(anom_res.get("explanation"))

        # Holdout Metrics
        metrics_file = Path("ml/artifacts/anomaly_metrics.json")
        if metrics_file.exists():
            with open(metrics_file, "r") as f:
                am = json.load(f)
            st.divider()
            st.caption(f"**Offline Holdout Metrics**: Precision: {am['precision']} | Recall: {am['recall']} | F1: {am['f1_score']} | ROC-AUC: {am['roc_auc']}")

    with tab2:
        st.subheader("Incident Category Classifier (TF-IDF + Logistic Regression)")
        st.caption("Predicts likely incident category across 7 PSE classes.")

        clf_svc = IncidentClassificationService()

        test_msg = st.text_area(
            "Input Log / Incident Text",
            value="Database connection pool timeout waiting for connection on POST /api/v1/orders",
            key="ml_clf_input_msg",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            t_err = st.text_input("Error Code", value="DB_TIMEOUT", key="ml_clf_err_code")
        with c2:
            t_status = st.number_input("HTTP Status", value=500, key="ml_clf_http_status")
        with c3:
            t_rt = st.number_input("Response Time (ms)", value=4820.0, key="ml_clf_rt_ms")

        clf_res = clf_svc.classify_incident(
            message=test_msg,
            error_code=t_err,
            status_code=t_status,
            response_time_ms=t_rt,
        )

        st.success(f"Predicted Category: **{clf_res['predicted_category']}** ({clf_res['probability']*100:.1f}% Confidence)")

        # Probabilities Bar Chart
        if clf_res.get("class_probabilities"):
            df_probs = pd.DataFrame(list(clf_res["class_probabilities"].items()), columns=["Category", "Probability"])
            p_chart = alt.Chart(df_probs).mark_bar().encode(
                x=alt.X("Probability:Q", scale=alt.Scale(domain=[0, 1])),
                y=alt.Y("Category:N", sort="-x"),
                color=alt.Color("Category:N", legend=None),
            ).properties(height=220)
            st.altair_chart(p_chart, use_container_width=True)

    with tab3:
        st.subheader("Semantic Incident Retrieval (Sentence-Transformers + FAISS)")
        st.caption("Queries 110 historical postmortems and past engineering resolutions using dense 384-d embeddings.")

        sim_svc = IncidentSimilarityService()

        sim_query = st.text_input(
            "Natural Language Incident Query:",
            value="POST /orders returned 500 database timeout and orders were not saved",
            key="ml_sim_query_input",
        )

        if st.button("Search Historical Incidents", type="primary", key="ml_sim_search_btn"):
            matches = sim_svc.find_similar_incidents(sim_query, top_k=3)
            for m in matches:
                st.markdown(f"""
                <div class="evidence-box">
                    <strong>#{m['incident_id']} — {m['title']}</strong> (Similarity: {m['similarity_score']*100:.1f}%)<br/>
                    <small><strong>Category:</strong> {m['category']}</small><br/>
                    <em>Summary:</em> {m['summary']}<br/>
                    <strong style="color:#0f766e;">Past Engineering Resolution:</strong> {m['resolution']}
                </div>
                """, unsafe_allow_html=True)

# ===================================================================
# 8. INCIDENT DETAILS PAGE
# ===================================================================
elif navigation == "📑 Incident Details":
    st.markdown('<div class="main-header">Incident Deep-Dive & Forensic Dossier</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive 360-degree investigation view: API, SQL, Logs, Metrics, ML, and Remediation</div>', unsafe_allow_html=True)

    incidents = api_get("/api/v1/incidents") or []
    if not incidents:
        st.info("No incidents logged yet. Trigger a fault scenario from the sidebar first!")
    else:
        inc_ids = [i["id"] for i in incidents]
        selected_id = st.selectbox("Select Incident Dossier", inc_ids, format_func=lambda i: f"Incident #{i} — {next(x['title'] for x in incidents if x['id'] == i)}")

        inc = next(i for i in incidents if i["id"] == selected_id)

        # Header Info
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Category", inc["category"])
        c2.metric("Severity", inc["severity"])
        c3.metric("Status", inc["status"])
        c4.metric("Diagnostic Confidence", f"{inc['confidence']*100:.1f}%")

        st.markdown(f"**Request ID:** `X-Request-ID: {inc['request_id']}`")
        st.markdown(f"**Probable Root Cause:** {inc['predicted_root_cause']}")

        st.divider()

        # Evidence Accordion Tabs
        with st.expander("📊 1. Correlated Structured Logs", expanded=True):
            logs = api_get(f"/api/v1/logs/{inc['request_id']}") or []
            if logs:
                st.dataframe(pd.DataFrame(logs)[["timestamp", "level", "service", "status_code", "error_code", "message"]], use_container_width=True, hide_index=True)
            else:
                st.caption("No logs correlated for this request ID.")

        with st.expander("🔍 2. Raw SQL Evidence & Data State", expanded=True):
            st.markdown(f"```text\n{inc.get('evidence_summary', 'SQL inspection active')}\n```")

        with st.expander("🤖 3. Machine Learning & Similar Historical Incidents", expanded=True):
            diag = api_get(f"/api/v1/incidents/{selected_id}/diagnosis")
            if diag and diag.get("similar_incidents"):
                for m in diag["similar_incidents"]:
                    st.markdown(f"**#{m['incident_id']} — {m['title']}** (Similarity: {m['similarity_score']*100:.1f}%)")
                    st.caption(f"Past Resolution: {m['resolution']}")
            else:
                st.caption("Semantic matches ready upon investigation.")

        with st.expander("🛠️ 4. Actionable Troubleshooting Remediation", expanded=True):
            recs = api_get(f"/api/v1/incidents/{selected_id}/recommendations")
            if recs and recs.get("actions"):
                for a in recs["actions"]:
                    st.markdown(f"**Priority {a['priority']}: {a['action']}**")
                    st.write(f"*Rationale:* {a['rationale']}")
                    st.caption(f"*Verification Step:* `{a['verification_step']}`")
                    st.divider()

        # Engineer vs Customer Summaries (Refinement 11)
        st.subheader("Dual Incident Communications (Product Solutions Engineer Workflow)")
        col_eng, col_cust = st.columns(2)
        diag = api_get(f"/api/v1/incidents/{selected_id}/diagnosis") or {}
        with col_eng:
            st.markdown("#### 🔧 Engineer-Facing Technical Postmortem")
            st.text_area("Internal Technical Summary", value=diag.get("engineer_summary", "Technical details..."), height=200)
        with col_cust:
            st.markdown("#### 🤝 Customer-Facing Executive Communication")
            st.text_area("Customer Support Communication", value=diag.get("customer_summary", "Customer details..."), height=200)

        # Status Update Action
        st.divider()
        st.subheader("Update Incident Status")
        new_status = st.selectbox("Lifecycle State", ["OPEN", "INVESTIGATING", "RESOLVED"], index=["OPEN", "INVESTIGATING", "RESOLVED"].index(inc["status"]))
        res_notes = st.text_input("Resolution Notes (Optional)")
        if st.button("Save Status Update", type="primary"):
            status_code, updated = api_patch(f"/api/v1/incidents/{selected_id}/status", json_data={"status": new_status, "resolution_notes": res_notes})
            if status_code == 200:
                st.success(f"Incident #{selected_id} updated to {new_status}!")
                st.rerun()

# ===================================================================
# 9. SYSTEM HEALTH
# ===================================================================
elif navigation == "📈 System Health":
    st.markdown('<div class="main-header">System Health & Telemetry Metrics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time infrastructure capacity, host saturation, and connection pool metrics</div>', unsafe_allow_html=True)

    metrics = api_get("/api/v1/metrics", params={"limit": 60}) or []
    if metrics:
        latest = metrics[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CPU Utilization", f"{latest['cpu_percent']:.1f}%", delta="High" if latest['cpu_percent'] > 80 else "Normal")
        c2.metric("Memory Usage", f"{latest['memory_percent']:.1f}%", delta="High" if latest['memory_percent'] > 85 else "Normal")
        c3.metric("DB Latency", f"{latest['db_latency_ms']:.1f} ms")
        c4.metric("Active Connections", latest['active_connections'])

        st.divider()

        df_m = pd.DataFrame(metrics)
        df_m["timestamp"] = pd.to_datetime(df_m["timestamp"])
        df_m = df_m.sort_values("timestamp")

        st.subheader("Telemetry Timeseries")
        st.line_chart(df_m.set_index("timestamp")[["cpu_percent", "memory_percent", "db_latency_ms"]])

        st.subheader("Raw Telemetry Observations")
        st.dataframe(df_m, use_container_width=True, hide_index=True)
    else:
        st.info("No system metrics available.")
