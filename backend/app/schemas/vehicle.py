from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from app.physics.constants import PRESET_NAMES

class VehicleIn(BaseModel):
    vehicle_name: str = Field(min_length=1, max_length=120)
    vehicle_type: str = "Custom (manual)"
    battery_chemistry: Literal["LFP", "NMC", "NCA", "LTO"]
    cooling_type: Literal["liquid", "air", "passive"]
    battery_capacity_kwh: float = Field(ge=0.3, le=1500)
    ac_charge_power_kw: float = Field(ge=0.1, le=1500)
    dc_charge_power_kw: float = Field(ge=0, le=1500)
    energy_use_wh_km: float = Field(ge=5, le=5000)
    odometer_km: float = Field(ge=0, le=3e6)
    distance_per_year_km: float = Field(ge=0, le=5e5)
    vehicle_age_years: float = Field(ge=0, le=15)
    ambient_temperature_c: float = Field(ge=-10, le=50)
    dc_fast_pct: float = Field(ge=0, le=100)
    daily_charge_limit: float = Field(ge=50, le=100)
    min_soc: float = Field(ge=0, le=60)
    @field_validator("vehicle_type")
    @classmethod
    def _preset(cls, v):
        if v not in PRESET_NAMES: raise ValueError(f"vehicle_type must be one of {PRESET_NAMES}")
        return v

class VehicleOut(VehicleIn):
    model_config = {"from_attributes": True}
    id: int; created_at: datetime

class MeasurementIn(BaseModel):
    measured_soh: float = Field(ge=40, le=100)
    measured_at: datetime | None = None
    odometer_km: float | None = Field(default=None, ge=0, le=3e6)
    ambient_temperature: float | None = Field(default=None, ge=-40, le=70)
    cell_temperature: float | None = Field(default=None, ge=-40, le=100)
    soc: float | None = Field(default=None, ge=0, le=100)
class MeasurementOut(MeasurementIn):
    model_config = {"from_attributes": True}
    id: int; vehicle_id: int; measured_at: datetime
