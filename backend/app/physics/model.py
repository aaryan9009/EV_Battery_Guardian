"""Physics aging model (MATLAB `simulate`, plus the anchoring block of `refresh`).
loss(t) = scale * [calendar + cycling] + late-life knee   (all as fractions of capacity)
"""
from dataclasses import dataclass
import numpy as np
from .constants import CHEMS, COOL_K

YEARS = np.arange(0, 15.0001, 0.25)           # forecast grid: 0..15 y in 0.25 y steps

@dataclass
class VehicleParams:
    chem: str; cool: int                      # cool: 1 liquid, 2 air, 3 passive
    cap: float; ac: float; dc: float; whkm: float
    odo: float; akm: float; age: float
    Tamb: float; fs: float; hi: float; lo: float   # fs, hi, lo in percent
    scale: float = 1.0                        # anchoring factor (1 = generic profile)
    def __post_init__(self):
        self.lo = min(self.lo, self.hi - 10)  # MATLAB: p.lo = min(p.lo, p.hi-10)

@dataclass
class SimResult:
    yrs: np.ndarray; soh: np.ndarray; cal: np.ndarray; cyc: np.ndarray
    hist: dict; baseNow: float; efc0: float; annual: float
    Tcell: float; Cac: float; Cdc: float; fCw: float; fS: float; dod: float; soc: float

def knee(Lr):
    """Late-life knee: accelerated fade once raw loss passes 12 %."""
    return Lr + 4 * np.maximum(Lr - 0.12, 0) ** 2

def simulate(p: VehicleParams, optimized: bool = False, hist: dict | None = None) -> SimResult:
    c = CHEMS[p.chem]
    fs, hi, lo, Tamb = p.fs / 100, p.hi, p.lo, p.Tamb
    if optimized:                              # "optimized habits" scenario
        fs = min(fs, 0.20); hi = min(hi, 80); lo = min(lo, hi - 20)
    Cac = p.ac / p.cap                         # AC C-rate
    Cdc = 0.7 * p.dc / p.cap                   # 0.7 = average over the CC-CV taper
    f_cf = lambda C: 1 + c.kc * max(C - 0.5, 0)            # C-rate stress
    fCw = (1 - fs) * f_cf(Cac) + fs * f_cf(Cdc)            # charging-mix stress
    Cw = (1 - fs) * Cac + fs * Cdc
    Tcell = Tamb + COOL_K[p.cool - 1] * min(Cw, 3)         # self-heating by cooling type
    if optimized:
        Tcell = min(Tcell, 30); Tamb = min(Tamb, 30)
    dod = hi - lo
    soc_rest = 0.75 * hi + 0.25 * lo                       # time-weighted resting SOC
    fD = (dod / 80) ** c.gD                                # depth-of-discharge factor
    fS = np.exp(c.ks * (soc_rest - 50) / 50)               # SOC stress (calendar)
    fTc = 2 ** (max(Tcell - 25, 0) / (2 * c.Td)) * (1 + c.cold * max(15 - Tcell, 0))
    fTk = 2 ** ((Tamb - 25) / c.Td)                        # Arrhenius-like calendar factor
    efc0 = p.odo * p.whkm / 1000 / p.cap                   # equivalent full cycles so far
    annual = p.akm * p.whkm / 1000 / p.cap                 # EFC per year
    cal_rate = c.kcal * fTk * fS
    cyc_rate = c.kcyc * fTc * fCw * fD
    if hist is None:                                       # aging already accumulated
        hist = {"cal": cal_rate * np.sqrt(p.age), "cyc": cyc_rate * efc0}
    cal = p.scale * (hist["cal"] + cal_rate * (np.sqrt(p.age + YEARS) - np.sqrt(p.age)))  # sqrt(t)
    cyc = p.scale * (hist["cyc"] + cyc_rate * annual * YEARS)                              # linear in EFC
    L = knee(cal + cyc)
    return SimResult(YEARS, np.maximum(100 * (1 - L), 30), cal, cyc, hist,
                     hist["cal"] + hist["cyc"], efc0, annual, Tcell, Cac, Cdc, float(fCw), float(fS), dod, soc_rest)

def anchor_scale(meas_soh: float, base_now: float) -> tuple[float, str]:
    """Re-anchor physics to a SOH value: invert the knee to get raw loss, scale = raw/baseNow
    (clamped 0.2..5). Returns (scale, warning). Port of the refresh() calibration block."""
    if base_now <= 0.003:
        return 1.0, "Anchoring skipped: too little aging so far."
    mL = 1 - meas_soh / 100
    r = (-0.04 + np.sqrt(0.0016 - 16 * (0.0576 - mL))) / 8 if mL > 0.12 else mL
    s = float(min(max(r / base_now, 0.2), 5))
    warn = f"Anchoring factor x{s:.2f} is far from 1: vehicle ages very differently from the generic profile." if (s < 0.5 or s > 2) else ""
    return s, warn

def life_to_80(res: SimResult, fallback: float | None = None):
    """Years until SOH first reaches 80 %, linearly interpolated between forecast grid points
    (0.25 y steps) so the result is not quantised. Only this calculation changed: the SOH curves are untouched."""
    idx = np.where(res.soh <= 80)[0]
    if not len(idx):
        return float(res.yrs[-1] if fallback is None else fallback), False
    i = int(idx[0])
    if i == 0: return float(res.yrs[0]), True                  # already at/below 80 % today
    y0, y1, s0, s1 = res.yrs[i - 1], res.yrs[i], res.soh[i - 1], res.soh[i]
    return float(y0 + (y1 - y0) * (s0 - 80.0) / (s0 - s1)), True
