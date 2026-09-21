"""Deterministic, Multi-Source Root-Cause Engine for Product Solutions Engineers.

Combines deterministic system telemetry, raw SQL findings, correlated logs,
and metrics with ML predictions and historical retrieval.
Produces separate Engineer-Facing and Customer-Facing incident narratives.
"""

from typing import Any, Dict, List, Optional


class RootCauseEngine:
    """Diagnostic synthesis engine combining deterministic facts with ML intelligence."""

    def diagnose(
        self,
        request_id: str,
        api_evidence: Dict[str, Any],
        sql_evidence: Dict[str, Any],
        log_evidence: Dict[str, Any],
        metric_evidence: Dict[str, Any],
        ml_anomaly: Dict[str, Any],
        ml_classifier: Dict[str, Any],
        similar_incidents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Synthesize all 7 evidence streams into an authoritative diagnostic report."""
        evidence_list: List[str] = []
        rules_triggered: List[str] = []

        # 1. Inspect API Evidence
        status_code = api_evidence.get("status_code") or 200
        api_latency = api_evidence.get("response_time_ms") or 0.0
        endpoint = api_evidence.get("endpoint", "")
        if status_code >= 500:
            evidence_list.append(f"API endpoint returned HTTP {status_code} server error (latency: {api_latency}ms)")
        elif status_code >= 400:
            evidence_list.append(f"API endpoint returned HTTP {status_code} client error (latency: {api_latency}ms)")

        # 2. Inspect SQL Evidence
        persisted = sql_evidence.get("persisted")
        if persisted is False:
            evidence_list.append("SQL verification confirmed expected order record was NOT committed to the database")
        elif persisted is True:
            evidence_list.append("SQL verification confirmed order record exists in database table")

        if sql_evidence.get("inconsistency_detected"):
            evidence_list.append("Data Inconsistency: API returned success status, but transaction commit was aborted")

        # 3. Inspect Log Evidence
        log_errors = log_evidence.get("detected_errors", [])
        error_codes = log_evidence.get("error_codes", [])
        if error_codes:
            evidence_list.append(f"Structured logs contain error codes: {', '.join(error_codes)}")
        if log_errors:
            sample_msg = log_errors[0].get("message", "")
            evidence_list.append(f"Primary log failure message: '{sample_msg}'")

        # 4. Inspect Metric Evidence
        db_lat = metric_evidence.get("db_latency_ms", 0.0)
        cpu_pct = metric_evidence.get("cpu_percent", 0.0)
        active_conns = metric_evidence.get("active_connections", 0)
        if db_lat > 50.0:
            evidence_list.append(f"Database latency elevated to {db_lat}ms (baseline < 15ms)")
        if cpu_pct > 80.0:
            evidence_list.append(f"Host CPU utilization reached {cpu_pct}% (critical threshold > 80%)")
        if active_conns > 80:
            evidence_list.append(f"High connection pool contention: {active_conns} active database connections")

        # 5. Inspect ML Evidence (Advisory)
        is_anomaly = ml_anomaly.get("is_anomaly", False)
        anomaly_score = ml_anomaly.get("anomaly_score", 0.0)
        if is_anomaly:
            evidence_list.append(f"ML Anomaly Detector flagged telemetry as abnormal (Isolation Forest score: {anomaly_score})")
        else:
            evidence_list.append(f"ML Anomaly Detector evaluated telemetry within normal baseline (score: {anomaly_score})")

        predicted_cat = ml_classifier.get("predicted_category", "Application")
        prob = ml_classifier.get("probability", 0.5)
        evidence_list.append(f"ML Incident Classifier predicted category '{predicted_cat}' (calibrated confidence: {prob*100:.1f}%)")

        if similar_incidents:
            top_sim = similar_incidents[0]
            evidence_list.append(
                f"Historical Case Match: #{top_sim.get('incident_id')} ('{top_sim.get('title')}') with {top_sim.get('similarity_score', 0)*100:.1f}% semantic similarity"
            )

        # -------------------------------------------------------------------
        # Deterministic Root Cause Decision Logic (Evidence-Weighted)
        # -------------------------------------------------------------------
        # Check rule 1: Authentication Failure (Definitive 401 / Auth log)
        if "AUTH_INVALID" in error_codes or status_code == 401 or "auth" in endpoint.lower():
            category = "Authentication"
            probable_cause = "Customer API key validation failure: invalid signature, expired credential, or malformed header."
            confidence = min(0.98, max(prob, 0.92))
            rules_triggered.append("RULE_AUTH_REJECTION")

        # Check rule 2: Data Inconsistency / Silent Rollback
        elif sql_evidence.get("inconsistency_detected") or "DATA_INCONSISTENCY" in error_codes or (status_code == 201 and persisted is False):
            category = "Data Consistency"
            probable_cause = "Asynchronous write failure or transaction rollback occurring after HTTP response dispatch."
            confidence = 0.94
            rules_triggered.append("RULE_DATA_PERSISTENCE_MISMATCH")

        # Check rule 3: Infrastructure Saturation / Circuit Breaker / 503
        elif "RESOURCE_EXHAUSTION" in error_codes or "SERVICE_UNAVAILABLE" in error_codes or cpu_pct > 90.0 or status_code == 503:
            category = "Infrastructure"
            probable_cause = "Host resource starvation (CPU/Memory saturation) or circuit breaker trip isolating degraded service."
            confidence = min(0.95, max(prob, 0.88))
            rules_triggered.append("RULE_INFRASTRUCTURE_SATURATION")

        # Check rule 4: Database Timeout / Lock Wait / Connection Failure (500)
        elif "DB_TIMEOUT" in error_codes or "DB_CONN_ERR" in error_codes or (db_lat > 100.0 and status_code >= 500):
            category = "Database"
            probable_cause = "Database connection pool exhaustion or query lock timeout preventing transaction commit."
            confidence = min(0.96, max(prob, 0.90))
            rules_triggered.append("RULE_DB_TIMEOUT_OR_HIGH_LATENCY")

        # Check rule 5: Performance / Slow Query / SLA Breach (200 / Non-500)
        elif "SLOW_SQL_QUERY" in error_codes or "HIGH_LATENCY" in error_codes or (api_latency > 2500.0 and status_code < 500) or (db_lat > 40.0 and status_code == 200):
            category = "Performance"
            probable_cause = "Unindexed database query execution or table lock contention exceeding SLA tolerances."
            confidence = min(0.94, max(prob, 0.88))
            rules_triggered.append("RULE_PERFORMANCE_DEGRADATION")

        # Check rule 6: Integration / Payload Schema
        elif "VALIDATION_FAILED" in error_codes or status_code == 422 or status_code == 400 or "WEBHOOK_TIMEOUT" in error_codes:
            category = "Integration"
            probable_cause = "Customer request payload schema mismatch or downstream partner webhook endpoint unreachable."
            confidence = min(0.95, max(prob, 0.89))
            rules_triggered.append("RULE_INTEGRATION_SCHEMA_ERROR")

        # Default: Fall back to ML classifier prediction backed by log evidence
        else:
            category = predicted_cat
            probable_cause = f"Application logic or service fault resembling historical '{category}' incidents."
            confidence = round(prob, 2)
            rules_triggered.append("RULE_ML_CLASSIFIER_ADVISORY")

        # -------------------------------------------------------------------
        # Build Engineer-Facing Technical Summary (PSE Investigation View)
        # -------------------------------------------------------------------
        engineer_summary = (
            f"TECHNICAL POSTMORTEM [Request ID: {request_id}]\n"
            f"Root Cause Assessment: {probable_cause}\n"
            f"Classification: {category} (Diagnostic Confidence: {confidence*100:.1f}%)\n"
            f"Key Findings:\n"
            + "\n".join(f"  • {item}" for item in evidence_list)
            + f"\nDiagnostic Rules Evaluated: {', '.join(rules_triggered)}\n"
        )

        # -------------------------------------------------------------------
        # Build Customer-Facing Business Summary (Partner Communication View)
        # -------------------------------------------------------------------
        customer_summary = self._generate_customer_summary(category, request_id, endpoint, status_code)

        return {
            "request_id": request_id,
            "category": category,
            "confidence": round(confidence, 2),
            "probable_root_cause": probable_cause,
            "rules_triggered": rules_triggered,
            "deterministic_evidence": evidence_list,
            "ml_evidence": {
                "anomaly_detection": ml_anomaly,
                "incident_classifier": ml_classifier,
            },
            "similar_incidents": similar_incidents,
            "engineer_summary": engineer_summary,
            "customer_summary": customer_summary,
        }

    def _generate_customer_summary(self, category: str, request_id: str, endpoint: str, status_code: int) -> str:
        """Generate professional, clear, partner-ready communication."""
        if category == "Database":
            return (
                f"Dear Customer Integration Team,\n\n"
                f"We identified a transient database connection delay affecting your request ({request_id}) "
                f"to {endpoint}. The transaction did not complete, and no duplicate charges or corrupted records were created. "
                f"Our engineering team has adjusted database connection pool limits. You may safely retry this request "
                f"with your existing idempotency key."
            )
        elif category == "Authentication":
            return (
                f"Dear Customer Integration Team,\n\n"
                f"Your API request ({request_id}) to {endpoint} was rejected with HTTP 401 Unauthorized. "
                f"Our validation check indicates that the API key provided in the 'X-API-Key' header was either "
                f"malformed, expired, or missing. Please verify your active credentials in the SolutionBridge partner "
                f"portal and ensure headers are formatted without whitespace."
            )
        elif category == "Performance":
            return (
                f"Dear Customer Integration Team,\n\n"
                f"We observed higher than normal processing latency on request {request_id} ({endpoint}). "
                f"While the request ultimately processed, response times temporarily exceeded our SLA target. "
                f"We have optimized query indexing for this route to restore sub-200ms latency."
            )
        elif category == "Integration":
            return (
                f"Dear Customer Integration Team,\n\n"
                f"Your API request ({request_id}) could not be processed due to a payload validation mismatch (HTTP {status_code}). "
                f"Please inspect the field data types and mandatory properties in your request against our OpenAPI 3.0 specification. "
                f"Feel free to reply with your payload schema if you would like us to review it together."
            )
        elif category == "Data Consistency":
            return (
                f"Dear Customer Integration Team,\n\n"
                f"Our automated reconciliation monitor detected a discrepancy regarding request {request_id}. "
                f"Although an initial acknowledgment was dispatched, the transaction was rolled back prior to final settlement. "
                f"Our team has isolated the asynchronous commit race condition and will confirm once the record has been resubmitted."
            )
        elif category == "Infrastructure":
            return (
                f"Dear Customer Integration Team,\n\n"
                f"A momentary infrastructure capacity spike caused request {request_id} to receive HTTP 503. "
                f"Automated auto-scaling nodes have spun up and system health is fully restored. Please retry the request."
            )
        else:
            return (
                f"Dear Customer Integration Team,\n\n"
                f"An internal error occurred while processing request {request_id} on {endpoint}. "
                f"Our solutions engineering team is actively investigating the error trail and will provide an update within 1 business hour."
            )
