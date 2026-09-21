"""API Testing endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.db.models import ApiTestRun
from app.db.schemas import ApiTestRunResponse, ApiTestSummary
from app.services.api_testing_service import ApiTestingService

router = APIRouter(prefix="/api/v1/tests", tags=["API Testing"])


@router.post("/run")
def run_api_tests(customer_id: int = Query(1), db: Session = Depends(get_db)):
    """Execute live integration test suite against registered product endpoints."""
    service = ApiTestingService(db)
    return service.run_all_tests(customer_id=customer_id)


@router.get("/results", response_model=List[ApiTestRunResponse])
def get_test_results(
    customer_id: Optional[int] = None,
    test_status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve historical test execution records."""
    query = db.query(ApiTestRun)
    if customer_id:
        query = query.filter(ApiTestRun.customer_id == customer_id)
    if test_status:
        query = query.filter(ApiTestRun.test_status == test_status.upper())

    return query.order_by(ApiTestRun.created_at.desc()).limit(limit).all()


@router.get("/summary", response_model=ApiTestSummary)
def get_test_summary(db: Session = Depends(get_db)):
    """Calculate aggregate API test health metrics across all runs."""
    total = db.query(func.count(ApiTestRun.id)).scalar() or 0
    passed = db.query(func.count(ApiTestRun.id)).filter(ApiTestRun.test_status == "PASSED").scalar() or 0
    failed = db.query(func.count(ApiTestRun.id)).filter(ApiTestRun.test_status == "FAILED").scalar() or 0
    errors = db.query(func.count(ApiTestRun.id)).filter(ApiTestRun.test_status == "ERROR").scalar() or 0
    avg_latency = db.query(func.avg(ApiTestRun.response_time_ms)).scalar() or 0.0

    pass_rate = round(100.0 * passed / total, 2) if total > 0 else 100.0

    return ApiTestSummary(
        total_tests=total,
        passed_tests=passed,
        failed_tests=failed,
        error_tests=errors,
        pass_rate=pass_rate,
        avg_response_time_ms=round(float(avg_latency), 2),
    )
