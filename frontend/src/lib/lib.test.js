import { describe, expect, it } from "vitest";
import { explain } from "./api";
import { gainText, lifeText, signedPct } from "./format";
import { fromPreset, toAnalysisInput } from "./vehicleFields";

describe("format", () => {
  it("shows a lower bound when 80% is not reached", () => {
    expect(lifeText(15, false)).toBe("> 15 yr");
    expect(lifeText(4.06, true)).toBe("4.1 yr");
    expect(gainText(2.1, false, true)).toBe("≥ +2.1 yr");
    expect(gainText(0, false, false)).toBe("n/a");
  });
  it("signs the ML correction", () => { expect(signedPct(0.8)).toBe("+0.8%"); expect(signedPct(-1.6)).toBe("−1.6%"); });
});
describe("api errors", () => {
  it("flattens FastAPI validation errors", () => {
    expect(explain([{ loc: ["body", "ambient_c"], msg: "too big" }], 422)).toBe("ambient_c: too big");
    expect(explain({ message: "bad csv" }, 422)).toBe("bad csv");
    expect(explain("nope", 409)).toBe("nope");
  });
});
describe("vehicle mapping", () => {
  it("maps /meta presets to the analysis payload", () => {
    const v = fromPreset({ name: "Passenger car", values: { chem: "NMC", cooling_type: "liquid", battery_capacity_kwh: 60, ac_charge_power_kw: 7.4, dc_charge_power_kw: 100, energy_use_wh_km: 160, vehicle_age_years: 3, odometer_km: 36000, distance_per_year_km: 12000, ambient_temperature_c: 30, dc_fast_pct: 20, daily_charge_limit: 90, min_soc: 15 } });
    const a = toAnalysisInput(v);
    expect(a).toMatchObject({ chem: "NMC", cooling: "liquid", cap_kwh: 60, fast_pct: 20, charge_limit: 90, use_ml: true });
  });
});
