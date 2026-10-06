from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_admin
from app.database.session import get_db
from app.models.orm import User, FleetDataset, MlModel
from app.services.ml_registry import registry, banner, TrainingBusy

router = APIRouter(prefix="/ml", tags=["ml"])

class TrainIn(BaseModel):
    dataset_id: int | None = None               # default: newest uploaded dataset, else the simulated one
    kind: Literal["gbt", "ridge"] = "gbt"

def _summary(rec: MlModel, ds: FleetDataset):
    return dict(model_id=rec.id, kind=rec.kind, data_source=rec.data_source, banner=banner(rec.data_source, ds.name, ds.n_rows),
                dataset=dict(id=ds.id, name=ds.name, n_rows=ds.n_rows, n_vehicles=ds.n_vehicles),
                trained_at=rec.trained_at, n_train=rec.n_train, n_test=rec.n_test)

@router.get("/status")
def status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, rec = registry.active(db)
    if rec is None or m is None:
        return dict(trained=False, training_in_progress=registry.training, active_model=None,
                    banner="No ML model is active; SOH is physics-only.")
    ds = db.get(FleetDataset, rec.dataset_id); s = _summary(rec, ds)
    return dict(trained=True, training_in_progress=registry.training, active_model=s, banner=s["banner"])

@router.get("/metrics")
def metrics(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, rec = registry.active(db)
    if rec is None: raise HTTPException(404, "No active ML model")
    s = rec.metrics
    return dict(**_summary(rec, db.get(FleetDataset, rec.dataset_id)),
                mae_physics=s["maeP"], mae_hybrid=s["maeH"], rmse_physics=s["rmseP"], rmse_hybrid=s["rmseH"],
                n_vehicles_train=s["nVehTrain"], n_vehicles_test=s["nVehTest"],
                split="by vehicle_id: test vehicles are never seen in training",
                feature_importance=rec.feature_importance, validation=rec.validation)

@router.get("/models", summary="Training history")
def models(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [dict(model_id=r.id, kind=r.kind, data_source=r.data_source, dataset_id=r.dataset_id, trained_at=r.trained_at,
                 is_active=r.is_active, mae_hybrid=r.metrics["maeH"], rmse_hybrid=r.metrics["rmseH"])
            for r in db.scalars(select(MlModel).order_by(MlModel.id.desc()))]

@router.post("/train", status_code=201, summary="Train on a stored dataset and activate the new model (admin)")
def train(body: TrainIn = TrainIn(), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    ds_id = body.dataset_id
    if ds_id is None:
        ds_id = db.scalar(select(FleetDataset.id).order_by((FleetDataset.source == "uploaded").desc(), FleetDataset.id.desc()).limit(1))
    if ds_id is None: raise HTTPException(404, "No dataset available")
    try: rec = registry.train_from_dataset(db, ds_id, body.kind)
    except TrainingBusy as e: raise HTTPException(409, str(e))
    except LookupError as e: raise HTTPException(404, str(e))
    except ValueError as e: raise HTTPException(422, str(e))
    return _summary(rec, db.get(FleetDataset, rec.dataset_id))
