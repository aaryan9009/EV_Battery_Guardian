"""Input validation. Limits mirror the MATLAB UI field/slider limits."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from app.physics.model import VehicleParams

COOL_CODE = {"liquid": 1, "air": 2, "passive": 3}

class AnalysisInput(BaseModel):
    chem: Literal["LFP", "NMC", "NCA", "LTO"]
    cooling: Literal["liquid", "air", "passive"]
    cap_kwh: float = Field(ge=0.3, le=1500)
    ac_kw: float = Field(ge=0.1, le=1500)
    dc_kw: float = Field(ge=0, le=1500)
    whkm: float = Field(ge=5, le=5000)
    odo_km: float = Field(ge=0, le=3e6)
    km_per_year: float = Field(ge=0, le=5e5)
    age_years: float = Field(ge=0, le=15)
    ambient_c: float = Field(ge=-10, le=50)
    fast_pct: float = Field(ge=0, le=100)
    charge_limit: float = Field(ge=50, le=100)
    min_soc: float = Field(ge=0, le=60)
    calibrate: bool = False
    measured_soh: float | None = Field(default=None, ge=40, le=100)
    use_ml: bool = True

    @model_validator(mode="after")
    def _need_measured(self):
        if self.calibrate and self.measured_soh is None:
            raise ValueError("measured_soh is required when calibrate is true")
        return self

    def to_params(self) -> VehicleParams:
        return VehicleParams(self.chem, COOL_CODE[self.cooling], self.cap_kwh, self.ac_kw, self.dc_kw, self.whkm,
                             self.odo_km, self.km_per_year, self.age_years, self.ambient_c, self.fast_pct,
                             self.charge_limit, self.min_soc)

# ---------- response contract (what the React app receives) ----------
class AnalyzeOptions(BaseModel):
    calibrate: bool = False                    # anchor to a measured SOH
    measured_soh: float | None = Field(default=None, ge=40, le=100)   # omitted -> latest stored measurement
    use_ml: bool = True
    save: bool = True                          # store the result in soh_predictions

class RiskFactor(BaseModel):
    name: str; value: float; unit: str; points: int; detail: str
class Risk(BaseModel):
    level: Literal["LOW", "MODERATE", "HIGH"]; score: int; max_score: int; factors: list[RiskFactor]
class Recommendation(BaseModel):
    kind: str; priority: Literal["high", "medium", "info"]; text: str
class Forecast(BaseModel):
    years: list[float]; current: list[float]; optimized: list[float]; reference: float
class Causes(BaseModel):
    labels: list[str]; calendar: list[float]; cycling: list[float]
class Details(BaseModel):
    ac_c_rate: float; dc_c_rate_avg: float; cell_temp_c: float; resting_soc: float
    dod: float; charging_stress: float; soc_stress: float
class MlInfo(BaseModel):
    kind: str; label: str; stats: dict; data_source: str | None = None; model_id: int | None = None
class AnalysisResult(BaseModel):
    soh_source: Literal["measured", "physics_ml", "physics_only"]
    soh_source_label: str
    current_soh: float; physics_soh: float
    ml_correction: float | None; soh_error_band: float | None
    anchor_scale: float; efc: float; efc_per_year: float
    life_years: float; life_reached: bool; life_km: float
    life_optimized_years: float; life_optimized_reached: bool; life_gained_years: float
    calendar_share: float
    risk: Risk; recommendations: list[Recommendation]; warnings: list[str]
    details: Details; forecast: Forecast; causes: Causes
    ml_model: MlInfo | None
    prediction_id: int | None = None; saved: bool = False
