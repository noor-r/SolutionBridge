"""SQLAlchemy database models."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Numeric,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Customer(Base):
    """Customer integration profile."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    environment = Column(String(50), default="production", nullable=False)
    api_key_hash = Column(String(128), nullable=False)
    status = Column(String(50), default="active", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    test_runs = relationship("ApiTestRun", back_populates="customer")
    incidents = relationship("Incident", back_populates="customer")


class Product(Base):
    """Product catalog for integration and orders."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    stock = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class ApiEndpoint(Base):
    """Registered API endpoints for integration testing."""
    __tablename__ = "api_endpoints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    method = Column(String(10), nullable=False)
    endpoint = Column(String(200), nullable=False)
    service = Column(String(100), nullable=False)
    expected_status = Column(Integer, default=200, nullable=False)
    max_response_time_ms = Column(Integer, default=500, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    test_runs = relationship("ApiTestRun", back_populates="endpoint")


class ApiTestRun(Base):
    """Individual API test run results."""
    __tablename__ = "api_test_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    endpoint_id = Column(Integer, ForeignKey("api_endpoints.id"), nullable=False)
    request_id = Column(String(100), nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    test_status = Column(String(50), nullable=False)  # PASSED, FAILED, ERROR
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    customer = relationship("Customer", back_populates="test_runs")
    endpoint = relationship("ApiEndpoint", back_populates="test_runs")


class Order(Base):
    """Customer order transactions."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    external_order_id = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    customer = relationship("Customer", back_populates="orders")


class Log(Base):
    """Application log entries for correlation and root-cause analysis."""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    service = Column(String(100), nullable=False, index=True)
    customer_id = Column(Integer, nullable=True, index=True)
    request_id = Column(String(100), nullable=False, index=True)
    endpoint = Column(String(200), nullable=True)
    status_code = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    error_code = Column(String(100), nullable=True, index=True)
    response_time_ms = Column(Float, nullable=True)
    metadata_json = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_logs_req_level", "request_id", "level"),
        Index("idx_logs_cust_time", "customer_id", "timestamp"),
    )


class SystemMetric(Base):
    """System telemetry observations."""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    db_latency_ms = Column(Float, nullable=False)
    active_connections = Column(Integer, nullable=False)
    request_rate = Column(Float, nullable=False)
    error_rate = Column(Float, nullable=False)


class Incident(Base):
    """Tracked incidents discovered through API failures or investigations."""
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    request_id = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(String(50), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    category = Column(String(100), nullable=False)  # Database, Authentication, Performance, Infrastructure, Integration, Application, Data Consistency
    predicted_root_cause = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), default="OPEN", nullable=False)  # OPEN, INVESTIGATING, RESOLVED
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="incidents")
    evidence_items = relationship("IncidentEvidence", back_populates="incident", cascade="all, delete-orphan")
    actions = relationship("TroubleshootingAction", back_populates="incident", cascade="all, delete-orphan")


class IncidentEvidence(Base):
    """Individual supporting evidence items attached to an incident."""
    __tablename__ = "incident_evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    evidence_type = Column(String(50), nullable=False)  # API, SQL, LOG, METRIC, ML, SIMILARITY
    source_id = Column(String(100), nullable=True)
    evidence_text = Column(Text, nullable=False)

    incident = relationship("Incident", back_populates="evidence_items")


class TroubleshootingAction(Base):
    """Actionable remediation steps recommended or taken for an incident."""
    __tablename__ = "troubleshooting_actions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    action = Column(String(250), nullable=False)
    rationale = Column(Text, nullable=False)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    incident = relationship("Incident", back_populates="actions")


class HistoricalIncident(Base):
    """Curated knowledge base of historical incidents for semantic vector retrieval."""
    __tablename__ = "historical_incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String(50), nullable=False, unique=True, index=True)
    text = Column(Text, nullable=False)
    embedding_reference = Column(String(100), nullable=True)
    resolution = Column(Text, nullable=False)
