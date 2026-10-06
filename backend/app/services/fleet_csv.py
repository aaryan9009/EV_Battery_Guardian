"""Fleet CSV validation. Nothing is accepted silently: every bad cell is reported with row/column/value."""
import io, math
import pandas as pd
from app.ml.model import MIN_ROWS
from app.core.config import get_settings

MIN_VEHICLES = 8            # so the 25 % vehicle hold-out has >= 2 unseen test vehicles
MAX_ROWS = 100_000
REQUIRED = ['vehicle_id','chem','cooling','cap_kWh','ac_kW','dc_kW','whkm','age_yr','odo_km','km_per_yr',
            'Tamb_C','fast_pct','charge_limit','min_soc','soh_pct']
LIMITS = {'cap_kWh': (0.3, 1500), 'ac_kW': (0.1, 1500), 'dc_kW': (0, 1500), 'whkm': (5, 5000), 'age_yr': (0, 25),
          'odo_km': (0, 3e6), 'km_per_yr': (0, 5e5), 'Tamb_C': (-30, 60), 'fast_pct': (0, 100),
          'charge_limit': (50, 100), 'min_soc': (0, 60), 'soh_pct': (30, 100)}
DB_COL = {'cap_kWh': 'cap_kwh', 'ac_kW': 'ac_kw', 'dc_kW': 'dc_kw', 'Tamb_C': 'tamb_c'}   # CSV name -> DB column
COOL_NAMES = {'liquid': 1, 'air': 2, 'passive': 3}
CHEMS = {'LFP', 'NMC', 'NCA', 'LTO'}

class FleetCSVError(ValueError):
    """File-level problem (unreadable, missing columns, too few rows...)."""
    def __init__(self, message, errors=None): super().__init__(message); self.errors = errors or []

def _num(raw, lo, hi):
    try: v = float(raw)
    except (TypeError, ValueError): return None, "not a number"
    if math.isnan(v) or math.isinf(v): return None, "not a finite number"
    if not lo <= v <= hi: return None, f"out of range [{lo:g}, {hi:g}]"
    return v, None

def parse(raw: bytes) -> dict:
    try: df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False, skipinitialspace=True)
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
        raise FleetCSVError(f"Could not read file as CSV: {e}")
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing: raise FleetCSVError("Missing required columns: " + ", ".join(missing))
    if len(df) > MAX_ROWS: raise FleetCSVError(f"Too many rows ({len(df)}); limit is {MAX_ROWS}.")
    rows, errors, adjusted = [], [], 0
    for i, r in enumerate(df.to_dict("records")):
        line, bad = i + 2, False                     # +2: header is line 1
        def err(col, msg):
            nonlocal bad; bad = True; errors.append(dict(row=line, column=col, value=str(r.get(col, ""))[:40], message=msg))
        out = {}
        vid = str(r['vehicle_id']).strip()
        if not vid: err('vehicle_id', "empty"); 
        out['vehicle_ref'] = vid[:64]
        chem = str(r['chem']).strip().upper()
        if chem not in CHEMS: err('chem', "must be LFP, NMC, NCA or LTO")
        out['chem'] = chem
        c = str(r['cooling']).strip().lower()
        if c in COOL_NAMES: out['cooling'] = COOL_NAMES[c]
        else:
            v, _ = _num(c, 1, 3)
            if v is None or v != int(v): err('cooling', "must be 1 (liquid), 2 (air), 3 (passive)"); out['cooling'] = 0
            else: out['cooling'] = int(v)
        for col, (lo, hi) in LIMITS.items():
            v, m = _num(r[col], lo, hi)
            if m: err(col, m)
            out[DB_COL.get(col, col)] = v
        if not bad and out['min_soc'] > out['charge_limit'] - 10: adjusted += 1   # model clamps this, as MATLAB does
        if not bad: rows.append(out)
    n_veh = len({r['vehicle_ref'] for r in rows})
    warnings = [f"{adjusted} row(s) have min_soc above charge_limit-10; the model will clamp it to charge_limit-10."] if adjusted else []
    extra = [c for c in df.columns if c not in REQUIRED]
    if extra: warnings.append("Ignored extra columns: " + ", ".join(extra))
    return dict(rows=rows, errors=errors, n_total=len(df), n_vehicles=n_veh, warnings=warnings)

def check_trainable(rows: list, n_vehicles: int):
    if len(rows) < MIN_ROWS: raise FleetCSVError(f"Need at least {MIN_ROWS} valid rows to train (found {len(rows)}).")
    if n_vehicles < MIN_VEHICLES:
        raise FleetCSVError(f"Need at least {MIN_VEHICLES} distinct vehicle_id values so held-out test vehicles are unseen (found {n_vehicles}).")
