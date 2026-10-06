from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import decode_token
from app.database.session import get_db
from app.models.orm import User, Vehicle

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
_401 = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})

def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload or not str(payload.get("sub", "")).isdigit(): raise _401
    user = db.get(User, int(payload["sub"]))
    if user is None: raise _401
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin": raise HTTPException(403, "Admin role required")
    return user

def owned_vehicle(db: Session, user: User, vehicle_id: int) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if v is None or v.user_id != user.id: raise HTTPException(404, "Vehicle not found")   # 404, not 403: don't leak existence
    return v
