import { useEffect } from "react";

export function Spinner({ className = "" }) {
  return <span className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`} role="status" aria-label="Loading" />;
}
export function ErrorBox({ children }) {
  if (!children) return null;
  return <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-300">{children}</div>;
}
export function Notice({ tone = "info", children }) {
  const t = { info: "border-sky-500/30 bg-sky-500/10 text-sky-800 dark:text-sky-200", warn: "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200", ok: "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200" }[tone];
  return <div className={`rounded-lg border px-3 py-2 text-sm ${t}`}>{children}</div>;
}
export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-2xl font-bold tracking-tight">{title}</h1>{subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}</div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
export function Empty({ title, children }) {
  return <div className="card py-10 text-center"><p className="font-medium">{title}</p><div className="mt-2 text-sm text-ink-soft">{children}</div></div>;
}
export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const k = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={title} className={`card my-8 w-full ${wide ? "max-w-3xl" : "max-w-md"}`}>
        <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2>
          <button className="text-ink-soft hover:text-ink" onClick={onClose} aria-label="Close">✕</button></div>
        {children}
      </div>
    </div>
  );
}
export function Field({ label, children, hint }) {
  return <label className="block"><span className="label">{label}</span>{children}{hint && <span className="mt-1 block text-xs text-ink-soft">{hint}</span>}</label>;
}
