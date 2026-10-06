from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, owned_vehicle
from app.database.session import get_db
from app.models.orm import User, Vehicle, BatteryMeasurement
from app.schemas.vehicle import VehicleIn, VehicleOut, MeasurementIn, MeasurementOut

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

@router.post("", response_model=VehicleOut, status_code=201)
def create(body: VehicleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = Vehicle(user_id=user.id, **body.model_dump()); db.add(v); db.commit(); return v

@router.get("", response_model=list[VehicleOut])
def list_vehicles(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Vehicle).where(Vehicle.user_id == user.id).order_by(Vehicle.id)).all()

@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_one(vehicle_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)): return owned_vehicle(db, user, vehicle_id)

@router.put("/{vehicle_id}", response_model=VehicleOut)
def update(vehicle_id: int, body: VehicleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = owned_vehicle(db, user, vehicle_id)
    for k, val in body.model_dump().items(): setattr(v, k, val)
    db.commit(); return v

@router.delete("/{vehicle_id}", status_code=204)
def delete(vehicle_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned_vehicle(db, user, vehicle_id)); db.commit(); return Response(status_code=204)

@router.post("/{vehicle_id}/measurements", response_model=MeasurementOut, status_code=201)
def add_measurement(vehicle_id: int, body: MeasurementIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = owned_vehicle(db, user, vehicle_id)
    data = body.model_dump(); data["measured_at"] = data["measured_at"] or datetime.now(timezone.utc)
    m = BatteryMeasurement(vehicle_id=v.id, **data); db.add(m); db.commit(); return m

@router.get("/{vehicle_id}/measurements", response_model=list[MeasurementOut])
def list_measurements(vehicle_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = owned_vehicle(db, user, vehicle_id)
    return db.scalars(select(BatteryMeasurement).where(BatteryMeasurement.vehicle_id == v.id)
                      .order_by(BatteryMeasurement.measured_at.desc())).all()
