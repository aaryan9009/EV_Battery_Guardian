import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";

export function useVehicles() {
  const [vehicles, setVehicles] = useState(null);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    try { setVehicles(await api.vehicles()); setError(""); } catch (e) { setError(e.message); setVehicles((v) => v ?? []); }
  }, []);
  useEffect(() => { reload(); }, [reload]);
  return { vehicles, error, reload };
}
