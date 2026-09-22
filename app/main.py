"""Main FastAPI Application Entrypoint for SolutionBridge."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger
from app.core.middleware import RequestTrackingMiddleware
from app.db.database import init_db, test_db_connection
from app.api.routes import (
    auth,
    customers,
    products,
    orders,
    tests,
    logs,
    metrics,
    incidents,
    demo,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.APP_ENV})")
    # Initialize DB schema on startup if needed
    try:
        init_db()
        logger.info("Database schema initialized.")
    except Exception as exc:
        logger.warning(f"Database initialization deferred: {exc}")
    yield
    logger.info("Shutting down SolutionBridge application.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "SolutionBridge — Product Integration & ML-Assisted Troubleshooting Platform "
        "tailored for Product Solutions Engineers. Automates the investigation lifecycle: "
        "Customer Integration → API Testing → SQL Validation → Log Analysis → System Monitoring → ML Diagnosis → Troubleshooting."
    ),
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware for Request ID tracking and structured logging
app.add_middleware(RequestTrackingMiddleware)


# Health & Readiness Endpoints
@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe: verifies the API service is accepting traffic."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@app.get("/ready", tags=["Health"])
def readiness_check():
    """Readiness probe: verifies connectivity to backend database dependencies."""
    db_ok = test_db_connection()
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unready",
                "database_connected": False,
                "message": "Database connection refused or unreachable.",
            },
        )
    return {
        "status": "ready",
        "database_connected": True,
        "service": settings.APP_NAME,
    }


# Include Route Modules
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(tests.router)
app.include_router(logs.router)
app.include_router(metrics.router)
app.include_router(incidents.router)
app.include_router(demo.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "platform": settings.APP_NAME,
        "description": "Product Integration & ML-Assisted Troubleshooting Platform",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "health_check": "/health",
        "readiness_check": "/ready",
    }
