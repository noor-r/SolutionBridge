"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Customer
from app.core.security import verify_api_key, mask_api_key
from app.utils.request_id import get_current_request_id
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    customer_id: int
    api_key: str


class LoginResponse(BaseModel):
    status: str
    customer_id: int
    customer_name: str
    environment: str
    masked_api_key: str
    session_token: str
    message: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate customer credentials and return integration session."""
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    req_id = get_current_request_id()

    if not customer or not verify_api_key(payload.api_key, customer.api_key_hash):
        logger.warning(
            f"Authentication failed for customer_id {payload.customer_id}",
            extra={
                "request_id": req_id,
                "customer_id": payload.customer_id,
                "status_code": 401,
                "error_code": "AUTH_INVALID",
                "service": "auth-service",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: customer ID or API key mismatch",
            headers={"X-Error-Code": "AUTH_INVALID"},
        )

    logger.info(
        f"Customer '{customer.name}' (ID: {customer.id}) authenticated successfully",
        extra={
            "request_id": req_id,
            "customer_id": customer.id,
            "status_code": 200,
            "service": "auth-service",
        },
    )

    return LoginResponse(
        status="authenticated",
        customer_id=customer.id,
        customer_name=customer.name,
        environment=customer.environment,
        masked_api_key=mask_api_key(payload.api_key),
        session_token=f"sess_{customer.id}_{req_id}",
        message="Integration credentials validated successfully.",
    )
