"""Glue between analysis results and the database (used by the API layer in Stage 5)."""
from sqlalchemy.orm import Session
from app.models.orm import SohPrediction

def save_prediction(db: Session, vehicle_id: int, inputs: dict, result: dict, model_id: int | None = None) -> SohPrediction:
    row = SohPrediction(
        vehicle_id=vehicle_id, model_id=model_id, soh_source=result["soh_source"], physics_soh=result["physics_soh"],
        ml_correction=result["ml_correction"], hybrid_soh=result["current_soh"], anchor_scale=result["anchor_scale"],
        risk_level=result["risk"]["level"], risk_score=result["risk"]["score"],
        life_remaining_years=result["life_years"], life_optimized_years=result["life_optimized_years"],
        life_gained_years=result["life_gained_years"], efc=result["efc"], inputs=inputs, result=result)
    db.add(row); db.flush()
    return row
