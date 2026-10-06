export const pct = (v, d = 1) => (v == null ? "–" : `${Number(v).toFixed(d)}%`);
export const signedPct = (v, d = 1) => (v == null ? "–" : `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(d)}%`);
export const yrs = (v, d = 1) => (v == null ? "–" : `${Number(v).toFixed(d)} yr`);
export const num = (v, d = 0) => (v == null ? "–" : Number(v).toLocaleString(undefined, { maximumFractionDigits: d }));
export const date = (s) => (s ? new Date(s).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "–");

// Life to 80 %: when the 80 % line is not reached inside the 15-year horizon the backend returns 15 with reached=false.
export const lifeText = (years, reached) => (reached ? yrs(years, 1) : `> ${yrs(years, 0)}`);
export const gainText = (gain, optReached, curReached) => (!curReached ? "n/a" : `${optReached ? "+" : "≥ +"}${Number(gain).toFixed(1)} yr`);

export const RISK_STYLE = {
  LOW: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  MODERATE: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  HIGH: "bg-red-500/15 text-red-700 dark:text-red-300",
};
export const SOURCE_STYLE = {
  measured: { dot: "bg-sky-500", text: "Measured SOH" },
  physics_ml: { dot: "bg-emerald-500", text: "Physics + ML" },
  physics_only: { dot: "bg-slate-400", text: "Physics only" },
};
