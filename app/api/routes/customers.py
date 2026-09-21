"""Customer management routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Customer
from app.db.schemas import CustomerCreate, CustomerResponse, CustomerCreatedWithKey
from app.core.security import generate_api_key, mask_api_key
from app.utils.request_id import get_current_request_id
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])


def _to_customer_response(c: Customer) -> CustomerResponse:
    return CustomerResponse(
        id=c.id,
        name=c.name,
        email=c.email,
        environment=c.environment,
        status=c.status,
        masked_api_key=f"sb_{c.environment[:4]}_***{c.api_key_hash[-4:]}",
        created_at=c.created_at,
    )


@router.get("", response_model=List[CustomerResponse])
def list_customers(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve list of registered customer integration accounts (masked credentials)."""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return [_to_customer_response(c) for c in customers]


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Retrieve specific customer details."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with ID {customer_id} not found")
    return _to_customer_response(customer)


@router.post("", response_model=CustomerCreatedWithKey, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    """
    Create a new customer account and generate API key.
    The raw API key is returned ONLY in this response and must be saved by the caller.
    """
    existing = db.query(Customer).filter(Customer.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Customer with email {payload.email} already exists")

    raw_key, key_hash, masked_key = generate_api_key(payload.environment)
    customer = Customer(
        name=payload.name,
        email=payload.email,
        environment=payload.environment,
        api_key_hash=key_hash,
        status=payload.status,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    logger.info(
        f"Customer {customer.name} created (ID: {customer.id})",
        extra={"customer_id": customer.id, "request_id": get_current_request_id()},
    )

    return CustomerCreatedWithKey(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        environment=customer.environment,
        status=customer.status,
        masked_api_key=masked_key,
        created_at=customer.created_at,
        raw_api_key=raw_key,
        notice="Store this API key safely. It will not be displayed again.",
    )
