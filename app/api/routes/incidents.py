"""Incident management, diagnosis, and recommendations routes."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Incident, IncidentEvidence, TroubleshootingAction
from app.db.schemas import (
    IncidentDiagnosisResponse,
    IncidentRecommendationsResponse,
    IncidentResponse,
    IncidentStatusUpdate,
)
from app.services.incident_service import IncidentService

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    incident_status: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve filtered list of tracked integration incidents."""
    query = db.query(Incident)
    if category:
        query = query.filter(Incident.category == category)
    if severity:
        query = query.filter(Incident.severity == severity.upper())
    if incident_status:
        query = query.filter(Incident.status == incident_status.upper())
    if customer_id:
        query = query.filter(Incident.customer_id == customer_id)

    return query.order_by(Incident.created_at.desc()).limit(limit).all()


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """Retrieve full incident details including evidence items and troubleshooting actions."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident


@router.post("/analyze/{request_id}", response_model=IncidentDiagnosisResponse)
def analyze_request_incident(request_id: str, db: Session = Depends(get_db)):
    """
    Trigger end-to-end multi-source investigation for an API failure:
    Correlates Logs -> Runs Raw SQL -> Extracts Metrics -> Anomaly ML -> Classifier ML -> FAISS -> Root Cause -> Actions
    """
    service = IncidentService(db)
    result = service.analyze_request(request_id)
    return IncidentDiagnosisResponse(
        incident_id=result["incident_id"],
        request_id=result["request_id"],
        category=result["category"],
        confidence=result["confidence"],
        predicted_root_cause=result["predicted_root_cause"],
        deterministic_evidence=result["deterministic_evidence"],
        ml_evidence=result["ml_evidence"],
        similar_incidents=result["similar_incidents"],
        engineer_summary=result["engineer_summary"],
        customer_summary=result["customer_summary"],
    )


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    incident_id: int,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update incident lifecycle state (OPEN, INVESTIGATING, RESOLVED)."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    incident.status = payload.status
    if payload.status == "RESOLVED":
        incident.resolved_at = datetime.now(timezone.utc)
        if payload.resolution_notes:
            incident.predicted_root_cause += f"\n[Resolution Notes]: {payload.resolution_notes}"

    db.commit()
    db.refresh(incident)
    return incident


@router.get("/{incident_id}/diagnosis", response_model=IncidentDiagnosisResponse)
def get_incident_diagnosis(incident_id: int, db: Session = Depends(get_db)):
    """Retrieve comprehensive forensic diagnostic report for an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    service = IncidentService(db)
    result = service.analyze_request(incident.request_id)
    return IncidentDiagnosisResponse(
        incident_id=incident.id,
        request_id=incident.request_id,
        category=result["category"],
        confidence=result["confidence"],
        predicted_root_cause=result["predicted_root_cause"],
        deterministic_evidence=result["deterministic_evidence"],
        ml_evidence=result["ml_evidence"],
        similar_incidents=result["similar_incidents"],
        engineer_summary=result["engineer_summary"],
        customer_summary=result["customer_summary"],
    )


@router.get("/{incident_id}/recommendations", response_model=IncidentRecommendationsResponse)
def get_incident_recommendations(incident_id: int, db: Session = Depends(get_db)):
    """Retrieve prioritized troubleshooting actions for an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    service = IncidentService(db)
    result = service.analyze_request(incident.request_id)
    return IncidentRecommendationsResponse(
        incident_id=incident.id,
        request_id=incident.request_id,
        category=incident.category,
        actions=result["recommended_actions"],
    )
