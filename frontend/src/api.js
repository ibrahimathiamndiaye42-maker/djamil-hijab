const BASE = import.meta.env.VITE_API_URL || "/api/v1";
export const getToken = () => localStorage.getItem("dh_token");
export const setToken = (t) => (t ? localStorage.setItem("dh_token", t) : localStorage.removeItem("dh_token"));

async function request(path, { method = "GET", body, params, form, blob } = {}) {
  const qs = params ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null)) : "";
  const headers = {};
  if (getToken()) headers.Authorization = `Bearer ${getToken()}`;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(BASE + path + qs, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) });
  if (res.status === 401 && getToken()) { setToken(null); window.dispatchEvent(new Event("dh-logout")); }
  if (!res.ok) {
    let msg = "Erreur serveur";
    try { msg = (await res.json()).error || msg; } catch { /* ignore */ }
    throw new Error(msg);
  }
  return blob ? res.blob() : res.json();
}
export const api = request;
export const uploadImage = (file, folder = "products") => {
  const form = new FormData(); form.append("file", file);
  return request("/uploads/image", { method: "POST", form, params: { folder } });
};
export async function openPdf(invoiceId) {
  const b = await request(`/invoices/${invoiceId}/pdf`, { blob: true });
  window.open(URL.createObjectURL(b), "_blank");
}
