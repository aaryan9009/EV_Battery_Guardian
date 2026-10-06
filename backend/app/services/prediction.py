"""Prediction service: SOH source priority, anchoring, life-to-80%, scenarios, risk, recommendations.
SOH source priority (as in the MATLAB app):  measured SOH  >  physics + ML correction  >  physics only."""
from dataclasses import replace
import numpy as np
from app.physics.constants import CHEMS
from app.physics.model import VehicleParams, simulate, anchor_scale, life_to_80
from app.ml.model import feature_vec
from . import risk as risk_svc, recommendations as rec_svc

SRC_MEASURED, SRC_ML, SRC_PHYSICS = "measured", "physics_ml", "physics_only"
SRC_LABEL = {SRC_MEASURED: "Measured SOH", SRC_ML: "Physics + ML correction", SRC_PHYSICS: "Physics only"}

def analyze(p: VehicleParams, *, calibrate=False, measured_soh=None, use_ml=True, model=None) -> dict:
    c = CHEMS[p.chem]
    R0 = simulate(p)                                        # generic (un-anchored) physics
    anchor_to, source, ml_corr = None, SRC_PHYSICS, None
    if calibrate and measured_soh is not None:
        anchor_to, source = float(measured_soh), SRC_MEASURED
    elif use_ml and model is not None:
        ml_corr = float(model.predict_resid(feature_vec(p, R0))[0])
        anchor_to, source = float(np.clip(R0.soh[0] + ml_corr, 40, 100)), SRC_ML
    warnings, scale = [], 1.0
    if anchor_to is not None:
        scale, w = anchor_scale(anchor_to, R0.baseNow)
        if w.startswith("Anchoring skipped"):               # nothing to anchor on -> falls back to physics
            source, ml_corr = SRC_PHYSICS, None
        if w: warnings.append(w)
    if anchor_to is None and use_ml and model is None:
        warnings.append("No trained ML model is active; showing physics-only SOH.")
    pa = replace(p, scale=scale)
    R = simulate(pa)                                        # current habits, anchored
    Ro = simulate(pa, True, R.hist)                         # optimized habits, same history
    cur = float(R.soh[0])
    life_c, reached_c = life_to_80(R)
    life_o, reached_o = life_to_80(Ro)
    gain = life_o - life_c
    rk = risk_svc.assess(c, R.Tcell, R.fCw, R.fS, cur)
    recs, cal_share = rec_svc.build(pa, c, R, gain, not reached_o)
    warnings = rec_svc.input_warnings(pa, c, R) + warnings
    i5 = int(np.argmax(R.yrs >= 5))
    st = getattr(model, "stats", None) if model is not None else None
    f = lambda a: [round(float(v), 4) for v in a]
    return dict(
        soh_source=source, soh_source_label=SRC_LABEL[source], current_soh=round(cur, 2),
        physics_soh=round(float(R0.soh[0]), 2), ml_correction=None if ml_corr is None else round(ml_corr, 2),
        soh_error_band=round(st["rmseH"], 2) if (source == SRC_ML and st) else None,
        anchor_scale=round(scale, 3), efc=round(R.efc0, 1), efc_per_year=round(R.annual, 1),
        life_years=round(life_c, 2), life_reached=reached_c, life_km=round(life_c * p.akm),
        life_optimized_years=round(life_o, 2), life_optimized_reached=reached_o, life_gained_years=round(gain, 2),
        calendar_share=round(cal_share, 3), risk=rk, recommendations=recs, warnings=warnings,
        details=dict(ac_c_rate=round(R.Cac, 3), dc_c_rate_avg=round(R.Cdc, 3), cell_temp_c=round(R.Tcell, 1),
                     resting_soc=round(R.soc, 1), dod=round(R.dod, 1), charging_stress=round(R.fCw, 3), soc_stress=round(R.fS, 3)),
        forecast=dict(years=f(R.yrs), current=f(R.soh), optimized=f(Ro.soh), reference=80),
        causes=dict(labels=["Today", "In 5 years"], calendar=[round(100 * R.cal[0], 3), round(100 * R.cal[i5], 3)],
                    cycling=[round(100 * R.cyc[0], 3), round(100 * R.cyc[i5], 3)]),
        ml_model=None if model is None else dict(kind=model.kind, label=model.label, stats=model.stats,
                                                 data_source=model.data_source or None, model_id=model.model_id))
