import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../components/Auth";
import { ErrorCompareChart, ImportanceChart, ValidationScatter } from "../components/Charts";
import { Empty, ErrorBox, Field, Notice, PageHeader, Spinner } from "../components/ui";
import { date, num } from "../lib/format";

function Stat({ label, value, sub }) {
  return <div className="card"><div className="label">{label}</div><div className="text-2xl font-bold tabular-nums">{value}</div>{sub && <div className="mt-1 text-xs text-ink-soft">{sub}</div>}</div>;
}

function UploadPanel({ datasets, onChanged }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null), [name, setName] = useState(""), [skip, setSkip] = useState(false), [kind, setKind] = useState("gbt");
  const [dsId, setDsId] = useState(""), [busy, setBusy] = useState(""), [err, setErr] = useState(null), [ok, setOk] = useState("");

  const upload = async () => {
    setErr(null); setOk(""); setBusy("upload");
    try {
      const r = await api.uploadFleet(file, name.trim(), skip);
      setOk(`Imported ${num(r.rows_imported)} of ${num(r.rows_in_file)} rows` + (r.rows_skipped ? ` (${r.rows_skipped} skipped)` : "") + ".");
      setDsId(String(r.dataset.id)); setFile(null); setName(""); if (fileRef.current) fileRef.current.value = "";
      onChanged();
    } catch (e) { setErr(e); } finally { setBusy(""); }
  };
  const train = async () => {
    setErr(null); setOk(""); setBusy("train");
    try { const r = await api.mlTrain({ dataset_id: dsId ? Number(dsId) : null, kind }); setOk(r.banner); onChanged(); }
    catch (e) { setErr(e); } finally { setBusy(""); }
  };
  const detail = err?.detail && typeof err.detail === "object" && !Array.isArray(err.detail) ? err.detail : null;

  return (
    <div className="card space-y-5">
      <h3 className="h-section !mb-0">Fleet data & training (admin)</h3>
      {ok && <Notice tone="ok">{ok}</Notice>}
      {err && <ErrorBox>{err.message}</ErrorBox>}
      {detail?.errors?.length > 0 && (
        <div className="max-h-48 overflow-auto rounded-lg border border-line text-xs">
          <table className="w-full"><thead className="sticky top-0 bg-surface text-left"><tr><th className="p-2">Row</th><th>Column</th><th>Value</th><th>Problem</th></tr></thead>
            <tbody>{detail.errors.map((e, i) => <tr key={i} className="border-t border-line"><td className="p-2">{e.row}</td><td>{e.column}</td><td>{String(e.value)}</td><td>{e.message || e.error}</td></tr>)}</tbody></table>
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-3">
          <p className="text-sm font-medium">1. Upload a real fleet / BMS CSV</p>
          <input ref={fileRef} type="file" accept=".csv,text/csv" className="input" onChange={(e) => setFile(e.target.files[0] || null)} />
          <Field label="Dataset name (optional)"><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Pune taxi fleet 2026" /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={skip} onChange={(e) => setSkip(e.target.checked)} />Skip invalid rows instead of rejecting the file</label>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" disabled={!file || !!busy} onClick={upload}>{busy === "upload" ? "Uploading…" : "Upload"}</button>
            <a className="btn-ghost" href={api.templateUrl()} download>Download template (synthetic)</a>
          </div>
        </div>
        <div className="space-y-3">
          <p className="text-sm font-medium">2. Train the model</p>
          <Field label="Dataset"><select className="input" value={dsId} onChange={(e) => setDsId(e.target.value)}>
            <option value="">Newest uploaded (else simulated)</option>
            {datasets.map((d) => <option key={d.id} value={d.id}>#{d.id} · {d.name} · {d.source} · {num(d.n_rows)} rows</option>)}</select></Field>
          <Field label="Algorithm"><select className="input" value={kind} onChange={(e) => setKind(e.target.value)}><option value="gbt">Gradient boosting</option><option value="ridge">Ridge regression</option></select></Field>
          <button className="btn-primary" disabled={!!busy} onClick={train}>{busy === "train" ? <><Spinner /> Training…</> : "Train model"}</button>
          <p className="text-xs text-ink-soft">The new model is activated immediately and used for every new analysis.</p>
        </div>
      </div>
    </div>
  );
}

export default function MLModel() {
  const { user } = useAuth();
  const [status, setStatus] = useState(null), [metrics, setMetrics] = useState(null), [models, setModels] = useState([]), [datasets, setDatasets] = useState([]);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const s = await api.mlStatus(); setStatus(s);
      const [m, list, ds] = await Promise.all([s.trained ? api.mlMetrics() : null, api.mlModels(), api.datasets()]);
      setMetrics(m); setModels(list); setDatasets(ds); setErr("");
    } catch (e) { setErr(e.message); setStatus((s) => s ?? { trained: false }); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (!status) return <div className="py-20 text-center"><Spinner /></div>;
  const simulated = status.active_model?.data_source === "simulated";

  return (
    <>
      <PageHeader title="ML Model" subtitle="A residual model that corrects the physics SOH. Evaluated on vehicles it never saw during training." />
      <div className="mb-4 space-y-2">
        <ErrorBox>{err}</ErrorBox>
        {status.training_in_progress && <Notice tone="info"><Spinner className="mr-2" />A model is currently being trained…</Notice>}
        {status.trained
          ? <Notice tone={simulated ? "warn" : "ok"}><b>ML Model Status:</b> {status.banner}{simulated && " Upload a real fleet dataset to replace it."}</Notice>
          : <Notice tone="warn"><b>ML Model Status:</b> {status.banner}</Notice>}
      </div>

      {metrics ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
            <Stat label="Training vehicles" value={num(metrics.dataset.n_vehicles)} sub={`final model uses all; ${num(metrics.n_vehicles_test)} held out for the metrics`} />
            <Stat label="Training rows" value={num(metrics.dataset.n_rows)} sub={`${num(metrics.n_test)} held-out rows scored`} />
            <Stat label="Physics MAE" value={metrics.mae_physics.toFixed(2)} sub="SOH points" />
            <Stat label="Hybrid MAE" value={metrics.mae_hybrid.toFixed(2)} sub="SOH points" />
            <Stat label="Physics RMSE" value={metrics.rmse_physics.toFixed(2)} sub="SOH points" />
            <Stat label="Hybrid RMSE" value={metrics.rmse_hybrid.toFixed(2)} sub="SOH points" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="card"><h3 className="h-section">Physics vs hybrid error</h3><ErrorCompareChart m={metrics} /><p className="mt-2 text-xs text-ink-soft">Lower is better. {metrics.split}.</p></div>
            <div className="card"><h3 className="h-section">Measured vs predicted SOH (held-out)</h3><ValidationScatter v={metrics.validation} /><p className="mt-2 text-xs text-ink-soft">Points closer to the dashed diagonal are more accurate.</p></div>
            <div className="card"><h3 className="h-section">Feature importance</h3><ImportanceChart items={metrics.feature_importance} /></div>
          </div>
          <div className="card text-sm"><span className="text-ink-soft">Active model</span> #{metrics.model_id} · {metrics.kind === "gbt" ? "gradient boosting" : metrics.kind} · dataset “{metrics.dataset.name}” ({num(metrics.dataset.n_rows)} rows, {num(metrics.dataset.n_vehicles)} vehicles) · trained {date(metrics.trained_at)}</div>
        </div>
      ) : !err && <Empty title="No metrics yet">Train a model to see its accuracy.</Empty>}

      <div className="mt-4 grid gap-4">
        <div className="card overflow-x-auto">
          <h3 className="h-section">Training history</h3>
          {models.length ? (
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-ink-soft"><tr>{["Model", "Trained", "Algorithm", "Data", "Hybrid MAE", "Hybrid RMSE", ""].map((h) => <th key={h} className="py-2 pr-4 font-medium">{h}</th>)}</tr></thead>
              <tbody className="divide-y divide-line tabular-nums">{models.map((m) => (
                <tr key={m.model_id}><td className="py-2 pr-4">#{m.model_id}</td><td className="pr-4">{date(m.trained_at)}</td><td className="pr-4">{m.kind}</td><td className="pr-4">{m.data_source}</td>
                  <td className="pr-4">{m.mae_hybrid.toFixed(2)}</td><td className="pr-4">{m.rmse_hybrid.toFixed(2)}</td><td>{m.is_active && <span className="rounded bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand">active</span>}</td></tr>))}</tbody>
            </table>
          ) : <p className="text-sm text-ink-soft">No models trained yet.</p>}
        </div>
        {user.role === "admin"
          ? <UploadPanel datasets={datasets} onChanged={load} />
          : <Notice tone="info">Uploading fleet data and retraining the model is limited to administrators. Admin emails are configured on the server (<code>ADMIN_EMAILS</code>).</Notice>}
      </div>
    </>
  );
}
