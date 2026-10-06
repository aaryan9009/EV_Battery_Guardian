"""Run against a real PostgreSQL that has been migrated:  DATABASE_URL=... alembic upgrade head && pytest tests/test_db.py"""
import os, pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, select, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.orm import *
from app.physics.constants import preset_as_dict
from app.physics.model import VehicleParams
from app.services.prediction import analyze
from app.services.persistence import save_prediction

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")

@pytest.fixture
def db():
    eng = create_engine(os.environ["DATABASE_URL"]); conn = eng.connect(); tx = conn.begin()
    s = Session(conn, join_transaction_mode="create_savepoint")
    yield s
    s.close(); tx.rollback(); conn.close()           # nothing persists between tests

def mk_vehicle(db):
    u = User(name="A", email=f"a{datetime.now().timestamp()}@x.io", password_hash="h"); db.add(u); db.flush()
    d = preset_as_dict(2)
    v = Vehicle(user_id=u.id, vehicle_name="Car", vehicle_type="Passenger car", battery_chemistry=d["chem"], cooling_type="liquid",
        battery_capacity_kwh=d["cap"], ac_charge_power_kw=d["ac"], dc_charge_power_kw=d["dc"], energy_use_wh_km=d["whkm"],
        odometer_km=d["odo"], distance_per_year_km=d["akm"], vehicle_age_years=d["age"], ambient_temperature_c=d["Tamb"],
        dc_fast_pct=d["fs"], daily_charge_limit=d["hi"], min_soc=d["lo"]); db.add(v); db.flush()
    return u, v

def test_full_chain_and_cascade(db):
    u, v = mk_vehicle(db)
    db.add(BatteryMeasurement(vehicle_id=v.id, measured_soh=91.2, measured_at=datetime.now(timezone.utc), soc=60))
    db.add(ChargingHistory(vehicle_id=v.id, charging_type="DC", charging_power_kw=100, start_soc=20, end_soc=80, charged_at=datetime.now(timezone.utc)))
    r = analyze(VehicleParams(**preset_as_dict(2)), use_ml=False)
    p = save_prediction(db, v.id, {"chem": "NMC"}, r)
    got = db.get(SohPrediction, p.id)
    assert got.result["forecast"]["reference"] == 80 and got.risk_level == r["risk"]["level"]
    db.delete(u); db.flush()                          # cascade: user -> vehicle -> children
    for T, col in ((Vehicle, Vehicle.id), (BatteryMeasurement, BatteryMeasurement.vehicle_id),
                   (ChargingHistory, ChargingHistory.vehicle_id), (SohPrediction, SohPrediction.vehicle_id)):
        assert db.scalar(select(func.count()).select_from(T).where(col == v.id)) == 0, T.__tablename__
    assert db.scalar(select(func.count()).select_from(SohPrediction).where(SohPrediction.id == p.id)) == 0

def test_constraints(db):
    u, v = mk_vehicle(db)
    for bad in (dict(battery_chemistry="XYZ"), dict(cooling_type="water"), dict(daily_charge_limit=120), dict(battery_capacity_kwh=0)):
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(Vehicle(**{**{c.name: getattr(v, c.name) for c in Vehicle.__table__.columns if c.name not in ("id", "created_at")}, **bad})); db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(User(name="dup", email=u.email, password_hash="h")); db.flush()

def test_fleet_and_single_active_model(db):
    db.execute(update(MlModel).values(is_active=False))                           # DB may already hold the API's active model (rolled back at the end)
    ds = FleetDataset(name="simulated", source="simulated", n_rows=600, n_vehicles=150); db.add(ds); db.flush()
    db.add(FleetTrainingData(dataset_id=ds.id, vehicle_ref="1", chem="NMC", cooling=1, cap_kwh=60, ac_kw=7, dc_kw=100, whkm=160,
        age_yr=3, odo_km=3e4, km_per_yr=1e4, tamb_c=30, fast_pct=20, charge_limit=90, min_soc=15, soh_pct=91)); db.flush()
    mk = lambda active: MlModel(dataset_id=ds.id, kind="gbt", data_source="simulated", n_train=1, n_test=1, metrics={}, feature_importance={},
                                validation={}, file_path="m.joblib", is_active=active)
    db.add(mk(True)); db.add(mk(False)); db.add(mk(False)); db.flush()          # many inactive OK
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(mk(True)); db.flush()                                              # second active rejected
    with pytest.raises(IntegrityError), db.begin_nested():
        db.delete(ds); db.flush()                                                 # RESTRICT: dataset in use by models
