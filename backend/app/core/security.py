import datetime as dt
import bcrypt
from jose import jwt, JWTError
from app.core.config import get_settings

def hash_password(pw: str) -> str: return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_password(pw: str, h: str) -> bool:
    try: return bcrypt.checkpw(pw.encode(), h.encode())
    except ValueError: return False
_DUMMY = hash_password("dummy-password")   # compared when the email is unknown, so timing doesn't reveal accounts

def create_token(user_id: int, role: str) -> str:
    s = get_settings()
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=s.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, s.jwt_secret, algorithm=s.jwt_algorithm)

def decode_token(token: str) -> dict | None:
    s = get_settings()
    try: return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError: return None
