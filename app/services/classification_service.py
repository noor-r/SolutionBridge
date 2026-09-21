"""Runtime Incident Classification Service using TF-IDF + Logistic Regression."""

from pathlib import Path
from typing import Any, Dict, List
import joblib
import pandas as pd
from app.core.config import settings
from app.core.logging import logger
from ml.data_generator import INCIDENT_CLASSES


class IncidentClassificationService:
    """Classifies incidents into 7 PSE categories with calibrated probability estimates."""

    def __init__(self):
        self.artifacts_dir = Path(settings.ML_ARTIFACTS_DIR)
        self.model_path = self.artifacts_dir / "incident_classifier.joblib"
        self.extractor_path = self.artifacts_dir / "feature_extractor.joblib"
        self.model = None
        self.extractor = None
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            if self.model_path.exists() and self.extractor_path.exists():
                self.model = joblib.load(self.model_path)
                self.extractor = joblib.load(self.extractor_path)
            else:
                logger.warning(f"Classifier artifacts not found at {self.artifacts_dir}. Run training first.")
        except Exception as exc:
            logger.error(f"Error loading classification artifacts: {exc}")

    def classify_incident(
        self,
        message: str,
        error_code: str = "",
        status_code: int = 500,
        endpoint: str = "/api/v1/orders",
        response_time_ms: float = 100.0,
        db_latency_ms: float = 5.0,
        cpu_percent: float = 30.0,
        memory_percent: float = 45.0,
    ) -> Dict[str, Any]:
        """
        Classify an incident observation into one of 7 categories.
        Returns:
            predicted_category: str
            probability: float
            class_probabilities: Dict[str, float]
            explanation: str
        """
        if self.model is None or self.extractor is None:
            self._load_artifacts()
            if self.model is None or self.extractor is None:
                return {
                    "predicted_category": "Application",
                    "probability": 0.50,
                    "class_probabilities": {c: round(1.0 / len(INCIDENT_CLASSES), 3) for c in INCIDENT_CLASSES},
                    "status": "model_not_loaded",
                    "explanation": "Classifier model artifact not loaded. Defaulting to baseline advisory category.",
                }

        text_feature = f"{message}. Error: {error_code} on {endpoint} with status {status_code}."
        row = pd.DataFrame([{
            "text": text_feature,
            "message": message,
            "error_code": error_code or "",
            "status_code": status_code or 500,
            "endpoint": endpoint or "",
            "response_time_ms": float(response_time_ms or 0.0),
            "db_latency_ms": float(db_latency_ms or 0.0),
            "cpu_percent": float(cpu_percent or 0.0),
            "memory_percent": float(memory_percent or 0.0),
        }])

        X = self.extractor.transform(row)
        pred_cat = str(self.model.predict(X)[0])
        probas = self.model.predict_proba(X)[0]

        classes = getattr(self.model, "classes_", INCIDENT_CLASSES)
        class_prob_map = {str(c): round(float(p), 4) for c, p in zip(classes, probas)}
        confidence = class_prob_map.get(pred_cat, 0.85)

        return {
            "predicted_category": pred_cat,
            "probability": round(confidence, 4),
            "class_probabilities": class_prob_map,
            "input_summary": {
                "message": message,
                "error_code": error_code,
                "status_code": status_code,
                "endpoint": endpoint,
            },
            "explanation": f"ML classifier predicted '{pred_cat}' category with {confidence*100:.1f}% confidence.",
        }
