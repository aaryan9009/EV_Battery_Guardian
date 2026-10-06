"""Chemistry-aware risk score (port of the MATLAB risk block). Four factors, 0-2 points each:
cell temperature vs the chemistry's warning limit, charging stress (fCw), resting-SOC stress (fS),
and current SOH. Score >=5 HIGH, >=3 MODERATE, else LOW."""
from app.physics.constants import Chem

def assess(c: Chem, Tcell: float, fCw: float, fS: float, soh: float) -> dict:
    def pts(v, hi_thr, mid_thr): return 2 if v >= hi_thr else (1 if v >= mid_thr else 0)
    factors = [
        dict(name="Cell temperature", value=round(Tcell, 1), unit="°C", points=pts(Tcell, c.tWarn, c.tWarn - 7),
             detail=f"Warning limit for {c.name} is {c.tWarn:.0f} °C"),
        dict(name="Charging stress", value=round(fCw, 2), unit="x", points=pts(fCw, 1.5, 1.2),
             detail="C-rate stress averaged over AC/DC charging mix"),
        dict(name="SOC stress", value=round(fS, 2), unit="x", points=pts(fS, 1.5, 1.2),
             detail="Resting-SOC calendar-aging multiplier"),
        dict(name="Current SOH", value=round(soh, 1), unit="%", points=2 if soh < 80 else (1 if soh < 90 else 0),
             detail="Below 90 % = watch, below 80 % = end-of-life threshold"),
    ]
    score = sum(f["points"] for f in factors)
    level = "HIGH" if score >= 5 else "MODERATE" if score >= 3 else "LOW"
    return dict(level=level, score=score, max_score=8, factors=factors)
