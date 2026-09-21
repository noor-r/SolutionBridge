"""Pydantic v2 schemas for SolutionBridge requests and responses."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -------------------------------------------------------------------
# Customer Schemas
# -------------------------------------------------------------------
class CustomerBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=150)
    environment: str = Field(default="production")
    status: str = Field(default="active")


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: int
    masked_api_key: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CustomerCreatedWithKey(CustomerResponse):
    """Returned ONLY upon customer creation or credential regeneration."""
    raw_api_key: str
    notice: str = "Store this API key safely. It will not be shown again."


# -------------------------------------------------------------------
# Product Schemas
# -------------------------------------------------------------------
class ProductBase(BaseModel):
    sku: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    stock: int = Field(default=100, ge=0)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------
# Order Schemas
# -------------------------------------------------------------------
class OrderCreate(BaseModel):
    customer_id: int
    external_order_id: str
    amount: Decimal = Field(..., gt=0)


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    external_order_id: str
    status: str
    amount: Decimal
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------
# API Endpoint & Test Schemas
# -------------------------------------------------------------------
class ApiEndpointResponse(BaseModel):
    id: int
    name: str
    method: str
    endpoint: str
    service: str
    expected_status: int
    max_response_time_ms: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class ApiTestRunCreate(BaseModel):
    customer_id: Optional[int] = None
    endpoint_id: int
    request_id: str
    status_code: int
    response_time_ms: float
    test_status: str
    response_body: Optional[str] = None
    error_message: Optional[str] = None


class ApiTestRunResponse(BaseModel):
    id: int
    customer_id: Optional[int]
    endpoint_id: int
    request_id: str
    status_code: int
    response_time_ms: float
    test_status: str
    response_body: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApiTestSummary(BaseModel):
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    pass_rate: float
    avg_response_time_ms: float


# -------------------------------------------------------------------
# Log Schemas
# -------------------------------------------------------------------
class LogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    service: str
    customer_id: Optional[int]
    request_id: str
    endpoint: Optional[str]
    status_code: Optional[int]
    message: str
    error_code: Optional[str]
    response_time_ms: Optional[float]
    metadata_json: Optional[str]
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------
# System Metric Schemas
# -------------------------------------------------------------------
class SystemMetricResponse(BaseModel):
    id: int
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    db_latency_ms: float
    active_connections: int
    request_rate: float
    error_rate: float
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------
# Incident & Diagnosis Schemas
# -------------------------------------------------------------------
class IncidentEvidenceResponse(BaseModel):
    id: int
    evidence_type: str
    source_id: Optional[str]
    evidence_text: str
    model_config = ConfigDict(from_attributes=True)


class TroubleshootingActionResponse(BaseModel):
    id: int
    action: str
    rationale: str
    result: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class IncidentResponse(BaseModel):
    id: int
    customer_id: Optional[int]
    request_id: str
    title: str
    severity: str
    category: str
    predicted_root_cause: str
    confidence: float
    status: str
    evidence_summary: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    evidence_items: List[IncidentEvidenceResponse] = []
    actions: List[TroubleshootingActionResponse] = []
    model_config = ConfigDict(from_attributes=True)


class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(OPEN|INVESTIGATING|RESOLVED)$")
    resolution_notes: Optional[str] = None


class IncidentDiagnosisResponse(BaseModel):
    incident_id: int
    request_id: str
    category: str
    confidence: float
    predicted_root_cause: str
    deterministic_evidence: List[str]
    ml_evidence: Dict[str, Any]
    similar_incidents: List[Dict[str, Any]]
    engineer_summary: str
    customer_summary: str


class IncidentRecommendationsResponse(BaseModel):
    incident_id: int
    request_id: str
    category: str
    actions: List[Dict[str, Any]]


# -------------------------------------------------------------------
# Demo Scenario Schemas
# -------------------------------------------------------------------
class DemoScenarioRequest(BaseModel):
    scenario: str
    customer_id: Optional[int] = 1


class DemoScenarioResponse(BaseModel):
    status: str
    scenario: str
    customer_id: int
    request_id: str
    http_status: int
    error_code: Optional[str] = None
    message: str
    investigation_url: str
    details: Dict[str, Any] = {}
