"""Model lifecycle. fleet_training_data -> train (Stage-3 code) -> joblib -> ml_models -> active -> prediction service.
The API never re-implements training: it only loads rows, calls ml.model.train_on_dataframe, and registers the result."""
import logging, os, threading, uuid
import pandas as pd
from sqlalchemy import select, update, insert, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.config import get_settings
from app.ml import model as ml
from app.ml.fleet import make_fleet
from app.models.orm import FleetDataset, FleetTrainingData, MlModel
from app.physics.constants import FEATURE_NAMES
from app.services.fleet_csv import DB_COL

log = logging.getLogger("ev_guardian.ml")
CSV_FROM_DB = {v: k for k, v in DB_COL.items()} | {'vehicle_ref': 'vehicle_id'}
DATA_COLS = ['vehicle_ref','chem','cooling','cap_kwh','ac_kw','dc_kw','whkm','age_yr','odo_km','km_per_yr','tamb_c','fast_pct','charge_limit','min_soc','soh_pct']

class TrainingBusy(RuntimeError): pass

def banner(source: str, dataset_name: str, n_rows: int) -> str:
    if source == "simulated": return "ML model currently trained on simulated fleet data."
    return f'ML model trained on uploaded fleet data: "{dataset_name}" ({n_rows} rows).'

def insert_rows(db: Session, dataset_id: int, rows: list[dict]):
    for i in range(0, len(rows), 5000):
        db.execute(insert(FleetTrainingData), [{**r, "dataset_id": dataset_id} for r in rows[i:i + 5000]])

class MlRegistry:
    def __init__(self):
        self._model = None; self._model_id = None; self._lock = threading.Lock()
    @property
    def training(self) -> bool: return self._lock.locked()

    def active(self, db: Session):
        """(model, record). Compares the DB's active id with the cached one, so several workers stay in sync."""
        rec = db.scalar(select(MlModel).where(MlModel.is_active))
        if rec is None: return None, None
        if rec.id != self._model_id:
            try:
                m = ml.load(rec.file_path)           # joblib = pickle: only ever load files this app wrote itself
                m.data_source, m.model_id = rec.data_source, rec.id
                self._model, self._model_id = m, rec.id
            except Exception:
                log.exception("Could not load model file %s", rec.file_path); return None, rec
        return self._model, rec

    def train_from_dataset(self, db: Session, dataset_id: int, kind: str = "gbt") -> MlModel:
        if not self._lock.acquire(blocking=False): raise TrainingBusy("A training job is already running.")
        path = None
        try:
            ds = db.get(FleetDataset, dataset_id)
            if ds is None: raise LookupError("dataset not found")
            rows = db.execute(select(*[getattr(FleetTrainingData, c) for c in DATA_COLS])
                              .where(FleetTrainingData.dataset_id == dataset_id)).all()
            df = pd.DataFrame(rows, columns=DATA_COLS).rename(columns=CSV_FROM_DB)
            M = ml.train_on_dataframe(df, ds.name, kind)             # <- the Stage-3 implementation
            os.makedirs(get_settings().model_dir, exist_ok=True)
            path = os.path.join(get_settings().model_dir, f"model_{uuid.uuid4().hex[:10]}.joblib")
            ml.save(M, path)
            imp = sorted(({"feature": f, "importance": round(float(v), 6)} for f, v in zip(FEATURE_NAMES, M.imp)),
                         key=lambda d: -d["importance"])
            db.execute(update(MlModel).where(MlModel.is_active).values(is_active=False))
            rec = MlModel(dataset_id=ds.id, kind=M.kind, data_source=ds.source, n_train=M.stats["nTrain"], n_test=M.stats["nTest"],
                          metrics=M.stats, feature_importance=imp, validation=M.val, file_path=path, is_active=True)
            db.add(rec); db.commit()
            M.data_source, M.model_id = ds.source, rec.id
            self._model, self._model_id = M, rec.id
            log.info("Activated model %s (%s) trained on dataset %s", rec.id, M.kind, ds.name)
            return rec
        except Exception:
            db.rollback()
            if path and os.path.exists(path): os.remove(path)        # no orphan files for failed registrations
            raise
        finally:
            self._lock.release()

    def ensure_startup_model(self, db: Session):
        """Idempotent: an active model that loads is reused; otherwise train on the simulated fleet once."""
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(727001)"))   # serialize workers starting together
        m, rec = self.active(db)
        if m is not None: return rec
        ds = db.scalar(select(FleetDataset).where(FleetDataset.source == "simulated").order_by(FleetDataset.id).limit(1))
        if ds is None:
            df = make_fleet(150)
            ds = FleetDataset(name="Simulated fleet (150 vehicles)", source="simulated", n_rows=len(df), n_vehicles=150)
            db.add(ds); db.flush()
            rows = df.rename(columns={'vehicle_id': 'vehicle_ref', **DB_COL})
            recs = rows[DATA_COLS].astype({'vehicle_ref': str}).to_dict("records")
            insert_rows(db, ds.id, recs); db.flush()
        return self.train_from_dataset(db, ds.id, "gbt")

registry = MlRegistry()
