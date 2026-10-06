// Maps between the saved-vehicle shape (VehicleIn) and the stateless /analyze shape (AnalysisInput).
// Field *limits and presets* are never hard-coded: they come from GET /api/meta.
export const FIELDS = [
  { key: "battery_capacity_kwh", label: "Battery capacity", unit: "kWh", step: 0.1 },
  { key: "ac_charge_power_kw", label: "AC charging", unit: "kW", step: 0.1 },
  { key: "dc_charge_power_kw", label: "DC charging", unit: "kW", step: 1 },
  { key: "energy_use_wh_km", label: "Energy consumption", unit: "Wh/km", step: 1 },
  { key: "odometer_km", label: "Odometer", unit: "km", step: 100 },
  { key: "distance_per_year_km", label: "Annual distance", unit: "km/yr", step: 100 },
  { key: "vehicle_age_years", label: "Vehicle age", unit: "years", step: 0.1 },
  { key: "ambient_temperature_c", label: "Ambient temperature", unit: "°C", step: 1 },
  { key: "dc_fast_pct", label: "Fast charging share", unit: "%", step: 1 },
  { key: "daily_charge_limit", label: "Charge limit", unit: "%", step: 1 },
  { key: "min_soc", label: "Minimum SOC", unit: "%", step: 1 },
];

export const toAnalysisInput = (v, extra = {}) => ({
  chem: v.battery_chemistry, cooling: v.cooling_type, cap_kwh: +v.battery_capacity_kwh, ac_kw: +v.ac_charge_power_kw,
  dc_kw: +v.dc_charge_power_kw, whkm: +v.energy_use_wh_km, odo_km: +v.odometer_km, km_per_year: +v.distance_per_year_km,
  age_years: +v.vehicle_age_years, ambient_c: +v.ambient_temperature_c, fast_pct: +v.dc_fast_pct,
  charge_limit: +v.daily_charge_limit, min_soc: +v.min_soc, use_ml: true, ...extra,
});

// /meta preset.values uses chem/cooling_type/... names; convert to the saved-vehicle shape.
export const fromPreset = (preset) => {
  const x = preset.values;
  return {
    vehicle_type: preset.name, battery_chemistry: x.chem, cooling_type: x.cooling_type,
    battery_capacity_kwh: x.battery_capacity_kwh, ac_charge_power_kw: x.ac_charge_power_kw, dc_charge_power_kw: x.dc_charge_power_kw,
    energy_use_wh_km: x.energy_use_wh_km, odometer_km: x.odometer_km, distance_per_year_km: x.distance_per_year_km,
    vehicle_age_years: x.vehicle_age_years, ambient_temperature_c: x.ambient_temperature_c, dc_fast_pct: x.dc_fast_pct,
    daily_charge_limit: x.daily_charge_limit, min_soc: x.min_soc,
  };
};

export const CUSTOM = "Custom (manual)";
export const emptyVehicle = (meta) => {
  const first = meta.presets.find((p) => p.values);
  return { vehicle_name: "", ...fromPreset(first) };
};
