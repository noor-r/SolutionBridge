"""Order processing routes."""

import time
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Customer, Order, Log
from app.db.schemas import OrderCreate, OrderResponse
from app.api.dependencies import get_current_customer
from app.utils.request_id import get_current_request_id
from app.core.logging import logger

router = APIRouter(prefix="/api/v1", tags=["Orders"])


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure"),
    db: Session = Depends(get_db),
    customer: Optional[Customer] = Depends(get_current_customer),
):
    """
    Process incoming customer order request.
    Supports integration failure simulation headers:
    - database_timeout
    - slow_sql_query
    - 500_application_exception
    - missing_order_record (silent rollback)
    """
    req_id = get_current_request_id()
    effective_customer_id = customer.id if customer else payload.customer_id

    # Check for failure simulation injection
    sim_header = (x_simulate_failure or "").lower().strip()

    if sim_header == "database_timeout":
        time.sleep(0.5)
        # Log structured error
        db_log = Log(
            level="ERROR",
            service="order-service",
            customer_id=effective_customer_id,
            request_id=req_id,
            endpoint="POST /api/v1/orders",
            status_code=500,
            message="Database connection pool timeout while attempting INSERT INTO orders",
            error_code="DB_TIMEOUT",
            response_time_ms=4820.0,
            metadata_json='{"db_cluster": "aurora-mysql-primary", "pool_active": 100, "pool_max": 100}',
        )
        db.add(db_log)
        db.commit()

        logger.error(
            f"Database connection timeout on POST /orders (Req: {req_id})",
            extra={"request_id": req_id, "customer_id": effective_customer_id, "error_code": "DB_TIMEOUT", "status_code": 500},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection timeout: could not acquire pool connection within 5000ms",
            headers={"X-Error-Code": "DB_TIMEOUT", "X-Request-ID": req_id},
        )

    if sim_header == "slow_sql_query":
        time.sleep(0.6)  # Emulate heavy lock contention
        # Persist order but log slow performance
        order = Order(
            customer_id=effective_customer_id,
            external_order_id=payload.external_order_id,
            amount=payload.amount,
            status="COMPLETED",
        )
        db.add(order)
        db_log = Log(
            level="WARNING",
            service="order-service",
            customer_id=effective_customer_id,
            request_id=req_id,
            endpoint="POST /api/v1/orders",
            status_code=200,
            message="Query execution latency exceeded 4500ms due to table lock contention",
            error_code="SLOW_SQL_QUERY",
            response_time_ms=4550.0,
        )
        db.add(db_log)
        db.commit()
        db.refresh(order)
        return order

    if sim_header == "500_application_exception":
        db_log = Log(
            level="ERROR",
            service="order-service",
            customer_id=effective_customer_id,
            request_id=req_id,
            endpoint="POST /api/v1/orders",
            status_code=500,
            message="Unhandled NullPointerException in PricingCalculationEngine.applyDiscounts()",
            error_code="INTERNAL_EXCEPTION",
            response_time_ms=120.0,
        )
        db.add(db_log)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail="Unhandled internal application exception",
            headers={"X-Error-Code": "INTERNAL_EXCEPTION", "X-Request-ID": req_id},
        )

    if sim_header == "missing_order_record":
        # Data Inconsistency scenario:
        # API returns 201 Created but deliberately rolls back DB commit!
        db_log = Log(
            level="ERROR",
            service="order-service",
            customer_id=effective_customer_id,
            request_id=req_id,
            endpoint="POST /api/v1/orders",
            status_code=201,
            message="Order transaction rolled back silently before commit phase; client returned 201",
            error_code="DATA_INCONSISTENCY",
            response_time_ms=85.0,
        )
        db.add(db_log)
        db.commit()

        # Return synthetic order object to simulate phantom success without saving to DB
        fake_now = db_log.timestamp
        return OrderResponse(
            id=999999,
            customer_id=effective_customer_id,
            external_order_id=payload.external_order_id,
            status="COMPLETED",
            amount=payload.amount,
            created_at=fake_now,
            updated_at=fake_now,
        )

    # Standard Normal Order Creation
    order = Order(
        customer_id=effective_customer_id,
        external_order_id=payload.external_order_id,
        amount=payload.amount,
        status="COMPLETED",
    )
    db.add(order)
    db_log = Log(
        level="INFO",
        service="order-service",
        customer_id=effective_customer_id,
        request_id=req_id,
        endpoint="POST /api/v1/orders",
        status_code=201,
        message=f"Order '{payload.external_order_id}' created successfully for customer {effective_customer_id}",
        response_time_ms=75.0,
    )
    db.add(db_log)
    db.commit()
    db.refresh(order)

    logger.info(
        f"Order {order.id} ({order.external_order_id}) created for customer {order.customer_id}",
        extra={"request_id": req_id, "customer_id": order.customer_id, "status_code": 201},
    )
    return order


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Retrieve single order by internal ID."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.get("/customers/{customer_id}/orders", response_model=List[OrderResponse])
def get_customer_orders(
    customer_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Retrieve all orders placed by a specific customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
