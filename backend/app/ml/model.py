"""Residual ML layer: learns (measured SOH - physics SOH). Hybrid = physics + clip(residual, +/-10).
GBT primary (MATLAB LSBoost: 150 cycles, lr .05, 15 splits, min leaf 5); quadratic ridge fallback (lambda 5)."""
from dataclasses import dataclass, field
import datetime as dt
import numpy as np, pandas as pd, joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from app.physics.constants import CHEM_NAMES, FEATURE_NAMES
from app.physics.model import VehicleParams, simulate

MIN_ROWS = 40
REQUIRED = ['chem','cooling','cap_kWh','ac_kW','dc_kW','whkm','age_yr','odo_km','km_per_yr',
            'Tamb_C','fast_pct','charge_limit','min_soc','soh_pct']

def feature_vec(p: VehicleParams, R) -> np.ndarray:
    return np.array([*(float(p.chem == c) for c in CHEM_NAMES), np.log(p.cap), R.Cac, R.Cdc, p.age,
                     R.efc0, R.annual, p.Tamb, R.Tcell, p.fs, p.hi, p.lo, R.dod, R.soc, R.fCw, R.fS, R.soh[0]])

def row_to_params(r) -> VehicleParams:
    name = str(r['chem']).strip().upper()
    if name not in CHEM_NAMES: raise ValueError(f'Unknown chemistry "{r["chem"]}" (use LFP, NMC, NCA or LTO).')
    return VehicleParams(name, int(min(max(round(r['cooling']), 1), 3)), r['cap_kWh'], r['ac_kW'], r['dc_kW'],
        r['whkm'], r['odo_km'], r['km_per_yr'], max(r['age_yr'], 0.05), r['Tamb_C'], r['fast_pct'],
        r['charge_limit'], min(r['min_soc'], r['charge_limit'] - 10))

@dataclass
class ResidualModel:
    kind: str = ""; obj: object = None; mu: np.ndarray = None; sg: np.ndarray = None
    imp: np.ndarray = None; stats: dict = field(default_factory=dict); label: str = ""
    val: dict = field(default_factory=dict); trained_at: str = ""
    data_source: str = ""; model_id: int | None = None   # set by the registry (simulated | uploaded)

    def predict_resid(self, X):
        X = np.atleast_2d(X)
        if self.kind == "gradient-boosted trees": y = self.obj.predict(X)
        else:
            Z = (X - self.mu) / self.sg; y = self.obj.predict(np.hstack([Z, Z ** 2]))
        return np.clip(y, -10, 10)           # limit the correction to +/-10 SOH points

def fit_residual(X, y, kind="gbt") -> ResidualModel:
    M = ResidualModel()
    if kind == "gbt":
        try:
            M.kind = "gradient-boosted trees"
            M.obj = GradientBoostingRegressor(n_estimators=150, learning_rate=.05, max_leaf_nodes=16,
                                              min_samples_leaf=5, random_state=0).fit(X, y)
            imp = M.obj.feature_importances_
        except Exception: kind = "ridge"
    if kind != "gbt":
        M.kind = "ridge regression (quadratic)"
        M.mu = X.mean(0); M.sg = X.std(0, ddof=1); M.sg[M.sg < 1e-9] = 1
        Z = (X - M.mu) / M.sg
        M.obj = Ridge(alpha=5).fit(np.hstack([Z, Z ** 2]), y)
        n = X.shape[1]; imp = np.abs(M.obj.coef_[:n]) + np.abs(M.obj.coef_[n:])
    M.imp = imp / max(imp.sum(), 1e-12)
    return M

def validate_frame(df: pd.DataFrame):
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss: raise ValueError("Missing columns: " + ", ".join(miss))
    if len(df) < MIN_ROWS: raise ValueError(f"Need at least {MIN_ROWS} rows of fleet data (found {len(df)}).")

def train_on_dataframe(df: pd.DataFrame, label: str, kind="gbt") -> ResidualModel:
    validate_frame(df); n = len(df)
    X = np.zeros((n, len(FEATURE_NAMES))); phys = np.zeros(n)
    for i in range(n):
        p = row_to_params(df.iloc[i]); R = simulate(p); X[i] = feature_vec(p, R); phys[i] = R.soh[0]
    y = df['soh_pct'].to_numpy(float) - phys                 # what the physics model misses
    ids = df['vehicle_id'].to_numpy() if 'vehicle_id' in df else np.arange(n)
    u = np.random.default_rng(1).permutation(np.unique(ids))
    test = np.isin(ids, u[:max(1, round(.25 * len(u)))])      # split BY VEHICLE, never by row
    Mt = fit_residual(X[~test], y[~test], kind)
    yt = df['soh_pct'].to_numpy(float)[test]
    hyb = np.clip(phys[test] + Mt.predict_resid(X[test]), 30, 100)
    st = dict(maeP=float(np.mean(abs(yt - phys[test]))), rmseP=float(np.sqrt(np.mean((yt - phys[test]) ** 2))),
              maeH=float(np.mean(abs(yt - hyb))), rmseH=float(np.sqrt(np.mean((yt - hyb) ** 2))),
              nTrain=int((~test).sum()), nTest=int(test.sum()),
              nVehTrain=int(len(set(ids[~test]))), nVehTest=int(len(set(ids[test]))))
    M = fit_residual(X, y, kind)                              # final model uses all data
    M.stats, M.label = st, label
    M.val = dict(measured=yt.tolist(), physics=phys[test].tolist(), hybrid=hyb.tolist())
    M.trained_at = dt.datetime.now(dt.timezone.utc).isoformat()
    return M

def save(M, path): joblib.dump(M, path)
def load(path): return joblib.load(path)
