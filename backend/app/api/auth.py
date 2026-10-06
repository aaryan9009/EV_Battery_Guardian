from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.core.config import get_settings
from app.core.security import hash_password, verify_password, create_token, _DUMMY
from app.database.session import get_db
from app.models.orm import User
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

def _token(u: User) -> TokenOut: return TokenOut(access_token=create_token(u.id, u.role), user=UserOut.model_validate(u))
def _authenticate(db, email, password) -> User:
    u = db.scalar(select(User).where(User.email == email.lower()))
    ok = verify_password(password, u.password_hash if u else _DUMMY)
    if not (u and ok): raise HTTPException(401, "Incorrect email or password")
    return u

@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)): raise HTTPException(409, "Email already registered")
    admins = {e.strip().lower() for e in get_settings().admin_emails.split(",") if e.strip()}
    u = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password), role="admin" if email in admins else "user")
    db.add(u); db.commit()
    return _token(u)

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)): return _token(_authenticate(db, body.email, body.password))

@router.post("/token", include_in_schema=True, summary="OAuth2 form login (used by the Swagger 'Authorize' button)")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    t = _token(_authenticate(db, form.username, form.password)); return {"access_token": t.access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)): return user
