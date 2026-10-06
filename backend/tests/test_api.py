import io, os, uuid, pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.database.session import new_session
from app.models.orm import MlModel, User, FleetTrainingData
from app.ml.fleet import make_fleet

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
PW = "correct-horse-battery"
CAR = dict(vehicle_name="My car", vehicle_type="Passenger car", battery_chemistry="NMC", cooling_type="liquid", battery_capacity_kwh=60,
           ac_charge_power_kw=7.4, dc_charge_power_kw=100, energy_use_wh_km=160, odometer_km=36000, distance_per_year_km=12000,
           vehicle_age_years=3, ambient_temperature_c=30, dc_fast_pct=20, daily_charge_limit=90, min_soc=15)

@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c: yield c            # runs the real lifespan (startup model)

def register(c, email=None, name="T"):
    email = email or f"{uuid.uuid4().hex[:8]}@test.io"
    r = c.post("/api/auth/register", json=dict(name=name, email=email, password=PW)); assert r.status_code == 201, r.text
    return email, {"Authorization": "Bearer " + r.json()["access_token"]}

@pytest.fixture(scope="module")
def admin(client):
    r = client.post("/api/auth/register", json=dict(name="Admin", email="admin@test.io", password=PW))
    if r.status_code == 409: r = client.post("/api/auth/login", json=dict(email="admin@test.io", password=PW))
    assert r.json()["user"]["role"] == "admin"; return {"Authorization": "Bearer " + r.json()["access_token"]}

def csv_bytes(df): return df.to_csv(index=False).encode()
def upload(c, h, data, name="fleet.csv", **params):
    return c.post("/api/fleet/upload", headers=h, params=params, files={"file": (name, data, "text/csv")})

# ---------------- startup / ML lifecycle ----------------
def test_startup_trains_simulated_model_once(client, admin):
    s = client.get("/api/ml/status", headers=admin).json()
    assert s["trained"] and s["active_model"]["data_source"] == "simulated"
    assert s["banner"] == "ML model currently trained on simulated fleet data."
    with new_session() as db: n0 = db.scalar(select(func.count()).select_from(MlModel)); mid = s["active_model"]["model_id"]
    from app.main import app
    with TestClient(app) as c2:                    # simulated server restart -> must NOT retrain
        assert c2.get("/api/ml/status", headers=admin).json()["active_model"]["model_id"] == mid
    with new_session() as db: assert db.scalar(select(func.count()).select_from(MlModel)) == n0
    m = client.get("/api/ml/metrics", headers=admin).json()
    assert m["rmse_hybrid"] < m["rmse_physics"] and m["n_vehicles_test"] > 0 and len(m["feature_importance"]) == 20
    imps = [f["importance"] for f in m["feature_importance"]]; assert imps == sorted(imps, reverse=True)
    assert set(m["validation"]) == {"measured", "physics", "hybrid"}

def test_health_and_meta(client):
    assert client.get("/api/health").json() == dict(status="ok", database="ok", ml_model_active=True)
    meta = client.get("/api/meta").json()
    assert [p["name"] for p in meta["presets"]][-1] == "Custom (manual)" and meta["presets"][2]["values"]["battery_capacity_kwh"] == 60
    assert meta["limits"]["battery_capacity_kwh"] == {"min": 0.3, "max": 1500}

# ---------------- auth ----------------
def test_auth(client):
    email, h = register(client)
    assert client.get("/api/auth/me", headers=h).json()["email"] == email
    assert client.post("/api/auth/register", json=dict(name="x", email=email.upper(), password=PW)).status_code == 409
    assert client.post("/api/auth/register", json=dict(name="x", email="a@b.io", password="short")).status_code == 422
    assert client.post("/api/auth/login", json=dict(email=email, password="wrong-password")).status_code == 401
    assert client.post("/api/auth/login", json=dict(email="nobody@test.io", password=PW)).status_code == 401
    assert client.post("/api/auth/login", json=dict(email=email, password=PW)).status_code == 200
    assert client.post("/api/auth/token", data=dict(username=email, password=PW)).status_code == 200      # Swagger flow
    for hdr in ({}, {"Authorization": "Bearer garbage"}):
        assert client.get("/api/vehicles", headers=hdr).status_code == 401
    with new_session() as db:
        u = db.scalar(select(User).where(User.email == email)); assert u.password_hash.startswith("$2") and PW not in u.password_hash
    assert client.get("/api/auth/me", headers=h).json()["role"] == "user"

