import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import { useMeta } from "../components/Meta";
import { useVehicles } from "../components/useVehicles";
import ResultView from "../components/ResultView";
import VehicleForm from "../components/VehicleForm";
import { ErrorBox, Field, Modal, Notice, PageHeader, Spinner } from "../components/ui";
import { CUSTOM, FIELDS, emptyVehicle, fromPreset, toAnalysisInput } from "../lib/vehicleFields";

// Sliders: the three habit levers from the what-if panel. Limits come from /api/meta.
const SLIDERS = [
  { key: "dc_fast_pct", label: "DC fast charging", unit: "%" },
  { key: "daily_charge_limit", label: "Charge limit", unit: "%" },
  { key: "ambient_temperature_c", label: "Ambient temperature", unit: "°C" },
  { key: "min_soc", label: "Minimum SOC", unit: "%" },
];
const SLIDER_KEYS = new Set(SLIDERS.map((s) => s.key));

export default function Analysis() {
  const { meta } = useMeta();
  const { vehicles } = useVehicles();
  const [v, setV] = useState(null);
  const [res, setRes] = useState(null), [loading, setLoading] = useState(false), [err, setErr] = useState("");
  const [saving, setSaving] = useState(false), [savedMsg, setSavedMsg] = useState("");
  const [measured, setMeasured] = useState("");
  const seq = useRef(0);

  useEffect(() => { if (meta && !v) setV(emptyVehicle(meta)); }, [meta, v]);

  const input = useMemo(() => {
    if (!v) return null;
    const m = measured === "" ? null : Number(measured);
    return toAnalysisInput(v, m != null && m >= 40 && m <= 100 ? { calibrate: true, measured_soh: m } : {});
  }, [v, measured]);
  const valid = !!v && FIELDS.every((f) => v[f.key] !== "" && v[f.key] != null && !Number.isNaN(Number(v[f.key])));

  // Live what-if: debounce, cancel the in-flight request, ignore stale responses. Nothing is saved.
  useEffect(() => {
    if (!input || !valid) return;
    const n = ++seq.current, ctl = new AbortController();
    const t = setTimeout(async () => {
      setLoading(true); setErr("");
      try { const r = await api.analyze(input, ctl.signal); if (n === seq.current) setRes(r); }
      catch (e) { if (e.name !== "AbortError" && n === seq.current) setErr(e.message); }
      finally { if (n === seq.current) setLoading(false); }
    }, 300);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [input, valid]);

  if (!meta || !v) return <div className="py-20 text-center"><Spinner /></div>;
  const lim = (k) => meta.limits[k] || {};
  const set = (k, val) => setV((p) => ({ ...p, [k]: val, ...(SLIDER_KEYS.has(k) || FIELDS.some((f) => f.key === k) || k === "battery_chemistry" || k === "cooling_type" ? { vehicle_type: CUSTOM } : {}) }));
  const fromSaved = (id) => { const s = vehicles.find((x) => x.id === Number(id)); if (s) { const { id: _i, created_at: _c, ...rest } = s; setV(rest); } };
  const pickPreset = (name) => { const p = meta.presets.find((x) => x.name === name); setV((c) => (p?.values ? { ...c, ...fromPreset(p) } : { ...c, vehicle_type: CUSTOM })); };

  return (
    <>
      <PageHeader title="Analysis" subtitle="Change any value and the forecast updates live. Nothing is saved until you choose to." />
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <div className="card space-y-3">
            <h3 className="h-section !mb-0">Vehicle</h3>
            {vehicles?.length > 0 && <Field label="Start from a saved vehicle"><select className="input" defaultValue="" onChange={(e) => e.target.value && fromSaved(e.target.value)}><option value="">Choose…</option>{vehicles.map((x) => <option key={x.id} value={x.id}>{x.vehicle_name}</option>)}</select></Field>}
            <Field label="Preset"><select className="input" value={v.vehicle_type} onChange={(e) => pickPreset(e.target.value)}>{meta.presets.map((p) => <option key={p.name}>{p.name}</option>)}</select></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Chemistry"><select className="input" value={v.battery_chemistry} onChange={(e) => set("battery_chemistry", e.target.value)}>{meta.chemistries.map((c) => <option key={c.name}>{c.name}</option>)}</select></Field>
              <Field label="Cooling"><select className="input" value={v.cooling_type} onChange={(e) => set("cooling_type", e.target.value)}>{meta.cooling.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select></Field>
            </div>
          </div>

          <div className="card space-y-4">
            <h3 className="h-section !mb-0">What-if sliders</h3>
            {SLIDERS.map((s) => {
              const l = lim(s.key);
              return (
                <div key={s.key}>
                  <div className="mb-1 flex justify-between text-sm"><label htmlFor={s.key} className="font-medium">{s.label}</label><span className="tabular-nums text-brand">{v[s.key]}{s.unit}</span></div>
                  <input id={s.key} className="w-full" type="range" min={l.min} max={l.max} step={1} value={v[s.key]} onChange={(e) => set(s.key, Number(e.target.value))} />
                  <div className="flex justify-between text-xs text-ink-soft"><span>{l.min}{s.unit}</span><span>{l.max}{s.unit}</span></div>
                </div>
              );
            })}
          </div>

          <details className="card">
            <summary className="cursor-pointer text-sm font-semibold">Vehicle parameters</summary>
            <div className="mt-3 grid grid-cols-2 gap-3">
              {FIELDS.filter((f) => !SLIDER_KEYS.has(f.key)).map((f) => (
                <Field key={f.key} label={`${f.label} (${f.unit})`}>
                  <input className="input tabular-nums" type="number" step={f.step} min={lim(f.key).min} max={lim(f.key).max} value={v[f.key]} onChange={(e) => set(f.key, e.target.value === "" ? "" : Number(e.target.value))} />
                </Field>
              ))}
            </div>
          </details>

          <div className="card space-y-3">
            <Field label="Measured SOH (optional)" hint="Anchors the model to a real reading (40–100%)"><input className="input" type="number" min="40" max="100" step="0.1" placeholder="e.g. 91.5" value={measured} onChange={(e) => setMeasured(e.target.value)} /></Field>
            <button className="btn-ghost w-full" onClick={() => { setSavedMsg(""); setSaving(true); }}>Save as vehicle…</button>
          </div>
        </aside>

        <section className="min-w-0">
          <div className="mb-3 space-y-2"><ErrorBox>{err}</ErrorBox>{savedMsg && <Notice tone="ok">{savedMsg}</Notice>}{!valid && <Notice tone="warn">Fill in every parameter to run the analysis.</Notice>}</div>
          {loading && <div className="mb-2 flex items-center gap-2 text-sm text-ink-soft"><Spinner className="text-brand" /> Updating…</div>}
          {res ? <ResultView r={res} stale={loading} /> : !err && <div className="py-16 text-center"><Spinner className="text-brand" /></div>}
        </section>
      </div>

      {saving && (
        <Modal wide title="Save as vehicle" onClose={() => setSaving(false)}>
          <VehicleForm initial={{ ...v, vehicle_name: "" }} submitLabel="Save vehicle"
            onSubmit={async (body) => { const created = await api.createVehicle(body); setSaving(false); setSavedMsg(`Saved "${created.vehicle_name}". Find it on the Dashboard and Vehicles pages.`); }}
            onCancel={() => setSaving(false)} />
        </Modal>
      )}
    </>
  );
}
