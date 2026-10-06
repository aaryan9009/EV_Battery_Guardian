import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";

// /api/meta is the single source of truth for presets, chemistries, cooling options and field limits.
const Ctx = createContext({ meta: null, error: null });
export const useMeta = () => useContext(Ctx);

export function MetaProvider({ children }) {
  const [state, setState] = useState({ meta: null, error: null });
  useEffect(() => { api.meta().then((meta) => setState({ meta, error: null })).catch((e) => setState({ meta: null, error: e.message })); }, []);
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}
