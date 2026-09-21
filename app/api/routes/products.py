"""Product catalog routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Product
from app.db.schemas import ProductCreate, ProductResponse
from app.utils.request_id import get_current_request_id
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
def list_products(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve catalog of available products for integration."""
    return db.query(Product).filter(Product.is_active == True).offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product in the catalog."""
    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU '{payload.sku}' already exists")

    product = Product(
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        stock=payload.stock,
        is_active=payload.is_active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    logger.info(
        f"Product '{product.name}' (SKU: {product.sku}) created",
        extra={"request_id": get_current_request_id()},
    )
    return product
