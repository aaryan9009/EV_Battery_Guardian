// Thin fetch wrapper. All physics/ML runs in the FastAPI backend; the UI only renders what comes back.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const KEY = "evg_token";

export const tokenStore = {
  get() { try { return localStorage.getItem(KEY); } catch { return null; } },
  set(t) { try { localStorage.setItem(KEY, t); } catch { /* storage unavailable: session-only */ } },
  clear() { try { localStorage.removeItem(KEY); } catch { /* ignore */ } },
};

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

export class ApiError extends Error {
  constructor(status, message, detail) { super(message); this.status = status; this.detail = detail; }
}

// FastAPI errors: {detail: "text"} | {detail: [{loc, msg}]} (validation) | {detail: {message, errors}} (CSV upload)
export function explain(detail, status) {
  if (!detail) return `Request failed (${status})`;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => `${(d.loc || []).slice(1).join(".") || "field"}: ${d.msg}`).join("; ");
  if (detail.message) return detail.message;
  return `Request failed (${status})`;
}

export async function request(path, { method = "GET", body, form, signal, auth = true } = {}) {
  const headers = {};
  const t = tokenStore.get();
  if (auth && t) headers.Authorization = `Bearer ${t}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  let res;
  try { res = await fetch(`${BASE}/api${path}`, { method, headers, body: payload, signal }); }
  catch (e) {
    if (e.name === "AbortError") throw e;
    throw new ApiError(0, "Cannot reach the server. Check that the backend is running and VITE_API_URL is correct.");
  }
  if (res.status === 204) return null;
  const ctype = res.headers.get("content-type") || "";
  const data = ctype.includes("json") ? await res.json().catch(() => null) : await res.text();
  if (!res.ok) {
    const detail = data && typeof data === "object" ? data.detail : undefined;
    if (res.status === 401 && auth && t) onUnauthorized();
    throw new ApiError(res.status, explain(detail, res.status), detail);
  }
  return data;
}

export const api = {
  meta: () => request("/meta", { auth: false }),
  health: () => request("/health", { auth: false }),
  register: (b) => request("/auth/register", { method: "POST", body: b, auth: false }),
  login: (b) => request("/auth/login", { method: "POST", body: b, auth: false }),
  me: () => request("/auth/me"),
  vehicles: () => request("/vehicles"),
  createVehicle: (b) => request("/vehicles", { method: "POST", body: b }),
  updateVehicle: (id, b) => request(`/vehicles/${id}`, { method: "PUT", body: b }),
  deleteVehicle: (id) => request(`/vehicles/${id}`, { method: "DELETE" }),
  measurements: (id) => request(`/vehicles/${id}/measurements`),
  addMeasurement: (id, b) => request(`/vehicles/${id}/measurements`, { method: "POST", body: b }),
  analyzeVehicle: (id, opts, signal) => request(`/vehicles/${id}/analyze`, { method: "POST", body: opts, signal }),
  history: (id) => request(`/vehicles/${id}/predictions?limit=20`),
  prediction: (id) => request(`/predictions/${id}`),
  analyze: (b, signal) => request("/analyze", { method: "POST", body: b, signal }),
  mlStatus: () => request("/ml/status"),
  mlMetrics: () => request("/ml/metrics"),
  mlModels: () => request("/ml/models"),
  mlTrain: (b) => request("/ml/train", { method: "POST", body: b }),
  datasets: () => request("/fleet/datasets"),
  uploadFleet: (file, name, skipInvalid) => {
    const f = new FormData(); f.append("file", file); if (name) f.append("name", name);
    return request(`/fleet/upload?skip_invalid=${skipInvalid ? "true" : "false"}`, { method: "POST", form: f });
  },
  deleteDataset: (id) => request(`/fleet/datasets/${id}`, { method: "DELETE" }),
  templateUrl: () => `${BASE}/api/fleet/template`,
};
