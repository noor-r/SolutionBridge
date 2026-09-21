"""Failure Simulator for controlled integration and infrastructure fault injection.

Simulates realistic, controlled failure conditions without corrupting production baseline data.
"""

from datetime import datetime, timezone
import random
from typing import Any, Dict
from sqlalchemy.orm import Session
from app.db.models import Customer, Log, SystemMetric
from app.utils.request_id import generate_request_id
from app.core.logging import logger


class FailureSimulator:
    """Orchestrates controlled integration failure scenarios."""

    SCENARIOS = {
        "database_timeout": "Simulate database connection pool exhaustion and query timeouts",
        "database_connection_failure": "Simulate primary database node unreachable / network partition",
        "slow_sql_query": "Simulate slow query execution (4500ms) from unindexed scan or table locks",
        "invalid_authentication": "Simulate invalid / expired customer API key or signature",
        "invalid_request_payload": "Simulate 422 payload schema validation failure",
        "500_application_exception": "Simulate unhandled NullPointer / business logic exception",
        "503_service_unavailable": "Simulate downstream circuit breaker trip and worker exhaustion",
        "high_response_time": "Simulate extreme service degradation and gateway latency",
        "missing_order_record": "Simulate silent write rollback: API claims 201, but DB record missing",
        "data_inconsistency": "Simulate transaction mismatch: API returned amount differs from DB",
        "high_cpu_memory": "Simulate container OOM / runaway loop (98% CPU, 95% RAM)",
        "webhook_failure": "Simulate customer webhook notification delivery timeout and retry failure",
    }

    def __init__(self, db: Session):
        self.db = db

    def trigger_scenario(self, scenario: str, customer_id: int = 1) -> Dict[str, Any]:
        """Execute a controlled failure scenario and record relevant logs and metrics."""
        scenario = scenario.lower().strip()
        req_id = generate_request_id()
        now = datetime.now(timezone.utc)

        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        customer_name = customer.name if customer else "Demo Customer"

        if scenario == "database_timeout":
            # 1. Log DB timeout
            log_entry = Log(
                timestamp=now,
                level="ERROR",
                service="order-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=500,
                error_code="DB_TIMEOUT",
                response_time_ms=4820.0,
                message="Database connection pool timeout: could not acquire pool connection within 5000ms",
                metadata_json='{"db_cluster": "aurora-mysql-primary", "pool_active": 100, "pool_max": 100}',
            )
            # 2. Metric spike in DB latency & active connections
            metric = SystemMetric(
                timestamp=now,
                cpu_percent=42.0,
                memory_percent=55.0,
                db_latency_ms=280.0,  # High DB latency
                active_connections=98,  # Pool near limit
                request_rate=210.0,
                error_rate=12.5,
            )
            self.db.add(log_entry)
            self.db.add(metric)
            self.db.commit()

            return {
                "status": "simulated_failure",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 500,
                "error_code": "DB_TIMEOUT",
                "message": f"Simulated Database Timeout on order placement for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {
                    "expected_category": "Database",
                    "observed_db_latency_ms": 280.0,
                    "active_connections": 98,
                    "order_persisted": False,
                },
            }

        elif scenario == "database_connection_failure":
            log_entry = Log(
                timestamp=now,
                level="CRITICAL",
                service="database-proxy",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=500,
                error_code="DB_CONN_ERR",
                response_time_ms=5010.0,
                message="Can't connect to MySQL server on 'aurora-primary:3306' (Target machine refused connection)",
                metadata_json='{"host": "aurora-primary", "port": 3306, "state": "CONN_REFUSED"}',
            )
            metric = SystemMetric(
                timestamp=now,
                cpu_percent=30.0,
                memory_percent=50.0,
                db_latency_ms=999.0,
                active_connections=0,
                request_rate=180.0,
                error_rate=25.0,
            )
            self.db.add(log_entry)
            self.db.add(metric)
            self.db.commit()

            return {
                "status": "simulated_failure",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 500,
                "error_code": "DB_CONN_ERR",
                "message": f"Simulated Database Connection Failure for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Database", "db_available": False},
            }

        elif scenario == "slow_sql_query":
            log_entry = Log(
                timestamp=now,
                level="WARNING",
                service="order-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="GET /api/v1/customers/{customer_id}/orders",
                status_code=200,
                error_code="SLOW_SQL_QUERY",
                response_time_ms=4550.0,
                message="Query execution exceeded 4000ms threshold: full table scan on unindexed column external_order_id",
                metadata_json='{"rows_examined": 150000, "query_time_s": 4.55}',
            )
            metric = SystemMetric(
                timestamp=now,
                cpu_percent=65.0,
                memory_percent=60.0,
                db_latency_ms=195.0,
                active_connections=65,
                request_rate=190.0,
                error_rate=0.5,
            )
            self.db.add(log_entry)
            self.db.add(metric)
            self.db.commit()

            return {
                "status": "simulated_degradation",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 200,
                "error_code": "SLOW_SQL_QUERY",
                "message": f"Simulated Slow SQL Query on order retrieval for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Performance", "response_time_ms": 4550.0},
            }

        elif scenario == "invalid_authentication":
            log_entry = Log(
                timestamp=now,
                level="ERROR",
                service="auth-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=401,
                error_code="AUTH_INVALID",
                response_time_ms=18.0,
                message="Authentication failed: invalid or tampered API key hash provided in X-API-Key header",
                metadata_json='{"header_present": true, "key_prefix": "sb_live_***", "reason": "HASH_MISMATCH"}',
            )
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "simulated_failure",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 401,
                "error_code": "AUTH_INVALID",
                "message": f"Simulated 401 Unauthorized API key rejection for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Authentication", "auth_passed": False},
            }

        elif scenario == "invalid_request_payload":
            log_entry = Log(
                timestamp=now,
                level="WARNING",
                service="gateway-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=422,
                error_code="VALIDATION_FAILED",
                response_time_ms=25.0,
                message="Request payload failed Pydantic schema validation: 'amount' must be greater than 0, got -50.00",
                metadata_json='{"field": "amount", "constraint": "gt_0"}',
            )
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "simulated_failure",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 422,
                "error_code": "VALIDATION_FAILED",
                "message": f"Simulated 422 Unprocessable Entity payload schema error for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Integration", "field_in_error": "amount"},
            }

        elif scenario == "500_application_exception":
            log_entry = Log(
                timestamp=now,
                level="ERROR",
                service="order-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=500,
                error_code="INTERNAL_EXCEPTION",
                response_time_ms=110.0,
                message="Unhandled NullPointerException in PricingCalculationEngine.applyDiscounts(): object reference not set to an instance",
                metadata_json='{"module": "pricing_engine", "line": 142}',
            )
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "simulated_failure",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 500,
                "error_code": "INTERNAL_EXCEPTION",
                "message": f"Simulated Unhandled Application 500 Exception for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Application", "stack_trace_captured": True},
            }

        elif scenario == "503_service_unavailable":
            log_entry = Log(
                timestamp=now,
                level="ERROR",
                service="gateway-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=503,
                error_code="SERVICE_UNAVAILABLE",
                response_time_ms=520.0,
                message="Circuit breaker 'order-service-breaker' tripped: 50% failure rate threshold exceeded; downstream unavailable",
                metadata_json='{"breaker_state": "OPEN", "consecutive_failures": 15}',
            )
            metric = SystemMetric(
                timestamp=now,
                cpu_percent=94.0,
                memory_percent=88.0,
                db_latency_ms=15.0,
                active_connections=35,
                request_rate=850.0,
                error_rate=45.0,
            )
            self.db.add(log_entry)
            self.db.add(metric)
            self.db.commit()

            return {
                "status": "simulated_failure",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 503,
                "error_code": "SERVICE_UNAVAILABLE",
                "message": f"Simulated 503 Service Unavailable / Circuit Breaker Trip for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Infrastructure", "circuit_breaker": "OPEN"},
            }

        elif scenario == "high_response_time":
            log_entry = Log(
                timestamp=now,
                level="WARNING",
                service="gateway-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=200,
                error_code="HIGH_LATENCY",
                response_time_ms=3950.0,
                message="Gateway SLA violated: upstream processing took 3950ms (max expected: 500ms)",
                metadata_json='{"sla_target_ms": 500, "actual_ms": 3950}',
            )
            metric = SystemMetric(
                timestamp=now,
                cpu_percent=78.0,
                memory_percent=72.0,
                db_latency_ms=120.0,
                active_connections=80,
                request_rate=450.0,
                error_rate=2.0,
            )
            self.db.add(log_entry)
            self.db.add(metric)
            self.db.commit()

            return {
                "status": "simulated_degradation",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 200,
                "error_code": "HIGH_LATENCY",
                "message": f"Simulated High Response Time (3950ms) SLA breach for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Performance", "response_time_ms": 3950.0},
            }

        elif scenario == "missing_order_record":
            # Silent rollback / Data inconsistency
            log_entry = Log(
                timestamp=now,
                level="ERROR",
                service="order-service",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=201,  # API returned 201 to customer!
                error_code="DATA_INCONSISTENCY",
                response_time_ms=90.0,
                message="Order write failed to commit; transaction aborted after 201 response sent to client",
                metadata_json='{"external_order_id": "ORD-GHOST-999", "persisted": false}',
            )
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "simulated_inconsistency",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 201,
                "error_code": "DATA_INCONSISTENCY",
                "message": f"Simulated Missing Order Record (API returned 201, DB has 0 rows) for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {
                    "expected_category": "Data Consistency",
                    "api_status_returned": 201,
                    "db_row_exists": False,
                },
            }

        elif scenario == "data_inconsistency":
            log_entry = Log(
                timestamp=now,
                level="ERROR",
                service="reconciliation-worker",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /api/v1/orders",
                status_code=200,
                error_code="DATA_INCONSISTENCY",
                response_time_ms=80.0,
                message="Audit mismatch: API acknowledged total $999.00 but database ledger recorded $0.00",
                metadata_json='{"api_amount": 999.00, "db_amount": 0.00, "discrepancy": 999.00}',
            )
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "simulated_inconsistency",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 200,
                "error_code": "DATA_INCONSISTENCY",
                "message": f"Simulated Ledger Amount Mismatch ($999.00 vs $0.00) for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Data Consistency"},
            }

        elif scenario == "high_cpu_memory":
            metric = SystemMetric(
                timestamp=now,
                cpu_percent=98.5,
                memory_percent=96.2,
                db_latency_ms=45.0,
                active_connections=75,
                request_rate=1200.0,
                error_rate=18.5,
            )
            log_entry = Log(
                timestamp=now,
                level="CRITICAL",
                service="infrastructure-monitor",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="/health",
                status_code=503,
                error_code="RESOURCE_EXHAUSTION",
                response_time_ms=1800.0,
                message="Resource limit exceeded: CPU at 98.5%, RAM at 96.2%; kernel throttling active",
                metadata_json='{"cpu_percent": 98.5, "memory_percent": 96.2}',
            )
            self.db.add(metric)
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "simulated_exhaustion",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 503,
                "error_code": "RESOURCE_EXHAUSTION",
                "message": f"Simulated Critical Resource Exhaustion (98.5% CPU, 96.2% RAM) for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Infrastructure", "cpu_percent": 98.5, "memory_percent": 96.2},
            }

        elif scenario == "webhook_failure":
            log_entry = Log(
                timestamp=now,
                level="ERROR",
                service="webhook-dispatcher",
                customer_id=customer_id,
                request_id=req_id,
                endpoint="POST /webhooks/orders",
                status_code=504,
                error_code="WEBHOOK_TIMEOUT",
                response_time_ms=10000.0,
                message="Customer webhook endpoint 'https://api.customer.com/webhooks' timed out after 10000ms; max retries (3) exhausted",
                metadata_json='{"webhook_url": "https://api.customer.com/webhooks", "retries": 3}',
            )
            self.db.add(log_entry)
            self.db.commit()

            return {
                "status": "simulated_failure",
                "scenario": scenario,
                "customer_id": customer_id,
                "request_id": req_id,
                "http_status": 504,
                "error_code": "WEBHOOK_TIMEOUT",
                "message": f"Simulated Webhook Delivery Failure for {customer_name}",
                "investigation_url": f"/api/v1/incidents/analyze/{req_id}",
                "details": {"expected_category": "Integration", "webhook_url": "https://api.customer.com/webhooks"},
            }

        else:
            raise ValueError(f"Unknown scenario '{scenario}'. Supported: {list(self.SCENARIOS.keys())}")
