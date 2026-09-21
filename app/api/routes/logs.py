"""Log exploration routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Log
from app.db.schemas import LogResponse

router = APIRouter(prefix="/api/v1/logs", tags=["Logs"])


@router.get("", response_model=List[LogResponse])
def get_logs(
    customer_id: Optional[int] = None,
    level: Optional[str] = None,
    service: Optional[str] = None,
    request_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Query structured application logs with multi-field filtering."""
    query = db.query(Log)
    if customer_id:
        query = query.filter(Log.customer_id == customer_id)
    if level:
        query = query.filter(Log.level == level.upper())
    if service:
        query = query.filter(Log.service == service)
    if request_id:
        query = query.filter(Log.request_id == request_id)

    return query.order_by(Log.timestamp.desc()).limit(limit).all()


@router.get("/{request_id}", response_model=List[LogResponse])
def get_logs_by_request(request_id: str, db: Session = Depends(get_db)):
    """Retrieve chronologically correlated log trail for a specific request ID."""
    logs = (
        db.query(Log)
        .filter(Log.request_id == request_id)
        .order_by(Log.timestamp.asc())
        .all()
    )
    if not logs:
        raise HTTPException(
            status_code=404,
            detail=f"No logs found for request ID '{request_id}'",
        )
    return logs
