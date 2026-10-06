import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, setUnauthorizedHandler, tokenStore } from "../lib/api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);
  useEffect(() => { setUnauthorizedHandler(logout); }, [logout]);

  useEffect(() => {              // restore session
    let alive = true;
    if (!tokenStore.get()) { setReady(true); return; }
    api.me().then((u) => alive && setUser(u)).catch(() => tokenStore.clear()).finally(() => alive && setReady(true));
    return () => { alive = false; };
  }, []);

  const accept = (t) => { tokenStore.set(t.access_token); setUser(t.user); };
  const value = useMemo(() => ({
    user, ready, logout,
    login: async (email, password) => accept(await api.login({ email, password })),
    register: async (name, email, password) => accept(await api.register({ name, email, password })),
  }), [user, ready, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function RequireAuth({ children }) {
  const { user, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return <div className="p-10 text-center text-sm text-ink-soft">Loading…</div>;
  return user ? children : <Navigate to="/login" replace state={{ from: loc.pathname }} />;
}
