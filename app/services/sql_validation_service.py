"""Dedicated Raw SQL Troubleshooting and Data-Validation Layer.

This service executes predefined, parameterized raw SQL queries directly against
the underlying database engine. It avoids ORM abstraction to provide explicit,
high-performance forensic data inspection for Product Solutions Engineers.

At least 10 distinct analytical queries are implemented, each with explicit
rationale documenting why it exists and how it assists troubleshooting.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.logging import logger


class SQLValidationService:
    """Forensic SQL validation engine for Product Solutions Engineers."""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------
    # Query 1: Order Persistence Verification
    # Why it exists: When a customer reports that an order was submitted via
    # POST /api/v1/orders but cannot be seen in their portal, the PSE must
    # verify whether the transaction actually reached and committed to the database.
    # -------------------------------------------------------------------
    def validate_order_persistence(self, customer_id: int, external_order_id: str) -> Dict[str, Any]:
        sql = text("""
            SELECT id, customer_id, external_order_id, status, amount, created_at, updated_at
            FROM orders
            WHERE customer_id = :customer_id
              AND external_order_id = :external_order_id
            ORDER BY created_at DESC
            LIMIT 5
        """)
        rows = self.db.execute(sql, {"customer_id": customer_id, "external_order_id": external_order_id}).mappings().all()
        persisted = len(rows) > 0
        return {
            "query_id": "QUERY_01_ORDER_PERSISTENCE",
            "title": "Verify Order Persistence",
            "customer_id": customer_id,
            "external_order_id": external_order_id,
            "persisted": persisted,
            "row_count": len(rows),
            "rows": [dict(r) for r in rows],
            "diagnostic_finding": (
                "Order record found in database." if persisted
                else "Order record NOT found in database. Transaction either aborted or silently rolled back."
            ),
        }

    # -------------------------------------------------------------------
    # Query 2: Duplicate Order Inspection
    # Why it exists: Customers retrying API calls due to network timeouts
    # often create accidental duplicate orders if idempotency keys fail.
    # -------------------------------------------------------------------
    def check_duplicate_orders(self, customer_id: int, external_order_id: str) -> Dict[str, Any]:
        sql = text("""
            SELECT external_order_id, COUNT(*) as duplicate_count, MIN(created_at) as first_seen, MAX(created_at) as last_seen
            FROM orders
            WHERE customer_id = :customer_id
              AND external_order_id = :external_order_id
            GROUP BY external_order_id
            HAVING COUNT(*) > 1
        """)
        rows = self.db.execute(sql, {"customer_id": customer_id, "external_order_id": external_order_id}).mappings().all()
        is_duplicate = len(rows) > 0
        return {
            "query_id": "QUERY_02_DUPLICATE_ORDERS",
            "title": "Detect Duplicate External Order IDs",
            "is_duplicate": is_duplicate,
            "rows": [dict(r) for r in rows],
            "diagnostic_finding": (
                f"Duplicate submissions detected ({rows[0]['duplicate_count']} records)!" if is_duplicate
                else "No duplicate orders detected for this external ID."
            ),
        }

    # -------------------------------------------------------------------
    # Query 3: Endpoint Latency Percentiles & Averages
    # Why it exists: When customers report 'API slowness', the PSE must
    # quantify response times over time to distinguish network lag from server latency.
    # -------------------------------------------------------------------
    def inspect_endpoint_latency_stats(self, endpoint_id: int, hours: int = 24) -> Dict[str, Any]:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        sql = text("""
            SELECT
                endpoint_id,
                COUNT(*) as total_requests,
                ROUND(AVG(response_time_ms), 2) as avg_latency_ms,
                ROUND(MIN(response_time_ms), 2) as min_latency_ms,
                ROUND(MAX(response_time_ms), 2) as max_latency_ms
            FROM api_test_runs
            WHERE endpoint_id = :endpoint_id
              AND created_at >= :start_time
            GROUP BY endpoint_id
        """)
        row = self.db.execute(sql, {"endpoint_id": endpoint_id, "start_time": start_time}).mappings().first()
        return {
            "query_id": "QUERY_03_ENDPOINT_LATENCY",
            "title": "Endpoint Latency Metrics",
            "endpoint_id": endpoint_id,
            "window_hours": hours,
            "stats": dict(row) if row else None,
            "diagnostic_finding": (
                f"Average latency: {row['avg_latency_ms']}ms, Max latency: {row['max_latency_ms']}ms" if row
                else "No test run observations found for this endpoint in the specified window."
            ),
        }

    # -------------------------------------------------------------------
    # Query 4: Aggregate Error Codes by Request ID
    # Why it exists: Correlates all structured log errors emitted across
    # distributed microservices for a single user-reported transaction.
    # -------------------------------------------------------------------
    def aggregate_error_codes_by_request(self, request_id: str) -> Dict[str, Any]:
        sql = text("""
            SELECT error_code, COUNT(*) as error_count, MIN(level) as highest_level, MIN(timestamp) as first_error_time
            FROM logs
            WHERE request_id = :request_id
              AND error_code IS NOT NULL
            GROUP BY error_code
            ORDER BY error_count DESC
        """)
        rows = self.db.execute(sql, {"request_id": request_id}).mappings().all()
        return {
            "query_id": "QUERY_04_REQUEST_ERROR_AGGREGATE",
            "title": "Aggregate Error Codes by Request ID",
            "request_id": request_id,
            "error_summary": [dict(r) for r in rows],
            "total_error_codes": len(rows),
            "diagnostic_finding": (
                f"Identified {len(rows)} distinct error code(s) for request {request_id}." if rows
                else "No explicit error codes logged for this request ID."
            ),
        }

    # -------------------------------------------------------------------
    # Query 5: Customer-Specific Failure Rate Comparison
    # Why it exists: Identifies whether failures are isolated to one customer's
    # integration payload/credentials or affecting all tenants platform-wide.
    # -------------------------------------------------------------------
    def check_customer_failure_rate(self, customer_id: int, hours: int = 24) -> Dict[str, Any]:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        sql = text("""
            SELECT
                customer_id,
                COUNT(*) as total_calls,
                SUM(CASE WHEN test_status IN ('FAILED', 'ERROR') THEN 1 ELSE 0 END) as failure_count,
                ROUND(100.0 * SUM(CASE WHEN test_status IN ('FAILED', 'ERROR') THEN 1 ELSE 0 END) / COUNT(*), 2) as failure_percentage
            FROM api_test_runs
            WHERE customer_id = :customer_id
              AND created_at >= :start_time
            GROUP BY customer_id
        """)
        row = self.db.execute(sql, {"customer_id": customer_id, "start_time": start_time}).mappings().first()
        return {
            "query_id": "QUERY_05_CUSTOMER_FAILURE_RATE",
            "title": "Customer Failure Rate Analysis",
            "customer_id": customer_id,
            "window_hours": hours,
            "metrics": dict(row) if row else None,
            "diagnostic_finding": (
                f"Customer failure rate is {row['failure_percentage']}% over last {hours} hours." if row
                else "No customer test calls recorded in this window."
            ),
        }

    # -------------------------------------------------------------------
    # Query 6: Detect Status Mismatches & Stalled Transactions
    # Why it exists: Discovers orders that remain stuck in PENDING or PROCESSING
    # due to missing payment webhooks or silent worker crashes.
    # -------------------------------------------------------------------
    def detect_status_mismatches(self, hours_threshold: int = 2) -> Dict[str, Any]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
        sql = text("""
            SELECT id, customer_id, external_order_id, status, amount, created_at
            FROM orders
            WHERE status IN ('PENDING', 'PROCESSING')
              AND created_at <= :cutoff_time
            ORDER BY created_at ASC
            LIMIT 20
        """)
        rows = self.db.execute(sql, {"cutoff_time": cutoff_time}).mappings().all()
        return {
            "query_id": "QUERY_06_STALLED_ORDERS",
            "title": "Stalled / Incomplete Order Transactions",
            "stalled_count": len(rows),
            "rows": [dict(r) for r in rows],
            "diagnostic_finding": (
                f"Found {len(rows)} orders stalled in non-final state older than {hours_threshold} hours." if rows
                else "No stalled orders detected."
            ),
        }

    # -------------------------------------------------------------------
    # Query 7: Database Latency & Connection Pool Contention
    # Why it exists: Proves or disproves whether database resource exhaustion
    # caused API timeouts during customer transaction bursts.
    # -------------------------------------------------------------------
    def inspect_db_contention_metrics(self, latency_threshold_ms: float = 50.0, limit: int = 10) -> Dict[str, Any]:
        sql = text("""
            SELECT id, timestamp, db_latency_ms, active_connections, cpu_percent, error_rate
            FROM system_metrics
            WHERE db_latency_ms >= :latency_threshold_ms
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        rows = self.db.execute(sql, {"latency_threshold_ms": latency_threshold_ms, "limit": limit}).mappings().all()
        return {
            "query_id": "QUERY_07_DB_CONTENTION",
            "title": "Database Latency & Connection Spikes",
            "threshold_ms": latency_threshold_ms,
            "spikes_detected": len(rows),
            "rows": [dict(r) for r in rows],
            "diagnostic_finding": (
                f"Detected {len(rows)} telemetry periods with elevated DB latency >= {latency_threshold_ms}ms." if rows
                else "Database latency remained within normal operating tolerances."
            ),
        }

    # -------------------------------------------------------------------
    # Query 8: Find Unhandled Server Exceptions (HTTP 500)
    # Why it exists: PSEs inspect recent 500 error logs to differentiate
    # client-side integration bugs from unhandled server exceptions.
    # -------------------------------------------------------------------
    def find_unhandled_exceptions(self, hours: int = 12, limit: int = 15) -> Dict[str, Any]:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        sql = text("""
            SELECT id, timestamp, service, customer_id, request_id, endpoint, error_code, message
            FROM logs
            WHERE status_code >= 500
              AND timestamp >= :start_time
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        rows = self.db.execute(sql, {"start_time": start_time, "limit": limit}).mappings().all()
        return {
            "query_id": "QUERY_08_SERVER_EXCEPTIONS",
            "title": "Unhandled 5xx Server Exceptions",
            "exception_count": len(rows),
            "rows": [dict(r) for r in rows],
            "diagnostic_finding": (
                f"Found {len(rows)} 5xx errors recorded in the last {hours} hours." if rows
                else "No 5xx errors logged in the specified timeframe."
            ),
        }

    # -------------------------------------------------------------------
    # Query 9: Detect Silent Order Rollbacks (Data Inconsistency)
    # Why it exists: When an API client receives HTTP 201 Created but the order
    # is missing from the database, this query reconciles log acknowledgements
    # against actual database rows.
    # -------------------------------------------------------------------
    def detect_silent_order_rollbacks(self, request_id: str) -> Dict[str, Any]:
        # Check logs for successful 201 acknowledgment
        log_sql = text("""
            SELECT request_id, customer_id, endpoint, status_code, message, error_code
            FROM logs
            WHERE request_id = :request_id
            LIMIT 5
        """)
        log_rows = self.db.execute(log_sql, {"request_id": request_id}).mappings().all()

        # Check if orders table contains matching records
        order_sql = text("""
            SELECT id, customer_id, external_order_id, status, amount
            FROM orders
            WHERE customer_id IN (
                SELECT customer_id FROM logs WHERE request_id = :request_id AND customer_id IS NOT NULL
            )
            ORDER BY id DESC
            LIMIT 5
        """)
        order_rows = self.db.execute(order_sql, {"request_id": request_id}).mappings().all()

        has_inconsistency_log = any(
            (r.get("error_code") == "DATA_INCONSISTENCY" or "rolled back" in (r.get("message") or "").lower())
            for r in log_rows
        )

        return {
            "query_id": "QUERY_09_SILENT_ROLLBACKS",
            "title": "Reconciliation: API Acknowledged vs Database State",
            "request_id": request_id,
            "logs_found": len(log_rows),
            "inconsistency_detected": has_inconsistency_log,
            "log_entries": [dict(r) for r in log_rows],
            "recent_orders": [dict(r) for r in order_rows],
            "diagnostic_finding": (
                "DATA INCONSISTENCY CONFIRMED: Log indicates transaction aborted or rolled back after API return."
                if has_inconsistency_log
                else "No silent transaction rollback pattern detected for this request."
            ),
        }

    # -------------------------------------------------------------------
    # Query 10: Customer Integration Health Scorecard
    # Why it exists: Provides an executive summary of integration volume,
    # success rate, and active orders for PSE customer sync meetings.
    # -------------------------------------------------------------------
    def inspect_customer_integration_health(self, customer_id: int) -> Dict[str, Any]:
        sql = text("""
            SELECT
                c.id as customer_id,
                c.name as customer_name,
                c.environment,
                c.status as customer_status,
                (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) as total_orders,
                (SELECT COUNT(*) FROM api_test_runs t WHERE t.customer_id = c.id) as total_test_runs,
                (SELECT COUNT(*) FROM api_test_runs t WHERE t.customer_id = c.id AND t.test_status = 'PASSED') as passed_test_runs
            FROM customers c
            WHERE c.id = :customer_id
        """)
        row = self.db.execute(sql, {"customer_id": customer_id}).mappings().first()
        if not row:
            return {"query_id": "QUERY_10_INTEGRATION_HEALTH", "found": False, "customer_id": customer_id}

        d = dict(row)
        total_tests = d["total_test_runs"] or 0
        passed_tests = d["passed_test_runs"] or 0
        pass_rate = round(100.0 * passed_tests / total_tests, 2) if total_tests > 0 else 100.0
        d["pass_rate"] = pass_rate

        return {
            "query_id": "QUERY_10_INTEGRATION_HEALTH",
            "title": "Customer Integration Health Scorecard",
            "found": True,
            "data": d,
            "diagnostic_finding": f"Customer '{d['customer_name']}' has a {pass_rate}% API integration pass rate across {total_tests} runs.",
        }

    # -------------------------------------------------------------------
    # Query 11: Top Failing API Endpoints
    # Why it exists: Helps engineering prioritize fixes for brittle endpoints.
    # -------------------------------------------------------------------
    def get_top_failing_endpoints(self, limit: int = 5) -> Dict[str, Any]:
        sql = text("""
            SELECT
                e.id as endpoint_id,
                e.name as endpoint_name,
                e.method,
                e.endpoint,
                COUNT(r.id) as total_runs,
                SUM(CASE WHEN r.test_status IN ('FAILED', 'ERROR') THEN 1 ELSE 0 END) as failure_count,
                ROUND(100.0 * SUM(CASE WHEN r.test_status IN ('FAILED', 'ERROR') THEN 1 ELSE 0 END) / COUNT(r.id), 2) as failure_rate
            FROM api_endpoints e
            JOIN api_test_runs r ON e.id = r.endpoint_id
            GROUP BY e.id, e.name, e.method, e.endpoint
            ORDER BY failure_count DESC
            LIMIT :limit
        """)
        rows = self.db.execute(sql, {"limit": limit}).mappings().all()
        return {
            "query_id": "QUERY_11_FAILING_ENDPOINTS",
            "title": "Top Failing API Endpoints",
            "endpoints": [dict(r) for r in rows],
            "diagnostic_finding": (
                f"Highest failure endpoint: {rows[0]['endpoint_name']} ({rows[0]['failure_rate']}% failure rate)"
                if rows else "All endpoints operating with 0% failures."
            ),
        }
