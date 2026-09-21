"""End-to-End Incident Orchestration Service for Solutions Engineering."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.db.models import Customer, Incident, IncidentEvidence, TroubleshootingAction
from app.services.log_analysis_service import LogAnalysisService
from app.services.sql_validation_service import SQLValidationService
from app.services.metrics_service import MetricsService
from app.services.anomaly_service import AnomalyDetectionService
from app.services.classification_service import IncidentClassificationService
from app.services.similarity_service import IncidentSimilarityService
from app.services.root_cause_engine import RootCauseEngine
from app.services.troubleshooting_service import TroubleshootingService
from app.services.llm_service import LLMExplanationService
from app.core.logging import logger


class IncidentService:
    """Orchestrates end-to-end multi-source investigation and incident management."""

    def __init__(self, db: Session):
        self.db = db
        self.log_service = LogAnalysisService(db)
        self.sql_service = SQLValidationService(db)
        self.metrics_service = MetricsService(db)
        self.anomaly_service = AnomalyDetectionService()
        self.classification_service = IncidentClassificationService()
        self.similarity_service = IncidentSimilarityService()
        self.root_cause_engine = RootCauseEngine()
        self.troubleshooting_service = TroubleshootingService()
        self.llm_service = LLMExplanationService()

    def analyze_request(self, request_id: str) -> Dict[str, Any]:
        """
        Execute full Product Solutions Engineer investigation workflow:
        Request ID -> Correlated Logs -> SQL Validation -> System Metrics -> ML Models -> FAISS -> Root Cause -> Actions
        """
        logger.info(f"Initiating end-to-end incident analysis for request_id: {request_id}")

        # 1. Correlate logs
        log_summary = self.log_service.analyze_logs(request_id)
        customer_id = log_summary.get("customer_id")
        endpoint = log_summary.get("primary_endpoint", "/api/v1/orders")
        detected_errors = log_summary.get("detected_errors", [])
        primary_msg = detected_errors[0]["message"] if detected_errors else "Order processing request"
        primary_err = detected_errors[0]["error_code"] if detected_errors else ""
        status_code = detected_errors[0]["status_code"] if detected_errors else 200

        # 2. Raw SQL forensic validation
        sql_findings = self.sql_service.detect_silent_order_rollbacks(request_id)
        order_persistence = self.sql_service.validate_order_persistence(
            customer_id=customer_id or 1,
            external_order_id=f"ORD-REQ-{request_id}",
        )
        sql_summary = {
            **sql_findings,
            "persisted": order_persistence.get("persisted", False),
        }

        # 3. Metrics extraction
        metric_vector = self.metrics_service.get_latest_feature_vector(
            latency_override=log_summary.get("max_latency_ms", 120.0),
        )

        # 4. ML Anomaly Detection
        ml_anomaly = self.anomaly_service.detect_anomaly(metric_vector)

        # 5. ML Incident Classification
        ml_classifier = self.classification_service.classify_incident(
            message=primary_msg,
            error_code=primary_err,
            status_code=status_code,
            endpoint=endpoint,
            response_time_ms=metric_vector.get("response_time_ms", 120.0),
            db_latency_ms=metric_vector.get("db_latency_ms", 5.0),
            cpu_percent=metric_vector.get("cpu_percent", 30.0),
            memory_percent=metric_vector.get("memory_percent", 45.0),
        )

        # 6. FAISS Semantic Similarity Search
        sim_query = f"{endpoint} status {status_code}. {primary_msg}. {primary_err}."
        similar_incidents = self.similarity_service.find_similar_incidents(sim_query, top_k=3)

        # 7. Root Cause Synthesis
        api_evidence = {
            "status_code": status_code,
            "response_time_ms": metric_vector.get("response_time_ms"),
            "endpoint": endpoint,
        }
        diagnosis = self.root_cause_engine.diagnose(
            request_id=request_id,
            api_evidence=api_evidence,
            sql_evidence=sql_summary,
            log_evidence=log_summary,
            metric_evidence=metric_vector,
            ml_anomaly=ml_anomaly,
            ml_classifier=ml_classifier,
            similar_incidents=similar_incidents,
        )

        # 8. Troubleshooting Recommendations
        recommended_actions = self.troubleshooting_service.get_recommendations(
            category=diagnosis["category"],
            evidence_list=diagnosis["deterministic_evidence"],
        )

        # 9. Optional LLM Explanation Layer (with deterministic template fallback)
        narratives = self.llm_service.generate_incident_narratives(
            request_id=request_id,
            category=diagnosis["category"],
            confidence=diagnosis["confidence"],
            root_cause=diagnosis["probable_root_cause"],
            evidence_list=diagnosis["deterministic_evidence"],
            default_engineer_summary=diagnosis["engineer_summary"],
            default_customer_summary=diagnosis["customer_summary"],
        )
        engineer_summary = narratives["engineer_summary"]
        customer_summary = narratives["customer_summary"]

        # 10. Persist or Update Incident in Database
        incident = self.db.query(Incident).filter(Incident.request_id == request_id).first()
        title = f"{diagnosis['category']} Failure on {endpoint} ({request_id})"

        if not incident:
            incident = Incident(
                customer_id=customer_id,
                request_id=request_id,
                title=title,
                severity=log_summary.get("severity", "MEDIUM"),
                category=diagnosis["category"],
                predicted_root_cause=diagnosis["probable_root_cause"],
                confidence=diagnosis["confidence"],
                status="OPEN",
                evidence_summary="\n".join(diagnosis["deterministic_evidence"]),
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(incident)
            self.db.flush()

            # Persist Evidence Items
            for ev in diagnosis["deterministic_evidence"]:
                ev_type = "LOG" if "log" in ev.lower() else ("SQL" if "sql" in ev.lower() else ("ML" if "ml" in ev.lower() else "API"))
                self.db.add(IncidentEvidence(
                    incident_id=incident.id,
                    evidence_type=ev_type,
                    source_id=request_id,
                    evidence_text=ev,
                ))

            # Persist Troubleshooting Actions
            for act in recommended_actions:
                self.db.add(TroubleshootingAction(
                    incident_id=incident.id,
                    action=act["action"],
                    rationale=act["rationale"],
                    result=None,
                ))

            self.db.commit()
            self.db.refresh(incident)
        else:
            # Update existing
            incident.category = diagnosis["category"]
            incident.predicted_root_cause = diagnosis["probable_root_cause"]
            incident.confidence = diagnosis["confidence"]
            incident.evidence_summary = "\n".join(diagnosis["deterministic_evidence"])
            self.db.commit()
            self.db.refresh(incident)

        return {
            "incident_id": incident.id,
            "request_id": request_id,
            "category": diagnosis["category"],
            "confidence": diagnosis["confidence"],
            "predicted_root_cause": diagnosis["probable_root_cause"],
            "deterministic_evidence": diagnosis["deterministic_evidence"],
            "ml_evidence": diagnosis["ml_evidence"],
            "similar_incidents": similar_incidents,
            "recommended_actions": recommended_actions,
            "engineer_summary": engineer_summary,
            "customer_summary": customer_summary,
        }
