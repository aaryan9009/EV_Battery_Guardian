import { useState } from "react";
import { useMeta } from "./Meta";
import { ErrorBox, Field } from "./ui";
import { CUSTOM, FIELDS, fromPreset } from "../lib/vehicleFields";

// Presets, chemistries, cooling options and numeric limits all come from /api/meta.
export default function VehicleForm({ initial, onSubmit, onCancel, submitLabel = "Save vehicle" }) {
  const { meta } = useMeta();
  const [v, setV] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k, val) => setV((p) => ({ ...p, [k]: val, ...(k !== "vehicle_name" && k !== "vehicle_type" ? { vehicle_type: CUSTOM } : {}) }));
  const lim = (k) => meta.limits[k] || {};

  const pickPreset = (name) => {
    const p = meta.presets.find((x) => x.name === name);
    if (p?.values) setV((cur) => ({ ...cur, ...fromPreset(p) }));      // keeps the user's vehicle name
    else setV((cur) => ({ ...cur, vehicle_type: CUSTOM }));
  };

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const body = { ...v }; FIELDS.forEach((f) => { body[f.key] = Number(body[f.key]); });
      await onSubmit(body);
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <ErrorBox>{err}</ErrorBox>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Vehicle name"><input className="input" required maxLength={120} value={v.vehicle_name} onChange={(e) => set("vehicle_name", e.target.value)} placeholder="e.g. Office Nexon EV" /></Field>
        <Field label="Vehicle preset">
          <select className="input" value={v.vehicle_type} onChange={(e) => pickPreset(e.target.value)}>{meta.presets.map((p) => <option key={p.name}>{p.name}</option>)}</select>
        </Field>
        <Field label="Chemistry">
          <select className="input" value={v.battery_chemistry} onChange={(e) => set("battery_chemistry", e.target.value)}>{meta.chemistries.map((c) => <option key={c.name}>{c.name}</option>)}</select>
        </Field>
        <Field label="Cooling">
          <select className="input" value={v.cooling_type} onChange={(e) => set("cooling_type", e.target.value)}>{meta.cooling.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>
        </Field>
        {FIELDS.map((f) => (
          <Field key={f.key} label={`${f.label} (${f.unit})`} hint={lim(f.key).min != null ? `${lim(f.key).min} – ${lim(f.key).max}` : undefined}>
            <input className="input tabular-nums" type="number" required step={f.step} min={lim(f.key).min} max={lim(f.key).max} value={v[f.key]} onChange={(e) => set(f.key, e.target.value)} />
          </Field>
        ))}
      </div>
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>}
        <button className="btn-primary" disabled={busy}>{busy ? "Saving…" : submitLabel}</button>
      </div>
    </form>
  );
}