# ---------------- vehicles ----------------
def test_vehicle_crud_and_isolation(client):
    _, a = register(client); _, b = register(client)
    r = client.post("/api/vehicles", json=CAR, headers=a); assert r.status_code == 201; vid = r.json()["id"]
    assert client.get("/api/vehicles", headers=a).json()[0]["id"] == vid and client.get("/api/vehicles", headers=b).json() == []
    for fn in (lambda: client.get(f"/api/vehicles/{vid}", headers=b), lambda: client.put(f"/api/vehicles/{vid}", json=CAR, headers=b),
               lambda: client.delete(f"/api/vehicles/{vid}", headers=b), lambda: client.post(f"/api/vehicles/{vid}/analyze", headers=b)):
        assert fn().status_code == 404
    assert client.put(f"/api/vehicles/{vid}", json={**CAR, "vehicle_name": "Renamed"}, headers=a).json()["vehicle_name"] == "Renamed"
    for bad in ({"battery_chemistry": "XYZ"}, {"battery_capacity_kwh": 0}, {"daily_charge_limit": 120}, {"vehicle_type": "Spaceship"}):
        assert client.post("/api/vehicles", json={**CAR, **bad}, headers=a).status_code == 422
    assert client.delete(f"/api/vehicles/{vid}", headers=a).status_code == 204 and client.get(f"/api/vehicles/{vid}", headers=a).status_code == 404

# ---------------- analysis ----------------
def test_analysis_sources_and_contract(client):
    _, h = register(client); vid = client.post("/api/vehicles", json=CAR, headers=h).json()["id"]
    ml = client.post(f"/api/vehicles/{vid}/analyze", headers=h).json()
    for k in ("current_soh soh_source soh_source_label life_years life_optimized_years life_gained_years risk recommendations efc forecast causes warnings").split():
        assert k in ml, k
    assert ml["soh_source"] == "physics_ml" and ml["ml_correction"] is not None and ml["ml_model"]["data_source"] == "simulated"
    assert ml["saved"] and ml["prediction_id"] and ml["risk"]["factors"] and len(ml["forecast"]["years"]) == 61
    ph = client.post(f"/api/vehicles/{vid}/analyze", json=dict(use_ml=False), headers=h).json()
    assert ph["soh_source"] == "physics_only" and ph["ml_correction"] is None and ph["current_soh"] == ml["physics_soh"]
    me = client.post(f"/api/vehicles/{vid}/analyze", json=dict(calibrate=True, measured_soh=88.5), headers=h).json()
    assert me["soh_source"] == "measured" and me["current_soh"] == pytest.approx(88.5, abs=0.01) and me["soh_source_label"] == "Measured SOH"
    # calibrate with no number and no stored measurement -> error; then store one and it is used
    assert client.post(f"/api/vehicles/{vid}/analyze", json=dict(calibrate=True), headers=h).status_code == 422
    assert client.post(f"/api/vehicles/{vid}/measurements", json=dict(measured_soh=91.0), headers=h).status_code == 201
    st = client.post(f"/api/vehicles/{vid}/analyze", json=dict(calibrate=True, save=False), headers=h).json()
    assert st["current_soh"] == pytest.approx(91.0, abs=0.01) and st["saved"] is False
    assert client.post(f"/api/vehicles/{vid}/analyze", json=dict(measured_soh=30), headers=h).status_code == 422
    hist = client.get(f"/api/vehicles/{vid}/predictions", headers=h).json()
    assert [p["soh_source"] for p in hist] == ["measured", "physics_only", "physics_ml"]          # newest first, save=False skipped
    full = client.get(f"/api/predictions/{hist[0]['id']}", headers=h).json(); assert full["result"]["forecast"]["reference"] == 80
    _, other = register(client); assert client.get(f"/api/predictions/{hist[0]['id']}", headers=other).status_code == 404

def test_preview_is_stateless(client):
    _, h = register(client)
    body = {k: CAR[v] for k, v in dict(cap_kwh="battery_capacity_kwh", ac_kw="ac_charge_power_kw", dc_kw="dc_charge_power_kw", whkm="energy_use_wh_km",
            odo_km="odometer_km", km_per_year="distance_per_year_km", age_years="vehicle_age_years", ambient_c="ambient_temperature_c",
            fast_pct="dc_fast_pct", charge_limit="daily_charge_limit", min_soc="min_soc").items()}
    r = client.post("/api/analyze", json=dict(chem="NMC", cooling="liquid", **body), headers=h)
    assert r.status_code == 200 and r.json()["saved"] is False and r.json()["soh_source"] == "physics_ml"
    assert client.post("/api/analyze", json=dict(chem="NMC", cooling="liquid", calibrate=True, **body), headers=h).status_code == 422

