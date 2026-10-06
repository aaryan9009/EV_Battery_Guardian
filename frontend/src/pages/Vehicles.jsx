import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useMeta } from "../components/Meta";
import { useVehicles } from "../components/useVehicles";
import VehicleForm from "../components/VehicleForm";
import { Empty, ErrorBox, Modal, PageHeader, Spinner } from "../components/ui";
import { emptyVehicle } from "../lib/vehicleFields";
import { num } from "../lib/format";

export default function Vehicles() {
  const { meta } = useMeta();
  const { vehicles, error, reload } = useVehicles();
  const [editing, setEditing] = useState(null);       // {} = new, vehicle = edit
  const [deleting, setDeleting] = useState(null), [delErr, setDelErr] = useState("");

  if (vehicles === null || !meta) return <div className="py-20 text-center"><Spinner /></div>;

  const save = async (body) => {
    if (editing.id) await api.updateVehicle(editing.id, body); else await api.createVehicle(body);
    setEditing(null); reload();
  };
  const remove = async () => {
    try { await api.deleteVehicle(deleting.id); setDeleting(null); setDelErr(""); reload(); }
    catch (e) { setDelErr(e.message); }
  };

  return (
    <>
      <PageHeader title="Vehicles" subtitle="Your saved vehicles. Dashboard analyses use these."
        actions={<button className="btn-primary" onClick={() => setEditing({ ...emptyVehicle(meta) })}>+ Add vehicle</button>} />
      <ErrorBox>{error}</ErrorBox>
      {!vehicles.length ? <Empty title="No vehicles yet">Add one to see its battery health on the dashboard.</Empty> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {vehicles.map((v) => (
            <div key={v.id} className="card flex flex-col">
              <div className="flex items-start justify-between gap-2"><h3 className="font-semibold">{v.vehicle_name}</h3>
                <span className="shrink-0 rounded bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand">{v.battery_chemistry}</span></div>
              <p className="text-sm text-ink-soft">{v.vehicle_type}</p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                {[["Capacity", `${v.battery_capacity_kwh} kWh`], ["Age", `${v.vehicle_age_years} yr`], ["Odometer", `${num(v.odometer_km)} km`], ["Per year", `${num(v.distance_per_year_km)} km`],
                  ["Fast charging", `${v.dc_fast_pct}%`], ["Charge limit", `${v.daily_charge_limit}%`]].map(([k, val]) => <div key={k}><dt className="text-xs text-ink-soft">{k}</dt><dd className="font-medium tabular-nums">{val}</dd></div>)}
              </dl>
              <div className="mt-4 flex gap-2 pt-1">
                <Link to="/" onClick={() => { try { localStorage.setItem("evg_selected_vehicle", String(v.id)); } catch { /* ignore */ } }} className="btn-ghost flex-1 !py-1.5">Analyse</Link>
                <button className="btn-ghost !py-1.5" onClick={() => setEditing(v)}>Edit</button>
                <button className="btn-danger !py-1.5" onClick={() => { setDelErr(""); setDeleting(v); }}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {editing && (
        <Modal wide title={editing.id ? "Edit vehicle" : "Add vehicle"} onClose={() => setEditing(null)}>
          <VehicleForm initial={editing} onSubmit={save} onCancel={() => setEditing(null)} submitLabel={editing.id ? "Save changes" : "Add vehicle"} />
        </Modal>
      )}
      {deleting && (
        <Modal title="Delete vehicle?" onClose={() => setDeleting(null)}>
          <p className="mb-4 text-sm">This permanently deletes <b>{deleting.vehicle_name}</b> together with its measurements and saved predictions.</p>
          <ErrorBox>{delErr}</ErrorBox>
          <div className="mt-4 flex justify-end gap-2"><button className="btn-ghost" onClick={() => setDeleting(null)}>Cancel</button><button className="btn-danger" onClick={remove}>Delete</button></div>
        </Modal>
      )}
    </>
  );
}
