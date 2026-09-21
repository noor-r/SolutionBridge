"""Demo scenario simulation routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.schemas import DemoScenarioRequest, DemoScenarioResponse
from app.services.failure_simulator import FailureSimulator

router = APIRouter(prefix="/api/v1/demo", tags=["Demo Simulator"])


@router.get("/scenarios")
def list_scenarios():
    """List all supported failure scenarios."""
    return {"scenarios": FailureSimulator.SCENARIOS}


@router.post("/scenario", response_model=DemoScenarioResponse)
def run_demo_scenario(payload: DemoScenarioRequest, db: Session = Depends(get_db)):
    """Trigger a controlled failure scenario to demonstrate the Product Solutions Engineer investigation workflow."""
    simulator = FailureSimulator(db)
    try:
        result = simulator.trigger_scenario(
            scenario=payload.scenario,
            customer_id=payload.customer_id or 1,
        )
        return DemoScenarioResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
