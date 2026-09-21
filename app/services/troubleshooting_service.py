"""Troubleshooting Engine and Remediation Knowledge Base."""

from typing import Any, Dict, List


class TroubleshootingService:
    """Expert system producing prioritized, evidence-based troubleshooting actions."""

    ACTIONS_KB = {
        "Database": [
            {
                "priority": 1,
                "action": "Inspect Database Connection Pool Saturation",
                "rationale": "High active connection counts lead to thread queue starvation and socket timeouts on customer order inserts.",
                "verification_step": "Run SQL query to inspect active connections: SELECT active_connections, db_latency_ms FROM system_metrics ORDER BY timestamp DESC LIMIT 5.",
            },
            {
                "priority": 2,
                "action": "Review Long-Running Queries and Table Locks",
                "rationale": "Unindexed table scans create shared read locks that block concurrent order INSERT transactions.",
                "verification_step": "Inspect MySQL slow query log or run SHOW PROCESSLIST to identify queries running longer than 1000ms.",
            },
            {
                "priority": 3,
                "action": "Verify Database Cluster Availability and Failover Health",
                "rationale": "Ensure the primary writer instance has not failed over or suffered an IOPS throttle.",
                "verification_step": "Check RDS/Aurora cluster status and verify writer endpoint connectivity.",
            },
        ],
        "Authentication": [
            {
                "priority": 1,
                "action": "Verify Customer API Key Validity and Status in Portal",
                "rationale": "Customer may be transmitting an inactive, revoked, or sandbox key in production.",
                "verification_step": "Check customer status in customers table: SELECT id, name, environment, status FROM customers WHERE id = :customer_id.",
            },
            {
                "priority": 2,
                "action": "Inspect HTTP Authorization Header Formatting",
                "rationale": "Customer client may be appending whitespace, omitting the header, or mislabeling 'Bearer' instead of 'X-API-Key'.",
                "verification_step": "Inspect inbound gateway headers in structured logs for malformed header encoding.",
            },
            {
                "priority": 3,
                "action": "Verify Clock Drift on Customer Request Signatures",
                "rationale": "If HMAC request signing is enabled, client-server clock drift > 300s causes automatic authentication rejection.",
                "verification_step": "Compare customer Date/Timestamp header against UTC server clock.",
            },
        ],
        "Performance": [
            {
                "priority": 1,
                "action": "Inspect API vs Database Latency Breakdown",
                "rationale": "Identify whether latency originates in downstream database execution or gateway payload serialization.",
                "verification_step": "Execute Query 03: inspect_endpoint_latency_stats to check average and max response times.",
            },
            {
                "priority": 2,
                "action": "Examine Database B-Tree Index Utilization",
                "rationale": "Missing index on (customer_id, external_order_id) forces expensive O(N) sequential table scans.",
                "verification_step": "Run EXPLAIN on the problematic order query to confirm index seek rather than full table scan.",
            },
            {
                "priority": 3,
                "action": "Inspect Traffic Volume and Concurrency Spike",
                "rationale": "Sudden customer burst traffic may overwhelm available worker thread pools.",
                "verification_step": "Check request_rate and active_connections in system_metrics for sudden 3x+ spikes.",
            },
        ],
        "Infrastructure": [
            {
                "priority": 1,
                "action": "Inspect Container CPU and Memory Utilization",
                "rationale": "Processes approaching container cgroup memory limits are subject to kernel OOM kills and latency degradation.",
                "verification_step": "Review Query 07 & metrics telemetry to verify if cpu_percent or memory_percent > 85%.",
            },
            {
                "priority": 2,
                "action": "Verify Gateway Circuit Breaker Status",
                "rationale": "Circuit breakers trip to protect cascading system failure if downstream error rates exceed 50%.",
                "verification_step": "Check gateway error logs for 'breaker_state': 'OPEN' or consecutive 503 responses.",
            },
            {
                "priority": 3,
                "action": "Verify Downstream Microservice Health Probes",
                "rationale": "Ensure order-service, inventory-service, and auth-service endpoints are returning 200 on /health and /ready.",
                "verification_step": "Execute GET /health and GET /ready probes across all cluster pods.",
            },
        ],
        "Integration": [
            {
                "priority": 1,
                "action": "Validate Inbound JSON Request Schema Against OpenAPI Spec",
                "rationale": "Customer payload may be missing required fields, using incorrect JSON keys, or passing invalid data types.",
                "verification_step": "Review gateway log entry error_code 'VALIDATION_FAILED' to identify the exact field failing validation.",
            },
            {
                "priority": 2,
                "action": "Verify Customer Webhook Endpoint Reachability and Response Time",
                "rationale": "If webhook notifications fail, customer integration pipelines may stall waiting for order confirmation.",
                "verification_step": "Check logs for 'WEBHOOK_TIMEOUT' and test customer webhook URL with curl or Postman.",
            },
            {
                "priority": 3,
                "action": "Provide Customer with Tested Postman Collection and cURL Samples",
                "rationale": "Accelerates customer self-service resolution with known-working request templates.",
                "verification_step": "Export SolutionBridge.postman_collection.json and provide customer-specific documentation.",
            },
        ],
        "Data Consistency": [
            {
                "priority": 1,
                "action": "Reconcile API Response Against Underlying Database Table",
                "rationale": "Confirm whether the transaction successfully wrote to the orders table or was aborted post-response.",
                "verification_step": "Execute Query 01: validate_order_persistence(customer_id, external_order_id).",
            },
            {
                "priority": 2,
                "action": "Inspect Asynchronous Write Handler and Event Queue",
                "rationale": "Event race condition may cause the HTTP response to return before database transaction commit finishes.",
                "verification_step": "Search structured logs for 'DATA_INCONSISTENCY' or aborted transaction messages.",
            },
            {
                "priority": 3,
                "action": "Re-submit or Backfill Missing Order Records",
                "rationale": "Safely replay uncommitted transactions without creating duplicate charges.",
                "verification_step": "Verify idempotency keys and trigger manual order ingest worker replay.",
            },
        ],
        "Application": [
            {
                "priority": 1,
                "action": "Inspect Application Stack Trace in Structured Logs",
                "rationale": "Unhandled exceptions reveal null pointers, type errors, or unhandled edge cases in business logic.",
                "verification_step": "Execute Query 08: find_unhandled_exceptions to extract exact exception class and stack line.",
            },
            {
                "priority": 2,
                "action": "Validate Edge-Case Input Conditions in Staging",
                "rationale": "Reproduce the customer's specific payload attributes in a controlled test environment.",
                "verification_step": "Run automated test case with customer's input payload against local staging server.",
            },
        ],
    }

    def get_recommendations(
        self,
        category: str,
        evidence_list: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve structured troubleshooting actions tailored to the diagnosed category."""
        actions = self.ACTIONS_KB.get(category, self.ACTIONS_KB["Application"])
        evidence_summary = "; ".join(evidence_list[:3]) if evidence_list else "Diagnostic observations"

        enriched_actions = []
        for act in actions:
            enriched_actions.append({
                "priority": act["priority"],
                "action": act["action"],
                "rationale": act["rationale"],
                "verification_step": act["verification_step"],
                "supporting_evidence": evidence_summary,
            })

        return enriched_actions
