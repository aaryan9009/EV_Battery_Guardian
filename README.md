# EV Battery Guardian — Stage 6 (React frontend)

```
frontend/   React 18 + Vite + Tailwind + Recharts   (new in Stage 6)
backend/    FastAPI + PostgreSQL + physics + ML      (Stage 5, one isolated change: life-to-80 % interpolation)
```

The frontend contains **no physics or ML**. It renders what the 26 API operations return.
Presets, chemistries, cooling options and field limits come from `GET /api/meta`.

## Run locally
```bash
# 1. backend (needs PostgreSQL; see backend/.env.example)
cd backend && pip install -r requirements.txt
cp .env.example .env            # set DATABASE_URL, JWT_SECRET, ADMIN_EMAILS
alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 2. frontend
cd frontend && npm install
npm run dev                     # http://localhost:5173  (Vite proxies /api to :8000)
```
Register with an email listed in `ADMIN_EMAILS` to get the admin role (needed for CSV upload and training on the ML page).

## Pages
| Page | What it does | Endpoints |
|---|---|---|
| Login / Register | JWT auth, session restored on reload, auto sign-out on 401 | `/auth/login`, `/auth/register`, `/auth/me` |
| Dashboard | Vehicle selector, Current SOH + source badge, Physics / ML correction / Final SOH, Life to 80 %, Risk, Optimized gain, EFC, forecast chart, aging causes, risk factors, recommendations, measured-SOH anchoring, prediction history | `/vehicles/{id}/analyze`, `/measurements`, `/predictions` |
| Vehicles | Add / edit / delete, presets from `/meta` | `/vehicles`, `/meta` |
| Analysis | Live what-if sliders (debounced, stale requests cancelled), nothing saved unless you press "Save as vehicle" | `/analyze` |
| ML Model | Status banner (follows backend `data_source`), MAE/RMSE, held-out scatter, feature importance, training history, admin CSV upload + train | `/ml/*`, `/fleet/*` |

## Tests
```bash
cd backend  && TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost/evtest pytest   # 34 tests
cd frontend && npm test && npm run build
```

## Backend change in this stage
`life_to_80` now linearly interpolates the 80 % crossing between the 0.25-year forecast points.
SOH curves, physics SOH, ML correction, EFC and risk are untouched (pinned by `tests/test_life.py`).
Example: the taxi (80.7 % SOH) now shows 0.1 yr instead of 0.25/0.5 yr.

## Stage 7 notes (deployment)
* Frontend: set `VITE_API_URL` to the deployed API origin and run `npm run build` (static `dist/`).
* Backend: add the frontend origin to `CORS_ORIGINS`; use a managed PostgreSQL URL and a strong `JWT_SECRET`.
* `model_store/` must be on persistent storage (or retrain after deploy; the simulated model is recreated at startup).
* Token is kept in `localStorage`; fine for this app, consider httpOnly cookies if the threat model grows.
