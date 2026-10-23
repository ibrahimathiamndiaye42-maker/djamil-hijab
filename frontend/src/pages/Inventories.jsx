import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Alert, Modal, Pager, ProductPicker, Table, dt, useList } from "../ui";

export default function Inventories() {
  const { can } = useAuth();
  const list = useList("/inventories");
  const [f, setF] = useState(null); const [err, setErr] = useState(""); const [view, setView] = useState(null);
  const add = (p) => setF((s) => (s.items.some((i) => i.p.id === p.id) ? s : { ...s, items: [...s.items, { p, counted: "", reason: "" }] }));
  const upd = (id, k, v) => setF((s) => ({ ...s, items: s.items.map((i) => (i.p.id === id ? { ...i, [k]: v } : i)) }));
  const save = async () => {
    setErr("");
    try { await api("/inventories", { method: "POST", body: { notes: f.notes, items: f.items.map((i) => ({ product_id: i.p.id, counted: Number(i.counted), reason: i.reason })) } }); setF(null); list.reload(); }
    catch (x) { setErr(x.message); }
  };
  const ready = f && f.items.length && f.items.every((i) => i.counted !== "" && (Number(i.counted) === i.p.stock_qty || i.reason.trim()));
  return (
    <>
      <div className="toolbar"><h2>Inventaires</h2>{can("inventories.run") && <button className="btn" onClick={() => { setErr(""); setF({ notes: "", items: [] }); }}>Nouvel inventaire</button>}</div>
      <Alert>{list.error}</Alert>
      <Table rows={list.items} onRowClick={async (i) => setView(await api(`/inventories/${i.id}`))} columns={[{ label: "N°", key: "code" }, { label: "Date", render: (i) => dt(i.created_at) }, { label: "Par", key: "user" }, { label: "Lignes", key: "lines" }, { label: "Écarts", render: (i) => (i.gaps ? <b className="neg">{i.gaps}</b> : 0) }]} />
      <Pager list={list} />
      {view && <Modal title={view.code} onClose={() => setView(null)} wide><Table rows={view.items} columns={[{ label: "Produit", key: "product" }, { label: "Théorique", key: "theoretical" }, { label: "Compté", key: "counted" }, { label: "Écart", render: (g) => <b className={g.diff ? "neg" : ""}>{g.diff}</b> }, { label: "Motif", key: "reason" }]} /></Modal>}
      {f && (
        <Modal title="Nouvel inventaire" onClose={() => setF(null)} wide>
          <div className="form"><Alert>{err}</Alert><ProductPicker onPick={add} placeholder="Ajouter un produit à compter" />
            {f.items.map((i) => {
              const diff = i.counted === "" ? null : Number(i.counted) - i.p.stock_qty;
              return (
                <div className="card" key={i.p.id}><p className="row"><b>{i.p.name}</b><button className="btn ghost" onClick={() => setF({ ...f, items: f.items.filter((x) => x.p.id !== i.p.id) })}>✕</button></p>
                  <p>Stock théorique : <b>{i.p.stock_qty}</b></p>
                  <input type="number" min="0" placeholder="Quantité comptée" value={i.counted} onChange={(e) => upd(i.p.id, "counted", e.target.value)} />
                  {diff ? <><p className="neg">⚠️ Écart : {diff > 0 ? "+" : ""}{diff}</p><input placeholder="Motif obligatoire" value={i.reason} onChange={(e) => upd(i.p.id, "reason", e.target.value)} /></> : null}</div>);
            })}
            <div className="actions"><button className="btn" disabled={!ready} onClick={save}>Valider l'inventaire</button></div></div>
        </Modal>)}
    </>
  );
}
