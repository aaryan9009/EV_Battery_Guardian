from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.physics.constants import PRESET_NAMES, PRESET_VALS, PRESET_KEYS, CHEMS, COOL_NAMES
from app.schemas.vehicle import VehicleIn
from app.services.ml_registry import registry

router = APIRouter(tags=["meta"])
COOL = {1: "liquid", 2: "air", 3: "passive"}

@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1")); m, rec = registry.active(db)
    return dict(status="ok", database="ok", ml_model_active=m is not None)

@router.get("/meta", summary="Presets, chemistries and field limits for the UI (single source of truth)")
def meta():
    names = ["chem", "cooling_type", "battery_capacity_kwh", "ac_charge_power_kw", "dc_charge_power_kw", "energy_use_wh_km",
             "vehicle_age_years", "odometer_km", "distance_per_year_km", "ambient_temperature_c", "dc_fast_pct", "daily_charge_limit", "min_soc"]
    presets = []
    for n, vals in zip(PRESET_NAMES[:-1], PRESET_VALS):
        d = dict(zip(PRESET_KEYS, vals))
        presets.append(dict(name=n, values=dict(zip(names, [list(CHEMS)[d["chem"] - 1], COOL[d["cool"]], d["cap"], d["ac"], d["dc"], d["whkm"],
                                                           d["age"], d["odo"], d["akm"], d["Tamb"], d["fs"], d["hi"], d["lo"]]))))
    presets.append(dict(name=PRESET_NAMES[-1], values=None))
    limits = {k: {kk: vv for kk, vv in (("min", next((m.ge for m in f.metadata if hasattr(m, "ge")), None)),
                                        ("max", next((m.le for m in f.metadata if hasattr(m, "le")), None))) if vv is not None}
              for k, f in VehicleIn.model_fields.items() if f.metadata}
    return dict(presets=presets, limits=limits, cooling=[dict(value=COOL[i + 1], label=l) for i, l in enumerate(COOL_NAMES)],
                chemistries=[dict(name=c.name, warn_temp_c=c.tWarn, typical_max_dc_c_rate=c.maxC) for c in CHEMS.values()])
