import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Alert, Field, Modal, Pager, ProductPicker, StockBadge, Table, dt, fmt, useDebounced, useList } from "../ui";

const TYPES = { ENTREE: "Entrée", VENTE: "Vente", RETOUR_CLIENT: "Retour client", RETOUR_FOURNISSEUR: "Retour fournisseur", ENDOMMAGE: "Endommagé", PERTE: "Perte", CORRECTION: "Correction", INVENTAIRE: "Inventaire" };

function Movements() {
  const [type, setType] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState(""); const [q, setQ] = useState("");
  const dq = useDebounced(q);
  const list = useList("/stock/movements", { type, date_from: from, date_to: to, q: dq });
  return (
    <>
      <div className="filters">
        <input placeholder="N° mouvement (MVT-…)" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value)}><option value="">Tous types</option>{Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /><input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      </div>
      <Alert>{list.error}</Alert>
      <Table rows={list.items} columns={[{ label: "N°", key: "code" }, { label: "Date", render: (m) => dt(m.created_at) }, { label: "Produit", key: "product" },
        { label: "Type", render: (m) => TYPES[m.type] }, { label: "Qté", render: (m) => <b className={m.qty_delta < 0 ? "neg" : "pos"}>{m.qty_delta > 0 ? "+" : ""}{m.qty_delta}</b> },
        { label: "Avant → Après", render: (m) => `${m.qty_before} → ${m.qty_after}` }, { label: "Utilisateur", key: "user" }, { label: "Motif", key: "reason" }]} />
      <Pager list={list} />
    </>
  );
}

export default function Stock() {
  const { can } = useAuth();
  const [tab, setTab] = useState("etat"); const [q, setQ] = useState(""); const [status, setStatus] = useState("");
  const dq = useDebounced(q);
  const list = useList("/products", { q: dq, status });
  const [adj, setAdj] = useState(null); const [err, setErr] = useState("");
  const save = async (e) => {
    e.preventDefault(); setErr("");
    try { await api("/stock/adjust", { method: "POST", body: { product_id: adj.p.id, type: adj.type, qty: Number(adj.qty), reason: adj.reason } }); setAdj(null); list.reload(); }
    catch (x) { setErr(x.message); }
  };
  return (
    <>
      <div className="toolbar"><h2>Stock</h2>
        <div className="tabs"><button className={tab === "etat" ? "on" : ""} onClick={() => setTab("etat")}>État du stock</button><button className={tab === "mvt" ? "on" : ""} onClick={() => setTab("mvt")}>Mouvements</button></div></div>
      {tab === "mvt" ? <Movements /> : (
        <>
          <div className="filters"><input placeholder="Rechercher un produit" value={q} onChange={(e) => setQ(e.target.value)} />
            <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tous statuts</option><option value="NORMAL">Normal</option><option value="FAIBLE">Faible</option><option value="RUPTURE">Rupture</option></select></div>
          {can("stock.adjust") && <div className="card"><b>Corriger le stock</b><ProductPicker onPick={(p) => { setErr(""); setAdj({ p, type: "CORRECTION", qty: "", reason: "" }); }} /></div>}
          <Alert>{list.error}</Alert>
          <Table rows={list.items} columns={[{ label: "Réf.", key: "code" }, { label: "Produit", key: "name" }, { label: "Quantité", render: (p) => <b>{p.stock_qty}</b> }, { label: "Seuil", key: "alert_threshold" },
            { label: "Prix achat", render: (p) => fmt(p.purchase_price) }, { label: "Prix vente", render: (p) => fmt(p.sell_price) }, { label: "Valeur", render: (p) => fmt(p.stock_value) }, { label: "Statut", render: (p) => <StockBadge s={p.status} /> }]} />
          <Pager list={list} />
        </>)}
      {adj && (
        <Modal title={`Mouvement — ${adj.p.name}`} onClose={() => setAdj(null)}>
          <form className="form" onSubmit={save}><Alert>{err}</Alert>
            <p>Stock actuel : <b>{adj.p.stock_qty}</b></p>
            <Field label="Type"><select value={adj.type} onChange={(e) => setAdj({ ...adj, type: e.target.value })}>{["CORRECTION", "PERTE", "ENDOMMAGE", "RETOUR_CLIENT", "RETOUR_FOURNISSEUR"].map((t) => <option key={t} value={t}>{TYPES[t]}</option>)}</select></Field>
            <Field label={adj.type === "CORRECTION" ? "Variation (ex : -2 ou +3)" : "Quantité"}><input type="number" value={adj.qty} onChange={(e) => setAdj({ ...adj, qty: e.target.value })} required /></Field>
            <Field label={adj.type === "RETOUR_CLIENT" ? "Motif (facultatif)" : "Motif (obligatoire)"}><input value={adj.reason} onChange={(e) => setAdj({ ...adj, reason: e.target.value })} required={adj.type !== "RETOUR_CLIENT"} /></Field>
            <div className="actions"><button className="btn">Valider</button></div></form>
        </Modal>)}
    </>
  );
}
