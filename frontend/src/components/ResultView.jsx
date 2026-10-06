import { CausesChart, ForecastChart } from "./Charts";
import { Notice } from "./ui";
import { RISK_STYLE, SOURCE_STYLE, gainText, lifeText, num, pct, signedPct } from "../lib/format";

function Kpi({ label, value, sub, children, big }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className={`${big ? "text-4xl" : "text-2xl"} font-bold tabular-nums tracking-tight`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-ink-soft">{sub}</div>}
      {children}
    </div>
  );
}

export function SourceBadge({ source, label }) {
  const s = SOURCE_STYLE[source] || SOURCE_STYLE.physics_only;
  return <span className="mt-2 inline-flex items-center gap-2 rounded-full bg-surface px-2.5 py-1 text-xs font-medium"><span className={`h-2 w-2 rounded-full ${s.dot}`} aria-hidden />{label || s.text}</span>;
}

// "Physics SOH 91.8% / ML correction +0.8% / Final SOH 92.6%": the backend deliberately exposes where the SOH came from.
function SohBreakdown({ r }) {
  const rows = r.soh_source === "measured"
    ? [["Physics SOH", pct(r.physics_soh), "model estimate, not used"], ["Measured SOH", pct(r.current_soh), "physics re-anchored to this value"], ["ML correction", "not applied", "measured SOH takes priority"]]
    : [["Physics SOH", pct(r.physics_soh)], ["ML correction", r.ml_correction == null ? "none" : signedPct(r.ml_correction)], ["Final SOH", pct(r.current_soh)]];
  return (
    <div className="card">
      <h3 className="h-section">How the SOH was obtained</h3>
      <dl className="divide-y divide-line text-sm">
        {rows.map(([k, v, note], i) => (
          <div key={k} className={`flex items-baseline justify-between py-2 ${i === rows.length - 1 && r.soh_source !== "measured" ? "font-semibold" : ""}`}>
            <dt className="text-ink-soft">{k}{note && <span className="ml-2 text-xs">({note})</span>}</dt><dd className="tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
      {r.soh_error_band != null && <p className="mt-2 text-xs text-ink-soft">Typical ML error on unseen vehicles: ±{r.soh_error_band} SOH points (RMSE).</p>}
      {r.anchor_scale !== 1 && <p className="mt-1 text-xs text-ink-soft">Aging re-scaled ×{r.anchor_scale} to match the anchored SOH.</p>}
    </div>
  );
}

function RiskFactors({ risk }) {
  const per = Math.max(2, ...risk.factors.map((f) => f.points));
  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between"><h3 className="h-section !mb-0">Battery risk factors</h3>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${RISK_STYLE[risk.level]}`}>{risk.level} · {risk.score}/{risk.max_score}</span></div>
      <ul className="space-y-3">
        {risk.factors.map((f) => (
          <li key={f.name}>
            <div className="flex justify-between text-sm"><span className="font-medium">{f.name}</span><span className="tabular-nums text-ink-soft">{f.value} {f.unit}</span></div>
            <div className="mt-1 flex gap-1" role="img" aria-label={`${f.points} of ${per} risk points`}>
              {Array.from({ length: per }, (_, i) => <span key={i} className={`h-2 flex-1 rounded-full ${i < f.points ? (f.points >= per ? "bg-red-500" : "bg-amber-500") : "bg-line"}`} />)}
            </div>
            <p className="mt-1 text-xs text-ink-soft">{f.detail}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

const PRIORITY = { high: "bg-red-500/15 text-red-700 dark:text-red-300", medium: "bg-amber-500/15 text-amber-700 dark:text-amber-300", info: "bg-sky-500/15 text-sky-700 dark:text-sky-300" };

export default function ResultView({ r, stale }) {
  const d = r.details;
  return (
    <div className={`space-y-4 transition-opacity ${stale ? "opacity-60" : ""}`}>
      {r.warnings.length > 0 && <div className="space-y-2">{r.warnings.map((w) => <Notice key={w} tone="warn">{w}</Notice>)}</div>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <div className="col-span-2 lg:col-span-1"><Kpi big label="Current SOH" value={pct(r.current_soh)}><SourceBadge source={r.soh_source} label={r.soh_source_label} /></Kpi></div>
        <Kpi label="Life to 80%" value={lifeText(r.life_years, r.life_reached)} sub={r.life_reached ? `≈ ${num(r.life_km)} km at current use` : "not reached within 15 years"} />
        <Kpi label="Battery risk" value={<span className={`rounded-lg px-2 py-0.5 text-xl ${RISK_STYLE[r.risk.level]}`}>{r.risk.level}</span>} sub={`score ${r.risk.score} of ${r.risk.max_score}`} />
        <Kpi label="Optimized life gain" value={gainText(r.life_gained_years, r.life_optimized_reached, r.life_reached)} sub={`optimized life ${lifeText(r.life_optimized_years, r.life_optimized_reached)}`} />
        <Kpi label="EFC" value={num(r.efc)} sub={`${num(r.efc_per_year)} cycles / year`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <h3 className="h-section">SOH forecast</h3>
          <ForecastChart forecast={r.forecast} />
        </div>
        <SohBreakdown r={r} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card">
          <h3 className="h-section">Aging causes</h3>
          <CausesChart causes={r.causes} />
          <p className="mt-2 text-xs text-ink-soft">{Math.round(r.calendar_share * 100)}% of aging so far is time-driven (calendar), {Math.round((1 - r.calendar_share) * 100)}% is usage-driven (cycling).</p>
        </div>
        <RiskFactors risk={r.risk} />
        <div className="card">
          <h3 className="h-section">Operating conditions</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {[["AC C-rate", d.ac_c_rate], ["Avg DC C-rate", d.dc_c_rate_avg], ["Cell temp", `${d.cell_temp_c} °C`], ["Resting SOC", `${d.resting_soc}%`], ["Depth of discharge", `${d.dod}%`], ["Charging stress", `×${d.charging_stress}`], ["SOC stress", `×${d.soc_stress}`]].map(([k, v]) => (
              <div key={k}><dt className="text-xs text-ink-soft">{k}</dt><dd className="font-medium tabular-nums">{v}</dd></div>
            ))}
          </dl>
        </div>
      </div>

      <div className="card">
        <h3 className="h-section">Recommendations</h3>
        <ul className="space-y-2">
          {r.recommendations.map((x) => (
            <li key={x.kind} className="flex items-start gap-3 text-sm">
              <span className={`mt-0.5 shrink-0 rounded px-2 py-0.5 text-xs font-semibold uppercase ${PRIORITY[x.priority]}`}>{x.priority}</span><span>{x.text}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
