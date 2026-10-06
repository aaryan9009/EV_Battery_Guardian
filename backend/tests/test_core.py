import numpy as np, tempfile, os
from app.physics.constants import preset_as_dict, FEATURE_NAMES
from app.physics.model import VehicleParams, simulate, anchor_scale, life_to_80
from app.ml.fleet import make_fleet
from app.ml.model import train_on_dataframe, feature_vec, save, load

def car(): return VehicleParams(**preset_as_dict(2))

def test_physics_car():
    R = simulate(car()); Ro = simulate(car(), True, R.hist)
    assert 80 < R.soh[0] < 100 and R.soh[-1] < R.soh[0]
    assert Ro.soh[-1] > R.soh[-1]                      # optimized habits age slower
    assert life_to_80(Ro, 15)[0] >= life_to_80(R, 15)[0]
    print("car: SOH0 %.2f, SOH15 %.2f, EFC %.0f, Tcell %.1f, life %s, opt life %s" % (
        R.soh[0], R.soh[-1], R.efc0, R.Tcell, life_to_80(R), life_to_80(Ro, 15)))

def test_anchor_roundtrip():
    p = car(); R0 = simulate(p)
    for meas in (95, 90, 85, 75):
        s, _ = anchor_scale(meas, R0.baseNow); p.scale = s
        got = simulate(p).soh[0]
        if 0.2 < s < 5: assert abs(got - meas) < 1e-6, (meas, got)

def test_fleet_and_ml():
    df = make_fleet(150); assert len(df) == 600 and df.vehicle_id.nunique() == 150
    M = train_on_dataframe(df, "simulated fleet"); s = M.stats
    print(s); assert s["nTest"] > 0 and s["rmseH"] < s["rmseP"]
    assert len(M.imp) == len(FEATURE_NAMES) and abs(M.imp.sum() - 1) < 1e-9
    print(sorted(zip(np.round(M.imp, 3), FEATURE_NAMES), reverse=True)[:5])
    with tempfile.TemporaryDirectory() as d:
        save(M, os.path.join(d, "m.joblib")); M2 = load(os.path.join(d, "m.joblib"))
        p = car(); x = feature_vec(p, simulate(p))
        assert abs(M.predict_resid(x)[0]) <= 10 and M2.predict_resid(x)[0] == M.predict_resid(x)[0]

def test_ridge_fallback():
    M = train_on_dataframe(make_fleet(60), "sim", kind="ridge"); print(M.kind, M.stats); assert "ridge" in M.kind
