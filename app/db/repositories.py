"""SQLAlchemy Repositories for normal Application CRUD operations."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import Customer, Product, Order, ApiEndpoint, ApiTestRun, Log, SystemMetric, Incident
from app.core.security import mask_api_key


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_email(self, email: str) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.email == email).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        return self.db.query(Customer).offset(skip).limit(limit).all()

    def create(self, name: str, email: str, environment: str, api_key_hash: str) -> Customer:
        customer = Customer(
            name=name,
            email=email,
            environment=environment,
            api_key_hash=api_key_hash,
            status="active",
        )
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.sku == sku).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Product]:
        return self.db.query(Product).filter(Product.is_active == True).offset(skip).limit(limit).all()

    def create(self, sku: str, name: str, price: float, stock: int = 100, description: str = "") -> Product:
        product = Product(sku=sku, name=name, price=price, stock=stock, description=description)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_by_customer_and_external_id(self, customer_id: int, external_order_id: str) -> Optional[Order]:
        return (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id, Order.external_order_id == external_order_id)
            .first()
        )

    def list_by_customer(self, customer_id: int, skip: int = 0, limit: int = 50) -> List[Order]:
        return (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, customer_id: int, external_order_id: str, amount: float, status: str = "PENDING") -> Order:
        order = Order(
            customer_id=customer_id,
            external_order_id=external_order_id,
            amount=amount,
            status=status,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order


class LogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_request_id(self, request_id: str) -> List[Log]:
        return self.db.query(Log).filter(Log.request_id == request_id).order_by(Log.timestamp.asc()).all()

    def list_recent(self, limit: int = 100) -> List[Log]:
        return self.db.query(Log).order_by(Log.timestamp.desc()).limit(limit).all()

    def create(
        self,
        level: str,
        service: str,
        message: str,
        request_id: str,
        customer_id: Optional[int] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        metadata_json: Optional[str] = None,
    ) -> Log:
        log_entry = Log(
            level=level,
            service=service,
            message=message,
            request_id=request_id,
            customer_id=customer_id,
            endpoint=endpoint,
            status_code=status_code,
            error_code=error_code,
            response_time_ms=response_time_ms,
            metadata_json=metadata_json,
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry
