"""Offline Model Evaluation and Diagnostics Summary."""

import json
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


def evaluate_all():
    print("==================================================")
    print("   SolutionBridge ML Models Performance Report    ")
    print("==================================================")

    # 1. Anomaly Detection
    anomaly_metrics_file = ARTIFACTS_DIR / "anomaly_metrics.json"
    if anomaly_metrics_file.exists():
        with open(anomaly_metrics_file, "r", encoding="utf-8") as f:
            am = json.load(f)
        print("\n[1] Telemetry Anomaly Detection (Isolation Forest)")
        print(f"    - Training Observations  : {am['n_train_samples']} (Strictly Normal Telemetry)")
        print(f"    - Holdout Test Samples   : {am['n_holdout_samples']} ({am['holdout_normal_count']} normal, {am['holdout_abnormal_count']} abnormal)")
        print(f"    - Holdout Precision      : {am['precision']:.4f}")
        print(f"    - Holdout Recall         : {am['recall']:.4f}")
        print(f"    - Holdout F1 Score       : {am['f1_score']:.4f}")
        print(f"    - ROC-AUC Score          : {am['roc_auc']:.4f}")
        cm = am['confusion_matrix']
        print(f"    - Holdout Confusion Matrix: TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")

    # 2. Incident Classification
    clf_metrics_file = ARTIFACTS_DIR / "classifier_metrics.json"
    if clf_metrics_file.exists():
        with open(clf_metrics_file, "r", encoding="utf-8") as f:
            cm = json.load(f)
        print("\n[2] Incident Classification (TF-IDF + Logistic Regression)")
        print(f"    - Production Classifier  : {cm['primary_model']}")
        val_size = cm['dataset_sizes'].get('validation', cm['dataset_sizes'].get('val', 0))
        print(f"    - Dataset Splits         : Train={cm['dataset_sizes']['train']}, Val={val_size}, Test={cm['dataset_sizes']['test']}")
        print(f"    - Test Accuracy          : {cm['test_metrics']['accuracy']:.4f}")
        print(f"    - Test Weighted F1       : {cm['test_metrics']['f1_weighted']:.4f}")
        print(f"    - Comparison RF Accuracy : {cm['comparison_metrics']['random_forest_accuracy']:.4f}")
        print("    - Per-Class F1 Scores    :")
        for cls_name, f1_val in cm['test_metrics']['per_class_f1'].items():
            print(f"        * {cls_name.ljust(20)}: {f1_val:.4f}")

    # 3. Vector Similarity
    faiss_file = ARTIFACTS_DIR / "faiss_index.bin"
    corpus_file = ARTIFACTS_DIR / "historical_incidents.json"
    if faiss_file.exists() and corpus_file.exists():
        with open(corpus_file, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        print("\n[3] Semantic Similar Incident Retrieval (FAISS + Sentence-Transformers)")
        print(f"    - Embedding Model        : all-MiniLM-L6-v2 (384-dimensional dense vectors)")
        print(f"    - Indexed Incidents      : {len(corpus)} historical postmortems & resolutions")
        print(f"    - Index Type             : Flat Inner-Product (Cosine Similarity)")

    print("\n==================================================")


if __name__ == "__main__":
    evaluate_all()
