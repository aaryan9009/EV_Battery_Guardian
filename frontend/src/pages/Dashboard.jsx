import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useVehicles } from "../components/useVehicles";
import ResultView from "../components/ResultView";
import { Empty, ErrorBox, Field, Modal, Notice, PageHeader, Spinner } from "../components/ui";
import { date, pct, lifeText, signedPct } from "../lib/format";

const SEL = "evg_selected_vehicle";
const loadSel = () => { try { return Number(localStorage.getItem(SEL)) || null; } catch { return null; } };
const saveSel = (id) => { try { localStorage.setItem(SEL, String(id)); } catch { /* ignore */ } };

function MeasurementModal({ vehicle, onClose, onSaved }) {
  const [soh, setSoh] = useState(""), [odo, setOdo] = useState(String(vehicle.odometer_km));
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try { await api.addMeasurement(vehicle.id, { measured_soh: Number(soh), odometer_km: odo === "" ? null : Number(odo) }); onSaved(); }
    catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  };
  return (
    <Modal title={`Add measured SOH · ${vehicle.vehicle_name}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorBox>{err}</ErrorBox>
        <Field label="Measured SOH (%)" hint="From a BMS read-out or capacity test, 40 – 100"><input className="input" type="number" step="0.1" min="40" max="100" required autoFocus value={soh} onChange={(e) => setSoh(e.target.value)} /></Field>
        <Field label="Odometer at measurement (km)"><input className="input" type="number" min="0" value={odo} onChange={(e) => setOdo(e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={busy}>Save measurement</button></div>
      </form>
    </Modal>
  );
}

export default function Dashboard() {
  const { vehicles, error: vErr } = useVehicles();
  const [id, setId] = useState(loadSel);
  const [calibrate, setCalibrate] = useState(false);
  const [res, setRes] = useState(null), [loading, setLoading] = useState(false), [err, setErr] = useState("");
  const [meas, setMeas] = useState([]), [hist, setHist] = useState([]);
  const [showMeas, setShowMeas] = useState(false), [savedMsg, setSavedMsg] = useState("");
  const seq = useRef(0);

  const vehicle = vehicles?.find((v) => v.id === id) || null;
  useEffect(() => { if (vehicles?.length && !vehicle) setId(vehicles[0].id); }, [vehicles, vehicle]);
  useEffect(() => { if (id) saveSel(id); }, [id]);

  const loadSide = useCallback(async (vid) => {
    const [m, h] = await Promise.all([api.measurements(vid).catch(() => []), api.history(vid).catch(() => [])]);
    setMeas(m); setHist(h);
  }, []);

  const run = useCallback(async (save = false) => {
    if (!id) return;
    const n = ++seq.current; setLoading(true); setErr(""); setSavedMsg("");
    try {
      const r = await api.analyzeVehicle(id, { calibrate, use_ml: true, save });
      if (n !== seq.current) return;              // a newer request superseded this one
      setRes(r); if (save) { setSavedMsg("Saved to history."); loadSide(id); }
    } catch (e) { if (n === seq.current) { setErr(e.message); setRes(null); } }
    finally { if (n === seq.current) setLoading(false); }
  }, [id, calibrate, loadSide]);

  useEffect(() => { setRes(null); setCalibrate(false); if (id) loadSide(id); }, [id, loadSide]);
  useEffect(() => { run(false); }, [run]);

  if (vehicles === null) return <div className="py-20 text-center"><Spinner /></div>;
  if (!vehicles.length) return (
    <><PageHeader title="Dashboard" /><ErrorBox>{vErr}</ErrorBox>
      <Empty title="No vehicles yet"><Link className="text-brand underline" to="/vehicles">Add your first vehicle</Link> or try the <Link className="text-brand underline" to="/analysis">what-if analysis</Link> without saving anything.</Empty></>
  );

  return (
    <>
      <PageHeader title="Dashboard" subtitle={vehicle ? `${vehicle.vehicle_type} · ${vehicle.battery_chemistry} · ${vehicle.battery_capacity_kwh} kWh` : undefined}
        actions={<>
          <button className="btn-ghost" onClick={() => setShowMeas(true)} disabled={!vehicle}>Add measured SOH</button>
          <button className="btn-primary" onClick={() => run(true)} disabled={loading || !res}>Save to history</button>
        </>} />
      <div className="card mb-4 flex flex-wrap items-end gap-4">
        <div className="min-w-[220px] flex-1"><Field label="Vehicle">
          <select className="input" value={id || ""} onChange={(e) => setId(Number(e.target.value))}>{vehicles.map((v) => <option key={v.id} value={v.id}>{v.vehicle_name}</option>)}</select></Field></div>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={calibrate} onChange={(e) => setCalibrate(e.target.checked)} disabled={!meas.length} />
          Anchor to latest measured SOH{meas.length ? ` (${pct(meas[0].measured_soh)}, ${date(meas[0].measured_at)})` : " (none recorded yet)"}
        </label>
        {loading && <Spinner className="mb-3 text-brand" />}
      </div>
      <div className="mb-4 space-y-2">{vErr && <ErrorBox>{vErr}</ErrorBox>}<ErrorBox>{err}</ErrorBox>{savedMsg && <Notice tone="ok">{savedMsg}</Notice>}</div>

      {res ? <ResultView r={res} stale={loading} /> : !err && <div className="py-16 text-center"><Spinner className="text-brand" /></div>}

      {hist.length > 0 && (
        <div className="card mt-4 overflow-x-auto">
          <h3 className="h-section">Saved prediction history</h3>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-ink-soft"><tr>{["When", "Source", "Physics", "ML corr.", "SOH", "Life to 80%", "Risk"].map((h) => <th key={h} className="py-2 pr-4 font-medium">{h}</th>)}</tr></thead>
            <tbody className="divide-y divide-line tabular-nums">
              {hist.map((h) => (
                <tr key={h.id}><td className="py-2 pr-4">{date(h.predicted_at)}</td><td className="pr-4">{h.soh_source.replace("_", " + ")}</td><td className="pr-4">{pct(h.physics_soh)}</td>
                  <td className="pr-4">{h.ml_correction == null ? "–" : signedPct(h.ml_correction)}</td><td className="pr-4 font-medium">{pct(h.current_soh)}</td><td className="pr-4">{lifeText(h.life_years, true)}</td><td>{h.risk_level}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showMeas && vehicle && <MeasurementModal vehicle={vehicle} onClose={() => setShowMeas(false)} onSaved={() => { setShowMeas(false); loadSide(vehicle.id); }} />}
    </>
  );
}
