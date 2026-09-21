"""System metrics and telemetry routes."""

from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import SystemMetric
from app.db.schemas import SystemMetricResponse

router = APIRouter(prefix="/api/v1/metrics", tags=["Metrics"])


@router.get("", response_model=List[SystemMetricResponse])
def get_metrics(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve recent system metric observations."""
    return (
        db.query(SystemMetric)
        .order_by(SystemMetric.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.get("/latest", response_model=SystemMetricResponse)
def get_latest_metric(db: Session = Depends(get_db)):
    """Retrieve the most recent telemetry observation."""
    latest = (
        db.query(SystemMetric)
        .order_by(SystemMetric.timestamp.desc())
        .first()
    )
    if not latest:
        # Return fallback dummy if table empty
        return SystemMetricResponse(
            id=0,
            timestamp=datetime.now(),
            cpu_percent=25.0,
            memory_percent=45.0,
            db_latency_ms=5.0,
            active_connections=20,
            request_rate=120.0,
            error_rate=0.2,
        )
    return latest
