"""System Metrics telemetry extraction and feature mapping."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.db.models import SystemMetric


class MetricsService:
    """Service to query, correlate, and assemble system telemetry vectors."""

    def __init__(self, db: Session):
        self.db = db

    def get_metrics_near_timestamp(
        self,
        target_time: datetime,
        window_minutes: int = 15,
    ) -> List[Dict[str, Any]]:
        """Retrieve metric observations surrounding an incident event timestamp."""
        start = target_time - timedelta(minutes=window_minutes)
        end = target_time + timedelta(minutes=window_minutes)

        metrics = (
            self.db.query(SystemMetric)
            .filter(SystemMetric.timestamp >= start, SystemMetric.timestamp <= end)
            .order_by(SystemMetric.timestamp.asc())
            .all()
        )

        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "db_latency_ms": m.db_latency_ms,
                "active_connections": m.active_connections,
                "request_rate": m.request_rate,
                "error_rate": m.error_rate,
            }
            for m in metrics
        ]

    def get_latest_feature_vector(self, latency_override: Optional[float] = None) -> Dict[str, float]:
        """Extract latest feature dictionary for ML anomaly detection."""
        latest = (
            self.db.query(SystemMetric)
            .order_by(SystemMetric.timestamp.desc())
            .first()
        )

        if latest:
            return {
                "response_time_ms": float(latency_override if latency_override is not None else 120.0),
                "db_latency_ms": float(latest.db_latency_ms),
                "cpu_percent": float(latest.cpu_percent),
                "memory_percent": float(latest.memory_percent),
                "request_rate": float(latest.request_rate),
                "error_rate": float(latest.error_rate),
                "active_connections": float(latest.active_connections),
            }

        # Fallback baseline
        return {
            "response_time_ms": float(latency_override if latency_override is not None else 85.0),
            "db_latency_ms": 6.5,
            "cpu_percent": 30.0,
            "memory_percent": 45.0,
            "request_rate": 150.0,
            "error_rate": 0.5,
            "active_connections": 25.0,
        }
