"""Relational schema.  users -> vehicles -> {battery_measurements, soh_predictions, charging_history}
                       users -> fleet_datasets -> {fleet_training_data, ml_models}
Schema changes go through Alembic only."""
from datetime import datetime
from sqlalchemy import (String, Integer, Float, Boolean, DateTime, ForeignKey, CheckConstraint, Index, JSON, text, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")
now = lambda: mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user")
    created_at: Mapped[datetime] = now()
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    __table_args__ = (CheckConstraint("role IN ('user','admin')", name="ck_users_role"),)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vehicle_name: Mapped[str] = mapped_column(String(120))
    vehicle_type: Mapped[str] = mapped_column(String(40))            # preset name or 'Custom (manual)'
    battery_chemistry: Mapped[str] = mapped_column(String(3))
    cooling_type: Mapped[str] = mapped_column(String(10))
    battery_capacity_kwh: Mapped[float] = mapped_column(Float)
    ac_charge_power_kw: Mapped[float] = mapped_column(Float)
    dc_charge_power_kw: Mapped[float] = mapped_column(Float)
    energy_use_wh_km: Mapped[float] = mapped_column(Float)
    odometer_km: Mapped[float] = mapped_column(Float)
    distance_per_year_km: Mapped[float] = mapped_column(Float)
    vehicle_age_years: Mapped[float] = mapped_column(Float)
    # usage inputs needed by the physics model (not in the original brief, required by the MATLAB model)
    ambient_temperature_c: Mapped[float] = mapped_column(Float)
    dc_fast_pct: Mapped[float] = mapped_column(Float)
    daily_charge_limit: Mapped[float] = mapped_column(Float)
    min_soc: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = now()
    user: Mapped[User] = relationship(back_populates="vehicles")
    measurements: Mapped[list["BatteryMeasurement"]] = relationship(cascade="all, delete-orphan", back_populates="vehicle")
    predictions: Mapped[list["SohPrediction"]] = relationship(cascade="all, delete-orphan", back_populates="vehicle")
    charging: Mapped[list["ChargingHistory"]] = relationship(cascade="all, delete-orphan", back_populates="vehicle")
    __table_args__ = (
        CheckConstraint("battery_chemistry IN ('LFP','NMC','NCA','LTO')", name="ck_vehicles_chem"),
        CheckConstraint("cooling_type IN ('liquid','air','passive')", name="ck_vehicles_cooling"),
        CheckConstraint("battery_capacity_kwh > 0", name="ck_vehicles_cap_pos"),
        CheckConstraint("daily_charge_limit BETWEEN 50 AND 100 AND min_soc BETWEEN 0 AND 60 AND dc_fast_pct BETWEEN 0 AND 100",
                        name="ck_vehicles_soc_ranges"),
    )

class BatteryMeasurement(Base):
    __tablename__ = "battery_measurements"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    measured_soh: Mapped[float] = mapped_column(Float)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    odometer_km: Mapped[float | None] = mapped_column(Float)
    ambient_temperature: Mapped[float | None] = mapped_column(Float)
    cell_temperature: Mapped[float | None] = mapped_column(Float)
    soc: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = now()
    vehicle: Mapped[Vehicle] = relationship(back_populates="measurements")
    __table_args__ = (CheckConstraint("measured_soh BETWEEN 0 AND 100", name="ck_meas_soh"),
                      Index("ix_meas_vehicle_time", "vehicle_id", "measured_at"))

class FleetDataset(Base):
    """One imported (or simulated) fleet file. Lets us say honestly where a model's training data came from."""
    __tablename__ = "fleet_datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(10))                  # 'simulated' | 'uploaded'
    n_rows: Mapped[int] = mapped_column(Integer)
    n_vehicles: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = now()
    __table_args__ = (CheckConstraint("source IN ('simulated','uploaded')", name="ck_dataset_source"),)

class FleetTrainingData(Base):
    __tablename__ = "fleet_training_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("fleet_datasets.id", ondelete="CASCADE"), index=True)
    vehicle_ref: Mapped[str] = mapped_column(String(64))             # vehicle_id column from the CSV (split key)
    chem: Mapped[str] = mapped_column(String(3))
    cooling: Mapped[int] = mapped_column(Integer)                    # 1 liquid, 2 air, 3 passive
    cap_kwh: Mapped[float] = mapped_column(Float); ac_kw: Mapped[float] = mapped_column(Float)
    dc_kw: Mapped[float] = mapped_column(Float); whkm: Mapped[float] = mapped_column(Float)
    age_yr: Mapped[float] = mapped_column(Float); odo_km: Mapped[float] = mapped_column(Float)
    km_per_yr: Mapped[float] = mapped_column(Float); tamb_c: Mapped[float] = mapped_column(Float)
    fast_pct: Mapped[float] = mapped_column(Float); charge_limit: Mapped[float] = mapped_column(Float)
    min_soc: Mapped[float] = mapped_column(Float); soh_pct: Mapped[float] = mapped_column(Float)
    __table_args__ = (CheckConstraint("chem IN ('LFP','NMC','NCA','LTO')", name="ck_fleet_chem"),
                      CheckConstraint("cooling BETWEEN 1 AND 3", name="ck_fleet_cooling"),
                      Index("ix_fleet_dataset_vehicle", "dataset_id", "vehicle_ref"))

class MlModel(Base):
    __tablename__ = "ml_models"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("fleet_datasets.id", ondelete="RESTRICT"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    data_source: Mapped[str] = mapped_column(String(10))             # copied from the dataset: drives the UI banner
    n_train: Mapped[int] = mapped_column(Integer); n_test: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSONType)                   # MAE/RMSE physics vs hybrid
    feature_importance: Mapped[list] = mapped_column(JSONType)
    validation: Mapped[dict] = mapped_column(JSONType)                # measured/physics/hybrid on held-out vehicles
    file_path: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    trained_at: Mapped[datetime] = now()
    __table_args__ = (Index("uq_ml_models_one_active", "is_active", unique=True,
                            postgresql_where=text("is_active"), sqlite_where=text("is_active")),)

class SohPrediction(Base):
    __tablename__ = "soh_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    model_id: Mapped[int | None] = mapped_column(ForeignKey("ml_models.id", ondelete="SET NULL"))
    soh_source: Mapped[str] = mapped_column(String(12))
    physics_soh: Mapped[float] = mapped_column(Float)
    ml_correction: Mapped[float | None] = mapped_column(Float)
    hybrid_soh: Mapped[float] = mapped_column(Float)                  # the SOH actually used (current_soh)
    anchor_scale: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(8))
    risk_score: Mapped[int] = mapped_column(Integer)
    life_remaining_years: Mapped[float] = mapped_column(Float)
    life_optimized_years: Mapped[float] = mapped_column(Float)
    life_gained_years: Mapped[float] = mapped_column(Float)
    efc: Mapped[float] = mapped_column(Float)
    inputs: Mapped[dict] = mapped_column(JSONType)                    # snapshot of the inputs used
    result: Mapped[dict] = mapped_column(JSONType)                    # full analysis payload (charts, recs)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vehicle: Mapped[Vehicle] = relationship(back_populates="predictions")
    __table_args__ = (CheckConstraint("risk_level IN ('LOW','MODERATE','HIGH')", name="ck_pred_risk"),
                      CheckConstraint("soh_source IN ('measured','physics_ml','physics_only')", name="ck_pred_source"),
                      Index("ix_pred_vehicle_time", "vehicle_id", "predicted_at"))

class ChargingHistory(Base):
    __tablename__ = "charging_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    charging_type: Mapped[str] = mapped_column(String(2))             # 'AC' | 'DC'
    charging_power_kw: Mapped[float] = mapped_column(Float)
    start_soc: Mapped[float] = mapped_column(Float); end_soc: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float)
    charging_duration_min: Mapped[float | None] = mapped_column(Float)
    charged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vehicle: Mapped[Vehicle] = relationship(back_populates="charging")
    __table_args__ = (CheckConstraint("charging_type IN ('AC','DC')", name="ck_charge_type"),
                      CheckConstraint("start_soc BETWEEN 0 AND 100 AND end_soc BETWEEN 0 AND 100", name="ck_charge_soc"),
                      Index("ix_charge_vehicle_time", "vehicle_id", "charged_at"))
