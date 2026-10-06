import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";

// Series colours: validated hues that stay distinguishable in light and dark mode. Direct labels / dashes carry meaning too.
export const C = { current: "#e0701f", optimized: "#0f8c6e", threshold: "#d64545", calendar: "#4f7cd1", cycling: "#c9791f", physics: "#7c8aa0", hybrid: "#0f8c6e", grid: "rgba(128,140,155,.25)", axis: "#8693a3" };
const axisProps = { stroke: C.axis, tick: { fill: C.axis, fontSize: 12 }, tickLine: false };
const niceTicks = (lo, hi, step = 10) => { const out = []; for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) out.push(t); return out; };
const tip = { contentStyle: { background: "rgb(var(--surface-raised))", border: "1px solid rgb(var(--line))", borderRadius: 8, fontSize: 12, color: "rgb(var(--ink))" } };

export function ForecastChart({ forecast }) {
  const data = forecast.years.map((y, i) => ({ year: y, current: forecast.current[i], optimized: forecast.optimized[i] }));
  const floor = Math.max(30, Math.floor(Math.min(...forecast.current, ...forecast.optimized) / 5) * 5);
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="year" type="number" domain={[0, 15]} ticks={[0, 3, 6, 9, 12, 15]} {...axisProps} label={{ value: "Years from today", position: "insideBottom", offset: -8, fill: C.axis, fontSize: 12 }} />
        <YAxis domain={[floor, 100]} ticks={niceTicks(floor, 100, floor <= 50 ? 10 : 5)} unit="%" width={48} {...axisProps} />
        <Tooltip {...tip} formatter={(v, n) => [`${Number(v).toFixed(1)}%`, n]} labelFormatter={(y) => `Year ${y}`} />
        <Legend verticalAlign="top" height={28} />
        <ReferenceLine y={forecast.reference} stroke={C.threshold} strokeDasharray="6 4" label={{ value: `${forecast.reference}% end-of-life`, fill: C.threshold, fontSize: 12, position: "insideBottomRight" }} />
        <Line name="Current habits" dataKey="current" stroke={C.current} strokeWidth={2.5} dot={false} />
        <Line name="Optimized habits" dataKey="optimized" stroke={C.optimized} strokeWidth={2.5} strokeDasharray="1 0" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Capacity loss split (percentage points of capacity) at "Today" and "In 5 years"
export function CausesChart({ causes }) {
  const data = causes.labels.map((l, i) => ({ when: l, calendar: causes.calendar[i], cycling: causes.cycling[i] }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="when" {...axisProps} />
        <YAxis unit="%" width={44} {...axisProps} />
        <Tooltip {...tip} cursor={{ fill: "rgba(128,140,155,.12)" }} formatter={(v, n) => [`${Number(v).toFixed(2)}% of capacity`, n]} />
        <Legend />
        <Bar name="Calendar aging" dataKey="calendar" stackId="a" fill={C.calendar} />
        <Bar name="Cycling aging" dataKey="cycling" stackId="a" fill={C.cycling} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ImportanceChart({ items }) {
  const data = items.slice(0, 10).map((d) => ({ feature: d.feature, importance: +(d.importance * 100).toFixed(1) }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 28)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={C.grid} horizontal={false} />
        <XAxis type="number" unit="%" {...axisProps} />
        <YAxis type="category" dataKey="feature" width={110} {...axisProps} />
        <Tooltip {...tip} cursor={{ fill: "rgba(128,140,155,.12)" }} formatter={(v) => [`${v}%`, "Importance"]} />
        <Bar dataKey="importance" fill={C.optimized} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ErrorCompareChart({ m }) {
  const data = [{ metric: "MAE", Physics: m.mae_physics, Hybrid: m.mae_hybrid }, { metric: "RMSE", Physics: m.rmse_physics, Hybrid: m.rmse_hybrid }];
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={C.grid} vertical={false} />
        <XAxis dataKey="metric" {...axisProps} />
        <YAxis unit=" pt" width={52} {...axisProps} />
        <Tooltip {...tip} cursor={{ fill: "rgba(128,140,155,.12)" }} formatter={(v, n) => [`${Number(v).toFixed(2)} SOH points`, n]} />
        <Legend />
        <Bar dataKey="Physics" fill={C.physics} radius={[4, 4, 0, 0]} />
        <Bar dataKey="Hybrid" fill={C.hybrid} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// Held-out vehicles: measured vs predicted SOH. Points on the diagonal are perfect.
export function ValidationScatter({ v }) {
  const phys = v.measured.map((m, i) => ({ measured: m, predicted: v.physics[i] }));
  const hyb = v.measured.map((m, i) => ({ measured: m, predicted: v.hybrid[i] }));
  const all = [...v.measured, ...v.physics, ...v.hybrid];
  const lo = Math.floor((Math.min(...all) - 1) / 10) * 10, hi = Math.min(100, Math.ceil((Math.max(...all) + 1) / 10) * 10), ticks = niceTicks(lo, hi, 10);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
        <CartesianGrid stroke={C.grid} />
        <XAxis type="number" dataKey="measured" domain={[lo, hi]} ticks={ticks} unit="%" {...axisProps} label={{ value: "Measured SOH", position: "insideBottom", offset: -8, fill: C.axis, fontSize: 12 }} />
        <YAxis type="number" dataKey="predicted" domain={[lo, hi]} ticks={ticks} unit="%" width={48} {...axisProps} />
        <ZAxis range={[28, 28]} />
        <ReferenceLine segment={[{ x: lo, y: lo }, { x: hi, y: hi }]} stroke={C.axis} strokeDasharray="4 4" />
        <Tooltip {...tip} formatter={(val) => `${Number(val).toFixed(1)}%`} />
        <Legend verticalAlign="top" height={28} />
        <Scatter name="Physics only" data={phys} fill={C.physics} shape="triangle" />
        <Scatter name="Physics + ML" data={hyb} fill={C.hybrid} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
