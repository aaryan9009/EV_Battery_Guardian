"""Knowledge base ported 1:1 from EV_Battery_Guardian_App.m (section 1).
Chemistry coefficients (MATLAB struct `chem`):
  kcyc : cycling-fade per equivalent full cycle     kcal : calendar-fade rate (per sqrt-year)
  Td   : temperature doubling scale (deg C)         cold : extra cycling fade below 15 C
  kc   : C-rate stress slope above 0.5C             gD   : depth-of-discharge exponent
  ks   : SOC-stress exponent                        maxC : typical max DC C-rate
  tWarn: cell-temperature warning limit (deg C)
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Chem:
    name: str; kcyc: float; kcal: float; Td: float; cold: float
    kc: float; gD: float; ks: float; maxC: float; tWarn: float

CHEMS = {c.name: c for c in [
    Chem("LFP", 4e-5,  .012, 12, .05, .25, .8, .3, 3, 45),
    Chem("NMC", 1.0e-4, .018, 10, .04, .50, 1.0, .8, 3, 40),
    Chem("NCA", 1.2e-4, .020, 10, .04, .60, 1.0, .9, 3, 40),
    Chem("LTO", 1.5e-5, .006, 15, .01, .05, .5, .1, 6, 55),
]}
CHEM_NAMES = list(CHEMS)                      # order matters for ML one-hot
COOL_NAMES = ["Liquid-cooled", "Air-cooled", "Passive / none"]
COOL_K = [3, 6, 9]                            # deg C rise per C-rate (1-based cooling code)

PRESET_NAMES = ["E-scooter (2W)", "E-rickshaw (3W)", "Passenger car",
                "Ride-hail taxi", "E-bus", "Custom (manual)"]
# chem(1-based) cool cap ac dc Wh/km age odo km/yr Tamb fast hi lo
PRESET_VALS = [
    [2, 2, 3,   0.6, 0,   35,   2, 14000,  7000,  32, 0,  100, 15],
    [1, 2, 7,   1.0, 0,   60,   2, 40000,  20000, 33, 0,  100, 20],
    [2, 1, 60,  7.4, 100, 160,  3, 36000,  12000, 30, 20, 90,  15],
    [2, 1, 50,  11,  100, 150,  3, 150000, 50000, 33, 60, 95,  10],
    [1, 1, 300, 22,  150, 1100, 4, 200000, 55000, 30, 50, 100, 20],
]
PRESET_KEYS = ["chem", "cool", "cap", "ac", "dc", "whkm", "age", "odo", "akm", "Tamb", "fs", "hi", "lo"]

def preset_as_dict(i: int) -> dict:
    d = dict(zip(PRESET_KEYS, PRESET_VALS[i]))
    d["chem"] = CHEM_NAMES[d["chem"] - 1]
    return d

FEATURE_NAMES = ['LFP','NMC','NCA','LTO','ln(capacity)','AC C-rate','DC C-rate','age',
    'EFC so far','EFC per year','ambient T','cell T','fast %','charge limit','min SOC',
    'DoD','resting SOC','C-rate stress','SOC stress','physics SOH']
