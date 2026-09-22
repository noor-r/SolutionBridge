"""FastAPI dependencies: DB sessions, API Key authentication, and context helpers."""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Customer
from app.core.security import verify_api_key, mask_api_key
from app.core.logging import logger
from app.utils.request_id import get_current_request_id


def get_current_customer(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Optional[Customer]:
    """
    Authenticate request via X-API-Key header.
    Looks up matching customer hash safely using constant-time comparison.
    """
    if not x_api_key:
        return None

    computed_hash = hash_api_key(x_api_key)
    customer = (
        db.query(Customer)
        .filter(Customer.api_key_hash == computed_hash, Customer.status == "active")
        .first()
    )
    if customer and verify_api_key(x_api_key, customer.api_key_hash):
        return customer

    req_id = get_current_request_id()
    logger.warning(
        f"API key authentication failed for supplied key: {mask_api_key(x_api_key)}",
        extra={
            "request_id": req_id,
            "status_code": 401,
            "error_code": "AUTH_INVALID",
            "service": "auth-service",
        },
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or unrecognized API key provided in X-API-Key header",
        headers={"WWW-Authenticate": "ApiKey", "X-Error-Code": "AUTH_INVALID"},
    )


def require_customer_auth(
    customer: Optional[Customer] = Depends(get_current_customer),
) -> Customer:
    """Strict dependency requiring authenticated customer."""
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey", "X-Error-Code": "AUTH_REQUIRED"},
        )
    return customer
