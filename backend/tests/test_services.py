import pytest
from pydantic import ValidationError
from app.physics.constants import preset_as_dict, CHEMS
from app.physics.model import VehicleParams
from app.ml.fleet import make_fleet
from app.ml.model import train_on_dataframe
from app.services.prediction import analyze
from app.services import risk
from app.schemas.analysis import AnalysisInput

@pytest.fixture(scope="module")
def model(): return train_on_dataframe(make_fleet(150), "simulated fleet")
def preset(i, **kw): return VehicleParams(**{**preset_as_dict(i), **kw})
kinds = lambda r: [x["kind"] for x in r["recommendations"]]

def test_source_priority(model):
    a = analyze(preset(2), use_ml=False); assert a["soh_source"] == "physics_only" and a["ml_correction"] is None
    b = analyze(preset(2), model=model);  assert b["soh_source"] == "physics_ml" and abs(b["ml_correction"]) <= 10
    assert b["soh_error_band"] == round(model.stats["rmseH"], 2)
    c = analyze(preset(2), calibrate=True, measured_soh=88.5, model=model)   # measured beats ML
    assert c["soh_source"] == "measured" and abs(c["current_soh"] - 88.5) < 0.01 and c["ml_correction"] is None
    d = analyze(preset(2), use_ml=False, calibrate=False, measured_soh=70, model=model)  # ignored w/o calibrate flag
    assert d["soh_source"] != "measured"

def test_outputs_consistent(model):
    r = analyze(preset(3), model=model)
    assert r["life_optimized_years"] >= r["life_years"] and r["life_gained_years"] >= 0
    assert r["forecast"]["current"][0] == pytest.approx(r["current_soh"], abs=1e-2)
    assert len(r["forecast"]["years"]) == 61 and r["causes"]["calendar"][1] >= r["causes"]["calendar"][0]
    assert r["risk"]["level"] in ("LOW", "MODERATE", "HIGH")
    print(r["current_soh"], r["life_years"], r["life_gained_years"], r["risk"]["level"], kinds(r))

def test_risk_levels():
    c = CHEMS["NMC"]
    assert risk.assess(c, 28, 1.0, 1.0, 97)["level"] == "LOW"
    assert risk.assess(c, 36, 1.3, 1.3, 92)["level"] == "MODERATE"      # 1+1+1+1 = 4
    assert risk.assess(c, 42, 1.6, 1.0, 85)["level"] == "HIGH"          # 2+2+0+1 = 5
    assert risk.assess(CHEMS["LFP"], 42, 1.0, 1.0, 97)["factors"][0]["points"] == 1   # LFP tolerates more heat

def test_recommendations_are_dynamic():
    taxi = analyze(preset(3), use_ml=False); scooter = analyze(preset(0), use_ml=False)
    assert "fast_charging" in kinds(taxi) and "fast_charging" not in kinds(scooter)
    assert "charge_limit" in kinds(scooter)                              # NMC at 100 % limit
    rick = analyze(preset(1), use_ml=False)                              # LFP at 100 % limit
    assert "lfp_calibration" not in kinds(rick)                          # hi=100 -> no 'charge to 100 occasionally'
    lfp = analyze(preset(1, hi=90), use_ml=False); assert "lfp_calibration" in kinds(lfp)
    cool = analyze(preset(2, Tamb=10, fs=0), use_ml=False); assert "temperature" not in kinds(cool)

def test_validation_and_warnings():
    with pytest.raises(ValidationError): AnalysisInput(**{**dict(chem="NMC", cooling="air", cap_kwh=60, ac_kw=7, dc_kw=50, whkm=150,
        odo_km=0, km_per_year=1e4, age_years=1, ambient_c=30, fast_pct=10, charge_limit=80, min_soc=15), "calibrate": True})
    p = AnalysisInput(chem="NMC", cooling="liquid", cap_kwh=60, ac_kw=100, dc_kw=0, whkm=150, odo_km=0, km_per_year=1e4,
                      age_years=1, ambient_c=30, fast_pct=10, charge_limit=80, min_soc=15).to_params()
    r = analyze(p, use_ml=False); assert any("above 1C" in w for w in r["warnings"]) and any("DC power is 0" in w for w in r["warnings"])
