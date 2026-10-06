import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "./Auth";

const links = [["/", "Dashboard"], ["/vehicles", "Vehicles"], ["/analysis", "Analysis"], ["/ml", "ML Model"]];

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-line bg-surface-raised/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-2 font-bold"><span className="grid h-7 w-7 place-items-center rounded-md bg-brand text-white" aria-hidden>⚡</span>EV Battery Guardian</div>
          <nav className="flex flex-1 gap-1 text-sm" aria-label="Main">
            {links.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"}
                className={({ isActive }) => `rounded-lg px-3 py-1.5 font-medium transition ${isActive ? "bg-brand-soft text-brand" : "text-ink-soft hover:text-ink"}`}>{label}</NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-ink-soft sm:inline">{user.name}{user.role === "admin" && <span className="ml-2 rounded bg-brand-soft px-1.5 py-0.5 text-xs font-medium text-brand">admin</span>}</span>
            <button className="btn-ghost !py-1.5" onClick={logout}>Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6"><Outlet /></main>
    </div>
  );
}
