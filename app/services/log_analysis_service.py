"""Structured Log Analysis and Multi-Service Timeline Correlation Service."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.db.models import Log


class LogAnalysisService:
    """Forensic log analysis engine that correlates events by request ID and customer ID."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_logs(self, request_id: str) -> Dict[str, Any]:
        """Analyze chronological log records for a given request ID."""
        logs = (
            self.db.query(Log)
            .filter(Log.request_id == request_id)
            .order_by(Log.timestamp.asc())
            .all()
        )

        if not logs:
            return {
                "request_id": request_id,
                "found": False,
                "message": f"No logs found matching request_id '{request_id}'",
                "timeline": [],
                "detected_errors": [],
                "severity": "UNKNOWN",
                "services_involved": [],
                "endpoints_involved": [],
                "max_latency_ms": 0.0,
                "error_codes": [],
            }

        timeline: List[Dict[str, Any]] = []
        detected_errors: List[Dict[str, Any]] = []
        services_involved = set()
        endpoints_involved = set()
        error_codes = set()
        max_latency_ms = 0.0
        customer_id: Optional[int] = None

        has_critical = False
        has_error = False
        has_warning = False

        for log in logs:
            if log.customer_id is not None:
                customer_id = log.customer_id
            if log.service:
                services_involved.add(log.service)
            if log.endpoint:
                endpoints_involved.add(log.endpoint)
            if log.error_code:
                error_codes.add(log.error_code)
            if log.response_time_ms and log.response_time_ms > max_latency_ms:
                max_latency_ms = log.response_time_ms

            if log.level == "CRITICAL":
                has_critical = True
            elif log.level == "ERROR":
                has_error = True
            elif log.level == "WARNING":
                has_warning = True

            entry = {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "service": log.service,
                "endpoint": log.endpoint,
                "status_code": log.status_code,
                "error_code": log.error_code,
                "response_time_ms": log.response_time_ms,
                "message": log.message,
                "metadata_json": log.metadata_json,
            }
            timeline.append(entry)

            # Error detection: by level OR 4xx/5xx HTTP status OR error_code
            if log.level in ("ERROR", "CRITICAL") or (log.status_code and log.status_code >= 400) or log.error_code:
                detected_errors.append(entry)

        # Severity determination
        if has_critical:
            severity = "CRITICAL"
        elif has_error:
            severity = "HIGH"
        elif has_warning or max_latency_ms > 2000.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        return {
            "request_id": request_id,
            "customer_id": customer_id,
            "found": True,
            "log_count": len(logs),
            "severity": severity,
            "services_involved": sorted(list(services_involved)),
            "endpoints_involved": sorted(list(endpoints_involved)),
            "error_codes": sorted(list(error_codes)),
            "max_latency_ms": round(max_latency_ms, 2),
            "detected_errors": detected_errors,
            "timeline": timeline,
            "primary_service": list(services_involved)[0] if services_involved else "unknown",
            "primary_endpoint": list(endpoints_involved)[0] if endpoints_involved else "unknown",
        }
