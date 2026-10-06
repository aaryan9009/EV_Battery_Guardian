import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, vehicles, analysis, fleet, ml, meta
from app.core.config import get_settings
from app.database.session import new_session
from app.services.ml_registry import registry

log = logging.getLogger("ev_guardian")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:                                            # idempotent: reuses the active model, trains on the simulated fleet only if none exists
        with new_session() as db: registry.ensure_startup_model(db)
    except Exception:
        log.exception("Startup model check failed; API runs with physics-only SOH until a model is trained")
    yield

app = FastAPI(title="EV Battery Guardian API", version="1.0.0", lifespan=lifespan,
              description="Hybrid physics + ML EV battery health: SOH, life to 80 %, risk and recommendations.")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=False)   # Bearer tokens, no cookies
for r in (meta.router, auth.router, vehicles.router, analysis.router, fleet.router, ml.router):
    app.include_router(r, prefix="/api")
