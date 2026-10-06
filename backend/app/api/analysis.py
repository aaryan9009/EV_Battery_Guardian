"""Analysis endpoints: thin wrappers over services.prediction.analyze (no calculations here)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, owned_vehicle
from app.database.session import get_db
from app.models.orm import User, Vehicle, BatteryMeasurement, SohPrediction
from app.physics.model import VehicleParams
from app.schemas.analysis import AnalysisInput, AnalyzeOptions, AnalysisResult, COOL_CODE
from app.services.ml_registry import registry
from app.services.persistence import save_prediction
from app.services.prediction import analyze

router = APIRouter(tags=["analysis"])

def _params(v: Vehicle) -> VehicleParams:
    return VehicleParams(v.battery_chemistry, COOL_CODE[v.cooling_type], v.battery_capacity_kwh, v.ac_charge_power_kw,
                         v.dc_charge_power_kw, v.energy_use_wh_km, v.odometer_km, v.distance_per_year_km, v.vehicle_age_years,
                         v.ambient_temperature_c, v.dc_fast_pct, v.daily_charge_limit, v.min_soc)

@router.post("/vehicles/{vehicle_id}/analyze", response_model=AnalysisResult)
def analyze_vehicle(vehicle_id: int, opts: AnalyzeOptions = AnalyzeOptions(), user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = owned_vehicle(db, user, vehicle_id)
    measured = opts.measured_soh
    if opts.calibrate and measured is None:                       # fall back to the newest stored measurement
        measured = db.scalar(select(BatteryMeasurement.measured_soh).where(BatteryMeasurement.vehicle_id == v.id)
                             .order_by(BatteryMeasurement.measured_at.desc()).limit(1))
        if measured is None: raise HTTPException(422, "calibrate=true needs measured_soh or a stored measurement for this vehicle")
        if measured < 40: raise HTTPException(422, "Stored measurement is below 40 %, outside the calibration range")
    model, rec = registry.active(db) if opts.use_ml else (None, None)
    result = analyze(_params(v), calibrate=opts.calibrate, measured_soh=measured, use_ml=opts.use_ml, model=model)
    result.update(saved=False, prediction_id=None)
    if opts.save:
        row = save_prediction(db, v.id, {"vehicle_id": v.id, **opts.model_dump(), "measured_soh_used": measured},
                              result, model_id=rec.id if (rec and result["soh_source"] == "physics_ml") else None)
        db.commit(); result.update(saved=True, prediction_id=row.id)
    return result

@router.post("/analyze", response_model=AnalysisResult, summary="Stateless what-if analysis (nothing is stored)")
def analyze_preview(body: AnalysisInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    model, _ = registry.active(db) if body.use_ml else (None, None)
    r = analyze(body.to_params(), calibrate=body.calibrate, measured_soh=body.measured_soh, use_ml=body.use_ml, model=model)
    r.update(saved=False, prediction_id=None); return r

@router.get("/vehicles/{vehicle_id}/predictions", summary="Prediction history (summaries)")
def history(vehicle_id: int, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = owned_vehicle(db, user, vehicle_id)
    rows = db.scalars(select(SohPrediction).where(SohPrediction.vehicle_id == v.id)
                      .order_by(SohPrediction.predicted_at.desc(), SohPrediction.id.desc()).limit(limit).offset(offset)).all()
    return [dict(id=p.id, predicted_at=p.predicted_at, soh_source=p.soh_source, physics_soh=p.physics_soh, ml_correction=p.ml_correction,
                 current_soh=p.hybrid_soh, risk_level=p.risk_level, life_years=p.life_remaining_years,
                 life_gained_years=p.life_gained_years, efc=p.efc, model_id=p.model_id) for p in rows]

@router.get("/predictions/{prediction_id}", summary="One stored prediction with its full result and inputs")
def one_prediction(prediction_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(SohPrediction, prediction_id)
    if p is None: raise HTTPException(404, "Prediction not found")
    owned_vehicle(db, user, p.vehicle_id)
    return dict(id=p.id, predicted_at=p.predicted_at, inputs=p.inputs, result={**p.result, "prediction_id": p.id, "saved": True})
