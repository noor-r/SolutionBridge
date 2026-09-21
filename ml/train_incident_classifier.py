"""Train and evaluate Incident Classification models across 7 PSE incident categories."""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from ml.data_generator import generate_incident_classifier_data, INCIDENT_CLASSES
from ml.preprocessing import IncidentFeatureExtractor

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def train_and_evaluate_classifier():
    print("Generating 1,400 labeled incident samples across 7 PSE categories...")
    df = generate_incident_classifier_data(n_samples=1400)

    # Split into train (70%), validation (15%), and test (15%)
    df_train, df_temp = train_test_split(df, test_size=0.30, random_state=42, stratify=df["category"])
    df_val, df_test = train_test_split(df_temp, test_size=0.50, random_state=42, stratify=df_temp["category"])

    print(f"Dataset split: Train={len(df_train)}, Validation={len(df_val)}, Test={len(df_test)}")

    # Extract features
    extractor = IncidentFeatureExtractor(max_features=1200)
    X_train = extractor.fit_transform(df_train)
    X_val = extractor.transform(df_val)
    X_test = extractor.transform(df_test)

    y_train = df_train["category"].values
    y_val = df_val["category"].values
    y_test = df_test["category"].values

    # Model 1: Baseline Logistic Regression
    print("\nTraining Baseline: TF-IDF + Logistic Regression...")
    lr_model = LogisticRegression(max_iter=1000, C=1.5, random_state=42)
    lr_model.fit(X_train, y_train)

    lr_test_preds = lr_model.predict(X_test)
    lr_acc = float(accuracy_score(y_test, lr_test_preds))
    lr_prec = float(precision_score(y_test, lr_test_preds, average="weighted", zero_division=0))
    lr_rec = float(recall_score(y_test, lr_test_preds, average="weighted", zero_division=0))
    lr_f1 = float(f1_score(y_test, lr_test_preds, average="weighted", zero_division=0))

    # Model 2: Comparison Random Forest Classifier
    print("Training Comparison: TF-IDF + Random Forest...")
    rf_model = RandomForestClassifier(n_estimators=120, max_depth=15, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)

    rf_test_preds = rf_model.predict(X_test)
    rf_acc = float(accuracy_score(y_test, rf_test_preds))
    rf_f1 = float(f1_score(y_test, rf_test_preds, average="weighted", zero_division=0))

    print(f"\nModel Comparison on Test Set:")
    print(f"  Logistic Regression : Accuracy = {lr_acc:.4f}, Weighted F1 = {lr_f1:.4f}")
    print(f"  Random Forest       : Accuracy = {rf_acc:.4f}, Weighted F1 = {rf_f1:.4f}")

    # Select Logistic Regression as primary production model for transparency & calibration
    primary_model = lr_model
    selected_name = "TF-IDF + Logistic Regression"
    cm = confusion_matrix(y_test, lr_test_preds, labels=INCIDENT_CLASSES).tolist()
    clf_report = classification_report(y_test, lr_test_preds, labels=INCIDENT_CLASSES, output_dict=True)

    metrics_payload = {
        "primary_model": selected_name,
        "classes": INCIDENT_CLASSES,
        "dataset_sizes": {
            "train": len(df_train),
            "validation": len(df_val),
            "test": len(df_test),
        },
        "test_metrics": {
            "accuracy": round(lr_acc, 4),
            "precision_weighted": round(lr_prec, 4),
            "recall_weighted": round(lr_rec, 4),
            "f1_weighted": round(lr_f1, 4),
            "confusion_matrix": cm,
            "per_class_f1": {cls: round(clf_report[cls]["f1-score"], 4) for cls in INCIDENT_CLASSES},
        },
        "comparison_metrics": {
            "random_forest_accuracy": round(rf_acc, 4),
            "random_forest_f1_weighted": round(rf_f1, 4),
        },
    }

    # Save artifacts
    model_path = ARTIFACTS_DIR / "incident_classifier.joblib"
    extractor_path = ARTIFACTS_DIR / "feature_extractor.joblib"
    metrics_path = ARTIFACTS_DIR / "classifier_metrics.json"

    joblib.dump(primary_model, model_path)
    joblib.dump(extractor, extractor_path)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"\nSaved primary model and extractor to {ARTIFACTS_DIR}")
    print(f"Metrics saved to {metrics_path}")
    return metrics_payload


if __name__ == "__main__":
    train_and_evaluate_classifier()
