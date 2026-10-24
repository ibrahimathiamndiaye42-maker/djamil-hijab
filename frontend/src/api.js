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

/** Envoie la facture PDF au client par WhatsApp (partage natif sur téléphone, sinon téléchargement + message WhatsApp). */
export async function shareInvoiceWhatsApp(sale, shopName, currency) {
  const blob = await request(`/invoices/${sale.invoice_id}/pdf`, { blob: true });
  const file = new File([blob], `${sale.invoice}.pdf`, { type: "application/pdf" });
  const total = new Intl.NumberFormat("fr-FR").format(sale.total);
  const text = `Bonjour${sale.customer ? " " + sale.customer : ""}, voici votre facture ${sale.invoice} de ${shopName} : ${total} ${currency}. Merci pour votre confiance !`;
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try { await navigator.share({ files: [file], text }); return; } catch (e) { if (e.name === "AbortError") return; }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = `${sale.invoice}.pdf`; a.click();
  let digits = (sale.customer_phone || "").replace(/\D/g, "");
  if (digits.length === 9) digits = "221" + digits;
  window.open(`https://wa.me/${digits}?text=${encodeURIComponent(text)}`, "_blank");
}
