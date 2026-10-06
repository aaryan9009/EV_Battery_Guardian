"""SIMULATED fleet (MATLAB `makeFleet`). True SOH = physics + effects physics lacks
(heat x fast-charge compounding, cold fast-charging, different calendar exponent,
vehicle spread, sensor noise). NOT real data."""
import numpy as np, pandas as pd
from app.physics.constants import PRESET_VALS, CHEM_NAMES
from app.physics.model import VehicleParams, simulate, knee

COLUMNS = ['vehicle_id','chem','cooling','cap_kWh','ac_kW','dc_kW','whkm','age_yr','odo_km',
           'km_per_yr','Tamb_C','fast_pct','charge_limit','min_soc','soh_pct']

def make_fleet(n_veh: int = 150, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed); rows = []
    for v in range(1, n_veh + 1):
        q = PRESET_VALS[rng.integers(len(PRESET_VALS))]
        ci = q[0]
        if rng.random() > 0.7: ci = int(rng.integers(1, 5))
        cap = float(np.clip(q[2] * np.exp(.25 * rng.standard_normal()), .5, 900))
        ac = q[3] * np.exp(.2 * rng.standard_normal()); dc = q[4] * np.exp(.2 * rng.standard_normal())
        wh = q[5] * np.exp(.15 * rng.standard_normal()); ak = q[8] * np.exp(.3 * rng.standard_normal())
        Ta = float(np.clip(q[9] + 4 * rng.standard_normal(), -5, 45))
        fs = float(np.clip(q[10] + 15 * rng.standard_normal(), 0, 100))
        hi = float(np.clip(q[11] + 5 * rng.standard_normal(), 60, 100))
        lo = min(float(min(max(q[12] + 5 * rng.standard_normal(), 3), 40)), hi - 20)
        mc, my = np.exp(.10 * rng.standard_normal()), np.exp(.12 * rng.standard_normal())
        for a in np.sort(0.3 + 7.7 * rng.random(4)):
            odo = a * ak * (1 + .1 * rng.standard_normal())
            p = VehicleParams(CHEM_NAMES[ci - 1], q[1], cap, ac, dc, wh, odo, ak, a, Ta, fs, hi, lo)
            R = simulate(p)
            cal_rate = R.cal[0] / np.sqrt(a); cyc_rate = R.cyc[0] / max(R.efc0, 1e-9)
            h = 1 + 0.6 * max(R.Tcell - 35, 0) / 10 * max(R.fCw - 1.2, 0) / 0.5   # heat x fast-charge
            if Ta < 8 and fs > 30: h *= 1.3                                        # cold fast charging
            Lr = mc * cal_rate * a ** 0.6 + my * h * cyc_rate * R.efc0
            soh = float(np.clip(100 * (1 - knee(Lr)) + .5 * rng.standard_normal(), 30, 100))
            rows.append([v, CHEM_NAMES[ci - 1], q[1], cap, ac, dc, wh, a, odo, ak, Ta, fs, hi, lo, soh])
    return pd.DataFrame(rows, columns=COLUMNS)
