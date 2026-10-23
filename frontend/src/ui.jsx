import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export const fmt = (n) => new Intl.NumberFormat("fr-FR").format(n ?? 0);
export const dt = (s) => (s ? new Date(s).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "");
export const today = () => new Date().toISOString().slice(0, 10);

export function useDebounced(value, ms = 350) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

/** Liste paginée côté serveur : ne charge jamais plus d'une page. */
export function useList(path, params = {}) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, per_page: 50 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const key = JSON.stringify(params);
  useEffect(() => { setPage(1); }, [key]);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setData(await api(path, { params: { ...params, page } })); } catch (e) { setError(e.message); }
    setLoading(false);
  }, [path, key, page]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  return { ...data, page, setPage, loading, error, reload: load };
}

export function Pager({ list }) {
  const { page, per_page, total, setPage } = list;
  const from = total ? (page - 1) * per_page + 1 : 0, to = Math.min(page * per_page, total);
  return (
    <div className="pager">
      <span>{from}–{to} sur {fmt(total)}</span>
      <button className="btn ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹ Préc.</button>
      <button className="btn ghost" disabled={to >= total} onClick={() => setPage(page + 1)}>Suiv. ›</button>
    </div>
  );
}

export function Table({ columns, rows, onRowClick, empty = "Aucun résultat" }) {
  if (!rows.length) return <p className="muted center">{empty}</p>;
  return (
    <table className="tbl">
      <thead><tr>{columns.map((c) => <th key={c.label}>{c.label}</th>)}</tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.id ?? i} onClick={onRowClick ? () => onRowClick(r) : undefined} className={onRowClick ? "click" : ""}>
            {columns.map((c) => <td key={c.label} data-label={c.label}>{c.render ? c.render(r) : r[c.key]}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Modal({ title, onClose, children, wide }) {
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={"modal" + (wide ? " wide" : "")}>
        <div className="modal-h"><h3>{title}</h3><button className="btn ghost" onClick={onClose}>✕</button></div>
        {children}
      </div>
    </div>
  );
}

export const Field = ({ label, children }) => <label className="field"><span>{label}</span>{children}</label>;
export const Alert = ({ children }) => (children ? <div className="alert">{children}</div> : null);

const STATUS = { NORMAL: ["🟢", "Normal", "ok"], FAIBLE: ["🟠", "Faible", "warn"], RUPTURE: ["🔴", "Rupture", "bad"] };
export const StockBadge = ({ s }) => <span className={"badge " + STATUS[s][2]}>{STATUS[s][0]} {STATUS[s][1]}</span>;

/** Recherche de produit avec liste déroulante (utilisée dans ventes, arrivages, inventaires). */
export function ProductPicker({ onPick, placeholder = "Rechercher un produit (nom, référence, PRD-…)" }) {
  const [q, setQ] = useState(""); const [res, setRes] = useState([]);
  const dq = useDebounced(q);
  useEffect(() => {
    if (!dq.trim()) { setRes([]); return; }
    let live = true;
    api("/products", { params: { q: dq, per_page: 8 } }).then((r) => live && setRes(r.items)).catch(() => {});
    return () => { live = false; };
  }, [dq]);
  return (
    <div className="picker">
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={placeholder} />
      {res.length > 0 && (
        <ul>{res.map((p) => (
          <li key={p.id} onClick={() => { onPick(p); setQ(""); setRes([]); }}>
            <b>{p.name}</b> <small>{p.code} · stock {p.stock_qty} · {fmt(p.sell_price)}</small>
          </li>))}
        </ul>)}
    </div>
  );
}
