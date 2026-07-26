const BASE = "/api";
const TOKEN_KEY = "allocnce_token";

// Renseigné par AuthProvider : purge la session dès qu'une 401 remonte.
let onUnauthorized = null;
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export function formatAllocOption(alloc) {
  const d = new Date(alloc.created_at + "Z");
  const day   = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const h     = String(d.getHours()).padStart(2, "0");
  const min   = String(d.getMinutes()).padStart(2, "0");
  return `${alloc.label}  (créée le ${day}/${month} à ${h}h${min})`;
}

function authHeaders(extra = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra };
}

async function errorMessage(res) {
  const err = await res.json().catch(() => ({ detail: res.statusText }));
  const detail = err.detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
  if (typeof detail === "string") return detail;
  return res.statusText;
}

async function handle(res) {
  if (res.status === 401) {
    const message = await errorMessage(res);
    if (onUnauthorized) onUnauthorized();
    throw new Error(message || "Session expirée");
  }
  if (!res.ok) throw new Error((await errorMessage(res)) || res.statusText);
  return res;
}

async function request(path, options = {}) {
  const res = await handle(
    await fetch(`${BASE}${path}`, { ...options, headers: authHeaders(options.headers) })
  );
  return res.status === 204 ? null : res.json();
}

/** Déclenche l'enregistrement d'un Blob sous `filename`. */
function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  // --- Authentification ---
  login: async (email, password) => {
    // /auth/login attend un form OAuth2 (username = email), pas du JSON.
    const body = new URLSearchParams({ username: email, password });
    const res = await handle(
      await fetch(`${BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      })
    );
    return res.json();
  },
  register: (payload) =>
    request("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  updateMe: (payload) =>
    request("/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  // --- Administration ---
  listUsers: () => request("/admin/users"),
  createUser: (payload) =>
    request("/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  updateUser: (id, payload) =>
    request(`/admin/users/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  deactivateUser: (id) => request(`/admin/users/${id}`, { method: "DELETE" }),
  adminStats: () => request("/admin/stats"),

  adminAllocations: ({ userId, date, limit = 50, offset = 0 } = {}) => {
    const p = new URLSearchParams({ limit, offset });
    if (userId) p.set("user_id", userId);
    if (date) p.set("date", date);
    return request(`/admin/allocations?${p}`);
  },
  adminDeleteAllocation: (id) =>
    request(`/admin/allocations/${id}`, { method: "DELETE" }),

  /** Aperçu d'une allocation appartenant à n'importe quel utilisateur. */
  adminPreviewAllocation: async (id) => {
    const res = await handle(
      await fetch(`${BASE}/admin/allocations/${id}/preview`, { headers: authHeaders() })
    );
    return res.text();
  },
  adminDownloadAllocation: async (id, label) => {
    const res = await handle(
      await fetch(`${BASE}/admin/allocations/${id}/download`, { headers: authHeaders() })
    );
    saveBlob(await res.blob(), `${label}.docx`);
  },

  // --- Allocations ---
  getAllocations: () => request("/allocations/"),
  createAllocation: (fd) => request("/allocations/create", { method: "POST", body: fd }),
  createPrealloc: (fd) => request("/allocations/prealloc", { method: "POST", body: fd }),
  createFinale: (fd) => request("/allocations/finale", { method: "POST", body: fd }),
  updateWithPdf: (id, fd) => request(`/allocations/${id}/update`, { method: "POST", body: fd }),
  deleteAllocation: (id) => request(`/allocations/${id}`, { method: "DELETE" }),

  /** Aperçu HTML du DOCX (fragment, pas du JSON). */
  previewAllocation: async (id) => {
    const res = await handle(
      await fetch(`${BASE}/allocations/${id}/preview`, { headers: authHeaders() })
    );
    return res.text();
  },

  /** Télécharge le DOCX. Un <a download> ne peut pas porter d'en-tête
   *  Authorization : on récupère le blob puis on l'enregistre. */
  downloadAllocation: async (id, label) => {
    const res = await handle(
      await fetch(`${BASE}/allocations/${id}/download`, { headers: authHeaders() })
    );
    saveBlob(await res.blob(), `${label}.docx`);
  },
};