# ---------------- fleet upload + training ----------------
def test_upload_validation(client, admin):
    _, user = register(client); good = make_fleet(30, seed=3)
    assert upload(client, user, csv_bytes(good)).status_code == 403                                           # not admin
    assert upload(client, admin, b"x", name="a.txt").status_code == 415
    r = upload(client, admin, csv_bytes(good.drop(columns=["whkm", "soh_pct"]))); assert r.status_code == 422
    assert "whkm" in r.json()["detail"]["message"] and "soh_pct" in r.json()["detail"]["message"]
    bad = good.copy().astype(object); bad.loc[2, "soh_pct"] = 150; bad.loc[5, "chem"] = "XYZ"; bad.loc[7, "cap_kWh"] = "abc"; bad.loc[9, "cooling"] = 7
    with new_session() as db: before = db.scalar(select(func.count()).select_from(FleetTrainingData))
    r = upload(client, admin, csv_bytes(bad)); d = r.json()["detail"]
    assert r.status_code == 422 and d["n_errors"] == 4 and {(e["row"], e["column"]) for e in d["errors"]} == {(4, "soh_pct"), (7, "chem"), (9, "cap_kWh"), (11, "cooling")}
    with new_session() as db: assert db.scalar(select(func.count()).select_from(FleetTrainingData)) == before        # strict mode stored nothing
    r = upload(client, admin, csv_bytes(bad), skip_invalid="true"); j = r.json()
    assert r.status_code == 201 and j["rows_imported"] == 116 and j["rows_skipped"] == 4 and len(j["errors"]) == 4          # reported, not silent
    r = upload(client, admin, csv_bytes(make_fleet(5, seed=1))); assert r.status_code == 422 and "at least 40" in r.json()["detail"]["message"]
    r = upload(client, admin, csv_bytes(pd.concat([make_fleet(7, seed=1)] * 2))); assert r.status_code == 422 and "distinct vehicle_id" in r.json()["detail"]["message"]
    assert upload(client, admin, b"a,b\n" + b"1,2\n" * 400000).status_code == 413                                              # > 1 MB
    tpl = client.get("/api/fleet/template").text; assert upload(client, admin, tpl.encode()).status_code == 201             # template is valid

def test_upload_train_activate_and_use(client, admin):
    r = upload(client, admin, csv_bytes(make_fleet(60, seed=5)), name="Depot fleet.csv"); assert r.status_code == 201, r.text
    ds = r.json()["dataset"]; assert ds["source"] == "uploaded" and ds["n_vehicles"] == 60
    rows = client.get(f"/api/fleet/datasets/{ds['id']}/rows", headers=admin, params=dict(limit=5)).json(); assert len(rows["rows"]) == 5 and rows["total"] == 240
    _, user = register(client); assert client.post("/api/ml/train", headers=user).status_code == 403
    old = client.get("/api/ml/status", headers=admin).json()["active_model"]["model_id"]
    t = client.post("/api/ml/train", headers=admin, json=dict(dataset_id=ds["id"])); assert t.status_code == 201, t.text
    t = t.json(); assert t["data_source"] == "uploaded" and t["model_id"] != old and "uploaded fleet data" in t["banner"]
    st = client.get("/api/ml/status", headers=admin).json(); assert st["active_model"]["model_id"] == t["model_id"] and "simulated" not in st["banner"]
    models = client.get("/api/ml/models", headers=admin).json(); assert sum(m["is_active"] for m in models) == 1
    with new_session() as db: assert os.path.exists(db.get(MlModel, t["model_id"]).file_path)
    _, h = register(client); vid = client.post("/api/vehicles", json=CAR, headers=h).json()["id"]
    a = client.post(f"/api/vehicles/{vid}/analyze", headers=h).json()
    assert a["ml_model"]["data_source"] == "uploaded" and a["ml_model"]["model_id"] == t["model_id"] and a["soh_source"] == "physics_ml"
    assert client.delete(f"/api/fleet/datasets/{ds['id']}", headers=admin).status_code == 409                # in use by a model
    assert client.post("/api/ml/train", headers=admin, json=dict(dataset_id=ds["id"], kind="ridge")).json()["kind"].startswith("ridge")
    assert client.post("/api/ml/train", headers=admin, json=dict(dataset_id=999999)).status_code == 404
