from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

class Base(DeclarativeBase): pass

_engine = _Session = None
def get_engine():
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine

def get_db():                                # FastAPI dependency
    get_engine(); db = _Session()
    try: yield db
    finally: db.close()

def new_session():
    get_engine(); return _Session()
