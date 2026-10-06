"""Dynamic recommendations (port of the MATLAB `recs`/`notes` blocks). Every item is driven by the
computed stresses of THIS vehicle, nothing is a fixed per-vehicle text."""
from app.physics.constants import Chem
from app.physics.model import VehicleParams, SimResult

def build(p: VehicleParams, c: Chem, R: SimResult, gain: float, gain_is_lower_bound: bool):
    recs = []
    add = lambda kind, priority, text: recs.append(dict(kind=kind, priority=priority, text=text))
    cal_share = R.cal[0] / (R.cal[0] + R.cyc[0]) if (R.cal[0] + R.cyc[0]) > 0 else 0.5
    if p.fs > 30 and R.fCw > 1.15:
        add("fast_charging", "high", f"Reduce DC fast charging (about {R.Cdc:.1f}C average at the pack): "
            f"it raises charging stress by {100 * (R.fCw - 1):.0f}% for {c.name}.")
    if p.hi > 85 and R.fS > 1.15:
        add("charge_limit", "high", f"Set the daily charge limit to about 80% (resting-SOC stress is x{R.fS:.2f}).")
    elif c.name == "LFP" and p.hi < 100:
        add("lfp_calibration", "info", "LFP tolerates high SOC well; charge to 100% occasionally so the BMS can recalibrate SOC.")
    if R.Tcell > c.tWarn - 7:
        add("temperature", "high", f"Cell temperature is high (about {R.Tcell:.0f} °C): park in shade, precondition, avoid charging when hot.")
    if R.dod > 80 and c.name != "LTO":
        add("deep_cycle", "medium", f"Deep cycles ({R.dod:.0f}% depth of discharge): recharge before dropping below about 20%.")
    if cal_share > 0.5:
        add("aging_driver", "info", f"Aging is mostly time-driven ({100 * cal_share:.0f}% calendar): resting SOC and temperature matter most.")
    else:
        add("aging_driver", "info", f"Aging is mostly usage-driven ({100 * (1 - cal_share):.0f}% cycling): charging power, depth of discharge and throughput matter most.")
    add("optimized_gain", "info", "Optimized habits (charge limit 80%, <=20% fast charging, cell <=30 °C) extend life by "
        f"{'at least ' if gain_is_lower_bound else 'about '}{gain:.1f} years.")
    return recs, cal_share

def input_warnings(p: VehicleParams, c: Chem, R: SimResult) -> list[str]:
    w = []
    if p.dc / p.cap > c.maxC: w.append(f"DC peak {p.dc / p.cap:.1f}C is above the ~{c.maxC:.0f}C typical for {c.name}: estimate is uncertain.")
    if R.Cac > 1: w.append("AC charging above 1C: please check pack capacity and charger power.")
    if p.cap < 1.5 or p.cap > 400: w.append("Pack capacity outside the typical 1.5-400 kWh range: lower confidence.")
    if R.Tcell > c.tWarn: w.append(f"Cell temperature above the {c.tWarn:.0f} °C limit usual for {c.name}.")
    if p.dc == 0 and p.fs > 0: w.append("DC power is 0, so the fast-charge share has no effect.")
    if R.efc0 > 5000 or R.annual > 600: w.append("Unusually high cycle count: lower confidence.")
    return w
