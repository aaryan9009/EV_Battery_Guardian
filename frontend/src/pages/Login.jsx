import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../components/Auth";
import { ErrorBox, Field } from "../components/ui";

export default function Login() {
  const { user, login, register } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={loc.state?.from || "/"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await login(f.email, f.password);
      else await register(f.name, f.email, f.password);
      nav(loc.state?.from || "/", { replace: true });
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="min-h-screen w-full bg-[#f8fafc] text-slate-800 flex items-center justify-center p-4 font-sans antialiased">
      <div className="w-full max-w-md">
        
        {/* Brand Header matching top navbar style */}
        <div className="mb-6 text-center">
          <div
            className="mx-auto mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600 text-2xl text-white shadow-sm"
            aria-hidden="true"
          >
            ⚡
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            EV Battery Guardian
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Hybrid physics + ML battery health, life and risk.
          </p>
        </div>

        {/* Form Card matching dashboard white card components */}
        <div className="rounded-2xl bg-white p-6 sm:p-8 shadow-sm border border-slate-200/80">
          
          {/* Mode Switcher Tabs (Matching Dashboard 'Analysis' Pill/Tab style) */}
          <div
            className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100/80 p-1 text-sm font-medium mb-6"
            role="tablist"
          >
            {[
              ["login", "Sign in"],
              ["register", "Create account"],
            ].map(([m, l]) => (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={mode === m}
                onClick={() => {
                  setMode(m);
                  setErr("");
                }}
                className={`rounded-lg py-2 text-center text-xs font-semibold transition-all duration-150 ${
                  mode === m
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                }`}
              >
                {l}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            <ErrorBox>{err}</ErrorBox>

            {mode === "register" && (
              <Field label="Name">
                <input
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 transition-colors"
                  placeholder="Your full name"
                  required
                  maxLength={120}
                  value={f.name}
                  onChange={up("name")}
                  autoComplete="name"
                />
              </Field>
            )}

            <Field label="Email">
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 transition-colors"
                type="email"
                placeholder="name@example.com"
                required
                value={f.email}
                onChange={up("email")}
                autoComplete="email"
              />
            </Field>

            <Field
              label="Password"
              hint={mode === "register" ? "8–72 characters" : undefined}
            >
              <div className="relative mt-1">
                <input
                  className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3.5 py-2.5 pr-10 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 transition-colors"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  required
                  minLength={mode === "register" ? 8 : 1}
                  maxLength={72}
                  value={f.password}
                  onChange={up("password")}
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="h-4 w-4"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3.98 8.98A10.477 10.477 0 0 0 2.25 12c1.5 3.5 5.2 6 9.75 6a9.7 9.7 0 0 0 5.02-1.4M6.23 6.23A9.8 9.8 0 0 1 12 4c4.55 0 8.25 2.5 9.75 6a10.5 10.5 0 0 1-2.14 3.19M6.23 6.23 3 3m3.23 3.23 3.11 3.11m5.66 5.66L21 21m-5.99-5.99a3.5 3.5 0 0 1-4.95-4.95"
                      />
                    </svg>
                  ) : (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="h-4 w-4"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M2.25 12s3.75-6 9.75-6 9.75 6 9.75 6-3.75 6-9.75 6-9.75-6-9.75-6Z"
                      />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </Field>

            <button
              type="submit"
              className="mt-2 w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 active:bg-emerald-800 transition-colors disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
              disabled={busy}
            >
              {busy ? (
                <>
                  <svg
                    className="animate-spin h-4 w-4 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  <span>Please wait…</span>
                </>
              ) : mode === "login" ? (
                "Sign in"
              ) : (
                "Create account"
              )}
            </button>
          </form>
        </div>

        {/* Dashboard Footer Note */}
        <p className="mt-6 text-center text-xs text-slate-400">
          Powered by EV Battery Guardian Predictive Engine
        </p>
      </div>
    </div>
  );
}