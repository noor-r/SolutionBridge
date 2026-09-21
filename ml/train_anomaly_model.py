"""Train and evaluate Isolation Forest anomaly detection model."""

import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from ml.data_generator import generate_anomaly_data
from ml.preprocessing import ANOMALY_FEATURE_NAMES

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def train_and_evaluate_anomaly_model():
    print("Generating telemetry data: training (normal-only) and holdout evaluation set...")
    df_train, df_holdout = generate_anomaly_data(
        n_train_normal=2000,
        n_test_normal=400,
        n_test_abnormal=200,
    )

    X_train = df_train[ANOMALY_FEATURE_NAMES].values
    X_test = df_holdout[ANOMALY_FEATURE_NAMES].values
    y_test = df_holdout["is_anomaly"].values  # 0 = normal, 1 = abnormal

    # Fit scaler strictly on normal training data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("Training IsolationForest on normal telemetry baseline...")
    # contamination is set to expected low baseline false-positive rate
    iso_forest = IsolationForest(
        n_estimators=150,
        contamination=0.03,
        random_state=42,
        n_jobs=-1,
    )
    iso_forest.fit(X_train_scaled)

    # Evaluate on holdout set
    # In sklearn IsolationForest: -1 indicates anomaly, 1 indicates normal
    raw_preds = iso_forest.predict(X_test_scaled)
    y_pred = np.where(raw_preds == -1, 1, 0)
    decision_scores = -iso_forest.decision_function(X_test_scaled)  # higher = more anomalous

    precision = float(precision_score(y_test, y_pred))
    recall = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))
    auc = float(roc_auc_score(y_test, decision_scores))
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "model_name": "IsolationForest",
        "features": ANOMALY_FEATURE_NAMES,
        "n_train_samples": len(df_train),
        "n_holdout_samples": len(df_holdout),
        "holdout_normal_count": int((y_test == 0).sum()),
        "holdout_abnormal_count": int((y_test == 1).sum()),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(auc, 4),
        "confusion_matrix": cm,
        "notes": "Model trained strictly on normal telemetry baseline and evaluated against labeled holdout set.",
    }

    # Save artifacts
    model_path = ARTIFACTS_DIR / "isolation_forest.joblib"
    scaler_path = ARTIFACTS_DIR / "scaler.joblib"
    metrics_path = ARTIFACTS_DIR / "anomaly_metrics.json"

    joblib.dump(iso_forest, model_path)
    joblib.dump(scaler, scaler_path)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\n--- Isolation Forest Holdout Evaluation ---")
    print(f"  Holdout Samples : {len(df_holdout)} ({metrics['holdout_normal_count']} normal, {metrics['holdout_abnormal_count']} abnormal)")
    print(f"  Precision       : {metrics['precision']:.4f}")
    print(f"  Recall          : {metrics['recall']:.4f}")
    print(f"  F1 Score        : {metrics['f1_score']:.4f}")
    print(f"  ROC-AUC Score   : {metrics['roc_auc']:.4f}")
    print(f"  Confusion Matrix: TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")
    print(f"Artifacts saved to {ARTIFACTS_DIR}\n")

    return metrics


if __name__ == "__main__":
    train_and_evaluate_anomaly_model()
