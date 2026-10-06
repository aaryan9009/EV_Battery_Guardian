import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_admin
from app.core.config import get_settings
from app.database.session import get_db
from app.ml.fleet import make_fleet
from app.models.orm import User, FleetDataset, FleetTrainingData, MlModel
from app.services import fleet_csv
from app.services.ml_registry import insert_rows

router = APIRouter(prefix="/fleet", tags=["fleet"])
def _ds(d: FleetDataset): return dict(id=d.id, name=d.name, source=d.source, n_rows=d.n_rows, n_vehicles=d.n_vehicles, created_at=d.created_at)

@router.post("/upload", status_code=201, summary="Validate and store a fleet/BMS CSV (admin)")
def upload(file: UploadFile = File(...), name: str | None = Form(None),
           skip_invalid: bool = Query(False, description="Import valid rows and report invalid ones, instead of rejecting the whole file"),
           user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not (file.filename or "").lower().endswith(".csv"): raise HTTPException(415, "Please upload a .csv file")
    limit = get_settings().max_upload_mb * 1024 * 1024
    raw = file.file.read(limit + 1)
    if len(raw) > limit: raise HTTPException(413, f"File larger than {get_settings().max_upload_mb} MB")
    try:
        res = fleet_csv.parse(raw)
        if res["errors"] and not skip_invalid:
            raise fleet_csv.FleetCSVError(f"{len(res['errors'])} invalid value(s) found. Nothing was imported. Fix the file, or re-upload with skip_invalid=true.", res["errors"])
        fleet_csv.check_trainable(res["rows"], res["n_vehicles"])
    except fleet_csv.FleetCSVError as e:
        raise HTTPException(422, detail=dict(message=str(e), n_errors=len(e.errors), errors=e.errors[:100]))
    ds = FleetDataset(name=(name or file.filename)[:255], source="uploaded", n_rows=len(res["rows"]), n_vehicles=res["n_vehicles"], uploaded_by=user.id)
    db.add(ds); db.flush(); insert_rows(db, ds.id, res["rows"]); db.commit()
    skipped = len({e["row"] for e in res["errors"]})
    return dict(dataset=_ds(ds), rows_in_file=res["n_total"], rows_imported=len(res["rows"]), rows_skipped=skipped,
                n_errors=len(res["errors"]), errors=res["errors"][:100], warnings=res["warnings"])

@router.get("/datasets")
def datasets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_ds(d) for d in db.scalars(select(FleetDataset).order_by(FleetDataset.id.desc()))]

@router.get("/datasets/{dataset_id}/rows")
def rows(dataset_id: int, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
         user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.get(FleetDataset, dataset_id)
    if d is None: raise HTTPException(404, "Dataset not found")
    cols = [c for c in FleetTrainingData.__table__.columns if c.name not in ("id", "dataset_id")]
    q = db.execute(select(*cols).where(FleetTrainingData.dataset_id == dataset_id).order_by(FleetTrainingData.id).limit(limit).offset(offset))
    return dict(dataset=_ds(d), total=d.n_rows, rows=[dict(r._mapping) for r in q])

@router.delete("/datasets/{dataset_id}", status_code=204, summary="Delete a dataset (admin); refused while a model was trained on it")
def delete_dataset(dataset_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    d = db.get(FleetDataset, dataset_id)
    if d is None: raise HTTPException(404, "Dataset not found")
    if db.scalar(select(func.count()).select_from(MlModel).where(MlModel.dataset_id == d.id)):
        raise HTTPException(409, "A trained model references this dataset")
    db.delete(d); db.commit()

@router.get("/template", summary="Sample CSV (SYNTHETIC data; shows the required columns)")
def template():
    buf = io.StringIO(); make_fleet(12, seed=11).round(3).to_csv(buf, index=False)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="fleet_template_SYNTHETIC.csv"'})
