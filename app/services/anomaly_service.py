"""Runtime Anomaly Detection Service using trained Isolation Forest."""

from pathlib import Path
from typing import Any, Dict
import joblib
import numpy as np
from app.core.config import settings
from app.core.logging import logger
from ml.preprocessing import ANOMALY_FEATURE_NAMES


class AnomalyDetectionService:
    """Detects abnormal API and system telemetry patterns."""

    def __init__(self):
        self.artifacts_dir = Path(settings.ML_ARTIFACTS_DIR)
        self.model_path = self.artifacts_dir / "isolation_forest.joblib"
        self.scaler_path = self.artifacts_dir / "scaler.joblib"
        self.model = None
        self.scaler = None
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            if self.model_path.exists() and self.scaler_path.exists():
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
            else:
                logger.warning(f"Isolation Forest artifacts not found at {self.artifacts_dir}. Run training first.")
        except Exception as exc:
            logger.error(f"Error loading anomaly detection artifacts: {exc}")

    def detect_anomaly(self, telemetry_vector: Dict[str, float]) -> Dict[str, Any]:
        """
        Evaluate incoming telemetry against trained Isolation Forest baseline.
        Returns:
            is_anomaly: bool
            anomaly_score: float (decision function score)
            explanation: str
        """
        if self.model is None or self.scaler is None:
            # Re-attempt lazy load
            self._load_artifacts()
            if self.model is None or self.scaler is None:
                return {
                    "is_anomaly": False,
                    "anomaly_score": 0.0,
                    "status": "model_not_loaded",
                    "explanation": "Isolation Forest model artifact not loaded.",
                }

        # Build ordered vector
        features = [float(telemetry_vector.get(name, 0.0)) for name in ANOMALY_FEATURE_NAMES]
        X = np.array([features])
        X_scaled = self.scaler.transform(X)

        # In sklearn: -1 is anomaly, 1 is normal
        pred = self.model.predict(X_scaled)[0]
        # decision_function: negative indicates anomaly
        score = float(self.model.decision_function(X_scaled)[0])
        is_anomaly = bool(pred == -1)

        finding = (
            f"ANOMALOUS TELEMETRY DETECTED (Score: {score:.3f}). System parameters deviate significantly from normal baseline."
            if is_anomaly
            else f"Telemetry within normal operational baseline (Score: {score:.3f})."
        )

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(score, 4),
            "evaluated_features": telemetry_vector,
            "explanation": finding,
        }
