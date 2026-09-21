"""Unified One-Command Demo Runner for SolutionBridge.

Demonstrates the complete Product Solutions Engineer workflow:
Customer Integration → API Testing → SQL Validation → Log Analysis → System Monitoring → ML-Assisted Diagnosis → Troubleshooting Actions

Runs all 5 core scenarios:
- Scenario A: Database timeout
- Scenario B: Invalid authentication
- Scenario C: Performance degradation
- Scenario D: Infrastructure issue
- Scenario E: Data inconsistency (silent rollback)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Parse optional database URL override
parser = argparse.ArgumentParser(description="Run SolutionBridge end-to-end demonstration")
parser.add_argument("--database-url", "-d", help="Override DATABASE_URL")
args, _ = parser.parse_known_args()

if args.database_url:
    os.environ["DATABASE_URL"] = args.database_url
elif "DATABASE_URL" not in os.environ:
    # Use development database for local demonstration if not explicitly set
    os.environ["DATABASE_URL"] = "sqlite:///./solutionbridge_dev.db"

from app.core.config import settings
from app.core.logging import logger
from app.db.database import SessionLocal, init_db, test_db_connection
from app.db.seed import seed_database
from app.services.failure_simulator import FailureSimulator
from app.services.incident_service import IncidentService
from ml.train_anomaly_model import train_and_evaluate_anomaly_model
from ml.train_incident_classifier import train_and_evaluate_classifier
from ml.build_embeddings import build_embeddings_and_faiss


def ensure_ml_artifacts():
    """Ensure all required ML artifacts exist; train if missing."""
    artifacts_dir = Path(settings.ML_ARTIFACTS_DIR)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    iso_file = artifacts_dir / "isolation_forest.joblib"
    clf_file = artifacts_dir / "incident_classifier.joblib"
    faiss_file = artifacts_dir / "faiss_index.bin"

    if not iso_file.exists():
        print("Anomaly detection model artifact missing. Training Isolation Forest...")
        train_and_evaluate_anomaly_model()
    if not clf_file.exists():
        print("Classifier model artifact missing. Training Incident Classifier...")
        train_and_evaluate_classifier()
    if not faiss_file.exists():
        print("FAISS index artifact missing. Building sentence embeddings and FAISS index...")
        build_embeddings_and_faiss()


def run_demo():
    # Set utf-8 encoding on Windows console if supported
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("================================================================================")
    print("   SolutionBridge - Product Integration & ML Troubleshooting Demo   ")
    print("================================================================================")
    print(f"Target Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # 1. Initialize DB schema
    print("\n[Step 1/5] Initializing database schema...")
    init_db()

    # 2. Seed Baseline Data
    print("[Step 2/5] Seeding deterministic baseline datasets...")
    db = SessionLocal()
    try:
        counts = seed_database(db)
        print(f"  [OK] Seeded: {counts['customers']} customers, {counts['products']} products, {counts['orders']} orders, {counts['logs']} logs, {counts['historical_incidents']} historical postmortems")

        # 3. Ensure ML models
        print("\n[Step 3/5] Verifying ML model pipelines...")
        ensure_ml_artifacts()
        print("  [OK] ML models verified: Isolation Forest, TF-IDF + Logistic Regression, FAISS Index")

        # 4. Execute Scenarios A to E
        print("\n[Step 4/5] Executing 5 Controlled Fault Scenarios...")
        simulator = FailureSimulator(db)
        incident_service = IncidentService(db)

        scenarios_to_run = [
            ("Scenario A (Database Timeout)", "database_timeout", 1),
            ("Scenario B (Invalid Authentication)", "invalid_authentication", 2),
            ("Scenario C (Performance Degradation)", "slow_sql_query", 1),
            ("Scenario D (Infrastructure Saturation)", "503_service_unavailable", 3),
            ("Scenario E (Data Inconsistency / Rollback)", "missing_order_record", 2),
        ]

        scenario_reports = []

        for name, sc_key, cid in scenarios_to_run:
            print(f"\n  ------------------------------------------------------------")
            print(f"  Running: {name} (Customer #{cid})")
            sim_res = simulator.trigger_scenario(sc_key, customer_id=cid)
            req_id = sim_res["request_id"]
            print(f"  -> Injected HTTP {sim_res['http_status']} ({sim_res['error_code']}) with Request ID: {req_id}")

            # Analyze through multi-source engine
            analysis = incident_service.analyze_request(req_id)
            print(f"  -> ML & Engine Diagnosis: Category = [{analysis['category']}], Confidence = {analysis['confidence']*100:.1f}%")
            print(f"  -> Probable Root Cause  : {analysis['predicted_root_cause']}")
            print(f"  -> Deterministic Facts  :")
            for ev in analysis["deterministic_evidence"][:3]:
                print(f"      * {ev}")
            print(f"  -> Top Remediation Step : {analysis['recommended_actions'][0]['action']}")

            scenario_reports.append({
                "scenario": name,
                "request_id": req_id,
                "http_status": sim_res["http_status"],
                "diagnosed_category": analysis["category"],
                "confidence": f"{analysis['confidence']*100:.1f}%",
                "probable_cause": analysis["predicted_root_cause"][:65] + "...",
                "top_action": analysis["recommended_actions"][0]["action"],
            })

        # 5. Output Summary Table
        print("\n[Step 5/5] Demonstration Results Summary Table:")
        print("==========================================================================================================================")
        print(f"{'Scenario':<38} | {'Status':<6} | {'Diagnosed Category':<20} | {'Conf':<6} | {'Top Action':<35}")
        print("--------------------------------------------------------------------------------------------------------------------------")
        for r in scenario_reports:
            print(f"{r['scenario']:<38} | {r['http_status']:<6} | {r['diagnosed_category']:<20} | {r['confidence']:<6} | {r['top_action']:<35}")
        print("==========================================================================================================================\n")
        print("All 5 scenarios diagnosed successfully with combined API, SQL, Log, Metric, and ML evidence!")
        print("Ready for Streamlit dashboard display: python -m streamlit run dashboard/app.py")

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
