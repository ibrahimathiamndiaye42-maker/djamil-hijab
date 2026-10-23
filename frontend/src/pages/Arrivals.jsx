import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Alert, Field, Modal, Pager, ProductPicker, Table, fmt, today, useList } from "../ui";

export default function Arrivals() {
  const { can } = useAuth();
  const list = useList("/arrivals");
  const [sups, setSups] = useState([]); const [f, setF] = useState(null); const [err, setErr] = useState(""); const [view, setView] = useState(null);
  useEffect(() => { if (can("suppliers.read")) api("/suppliers", { params: { per_page: 100 } }).then((r) => setSups(r.items)); }, []); // eslint-disable-line
  const add = (p) => setF((s) => s.items.some((i) => i.product_id === p.id) ? s : { ...s, items: [...s.items, { product_id: p.id, name: p.name, qty: 1, unit_cost: p.purchase_price }] });
  const upd = (i, k, v) => setF((s) => ({ ...s, items: s.items.map((x, j) => (j === i ? { ...x, [k]: v } : x)) }));
  const total = f ? f.items.reduce((a, i) => a + i.qty * i.unit_cost, 0) : 0;
  const save = async () => {
    setErr("");
    try { await api("/arrivals", { method: "POST", body: { supplier_id: f.supplier_id || null, date: f.date, notes: f.notes, items: f.items.map((i) => ({ product_id: i.product_id, qty: Number(i.qty), unit_cost: Number(i.unit_cost) })) } }); setF(null); list.reload(); }
    catch (x) { setErr(x.message); }
  };
  return (
    <>
      <div className="toolbar"><h2>Arrivages</h2>{can("stock.entry") && <button className="btn" onClick={() => { setErr(""); setF({ date: today(), supplier_id: "", notes: "", items: [] }); }}>+ Nouvel arrivage</button>}</div>
      <Alert>{list.error}</Alert>
      <Table rows={list.items} onRowClick={async (a) => setView(await api(`/arrivals/${a.id}`))} columns={[{ label: "N°", key: "code" }, { label: "Date", key: "date" }, { label: "Fournisseur", key: "supplier" }, { label: "Total", render: (a) => fmt(a.total) }, { label: "Enregistré par", key: "user" }]} />
      <Pager list={list} />
      {view && <Modal title={view.code} onClose={() => setView(null)}><p>{view.date} — {view.supplier || "Sans fournisseur"} — par {view.user}</p>
        <Table rows={view.items} columns={[{ label: "Produit", key: "product" }, { label: "Qté", key: "qty" }, { label: "Prix achat", render: (i) => fmt(i.unit_cost) }]} /><p><b>Total : {fmt(view.total)}</b></p>{view.notes && <p className="muted">{view.notes}</p>}</Modal>}
      {f && (
        <Modal title="Nouvel arrivage" onClose={() => setF(null)} wide>
          <div className="form"><Alert>{err}</Alert>
            <div className="two"><Field label="Date"><input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
              <Field label="Fournisseur"><select value={f.supplier_id} onChange={(e) => setF({ ...f, supplier_id: e.target.value })}><option value="">—</option>{sups.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></Field></div>
            <ProductPicker onPick={add} />
            {f.items.map((i, k) => (
              <div className="line" key={i.product_id}><span>{i.name}</span>
                <input type="number" min="1" value={i.qty} onChange={(e) => upd(k, "qty", e.target.value)} aria-label="Quantité" />
                <input type="number" min="0" value={i.unit_cost} onChange={(e) => upd(k, "unit_cost", e.target.value)} aria-label="Prix d'achat" />
                <button className="btn ghost" onClick={() => setF({ ...f, items: f.items.filter((_, j) => j !== k) })}>✕</button></div>))}
            <Field label="Notes"><input value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
            <p><b>Total : {fmt(total)}</b></p>
            <div className="actions"><button className="btn" disabled={!f.items.length} onClick={save}>Enregistrer l'arrivage</button></div></div>
        </Modal>)}
    </>
  );
}
