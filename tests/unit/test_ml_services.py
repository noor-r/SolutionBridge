"""Unit tests for ML Inference and Root Cause & Troubleshooting Engines."""

from app.services.anomaly_service import AnomalyDetectionService
from app.services.classification_service import IncidentClassificationService
from app.services.similarity_service import IncidentSimilarityService
from app.services.root_cause_engine import RootCauseEngine
from app.services.troubleshooting_service import TroubleshootingService


def test_anomaly_detection_service():
    svc = AnomalyDetectionService()
    # Normal telemetry vector
    normal_vector = {
        "response_time_ms": 75.0,
        "db_latency_ms": 5.0,
        "cpu_percent": 30.0,
        "memory_percent": 45.0,
        "request_rate": 180.0,
        "error_rate": 0.2,
        "active_connections": 25.0,
    }
    normal_res = svc.detect_anomaly(normal_vector)
    assert normal_res["is_anomaly"] is False

    # Extreme anomalous vector
    abnormal_vector = {
        "response_time_ms": 4900.0,
        "db_latency_ms": 320.0,
        "cpu_percent": 98.0,
        "memory_percent": 95.0,
        "request_rate": 1500.0,
        "error_rate": 45.0,
        "active_connections": 115.0,
    }
    abnormal_res = svc.detect_anomaly(abnormal_vector)
    assert abnormal_res["is_anomaly"] is True
    assert abnormal_res["anomaly_score"] < 0.0


def test_incident_classification_service():
    svc = IncidentClassificationService()
    res = svc.classify_incident(
        message="Database connection pool timeout waiting for connection",
        error_code="DB_TIMEOUT",
        status_code=500,
        response_time_ms=4800.0,
        db_latency_ms=320.0,
    )
    assert res["predicted_category"] == "Database"
    assert res["probability"] > 0.5
    assert "class_probabilities" in res


def test_incident_similarity_service():
    svc = IncidentSimilarityService()
    matches = svc.find_similar_incidents("POST /orders database timeout latency 4.8s", top_k=3)
    assert len(matches) == 3
    assert matches[0]["similarity_score"] > 0.6
    assert "resolution" in matches[0]


def test_root_cause_engine():
    engine = RootCauseEngine()
    diag = engine.diagnose(
        request_id="REQ-TEST-DIAG",
        api_evidence={"status_code": 500, "response_time_ms": 4820.0, "endpoint": "POST /api/v1/orders"},
        sql_evidence={"persisted": False, "inconsistency_detected": False},
        log_evidence={"detected_errors": [{"message": "DB timeout"}], "error_codes": ["DB_TIMEOUT"]},
        metric_evidence={"db_latency_ms": 280.0, "cpu_percent": 45.0, "active_connections": 95},
        ml_anomaly={"is_anomaly": True, "anomaly_score": -0.42},
        ml_classifier={"predicted_category": "Database", "probability": 0.96},
        similar_incidents=[{"incident_id": "INC-421", "title": "DB Connection Exhaustion", "similarity_score": 0.82}],
    )
    assert diag["category"] == "Database"
    assert diag["confidence"] >= 0.90
    assert len(diag["deterministic_evidence"]) >= 3
    assert "TECHNICAL POSTMORTEM" in diag["engineer_summary"]
    assert "Dear Customer" in diag["customer_summary"]


def test_troubleshooting_service():
    svc = TroubleshootingService()
    actions = svc.get_recommendations("Database", ["DB connection timeout observed"])
    assert len(actions) >= 3
    assert actions[0]["priority"] == 1
    assert "action" in actions[0]
    assert "rationale" in actions[0]
    assert "verification_step" in actions[0]
