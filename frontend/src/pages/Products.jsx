import { useEffect, useState } from "react";
import { api, uploadImage } from "../api";
import { useAuth } from "../auth";
import { Alert, Field, Modal, Pager, StockBadge, Table, fmt, useDebounced, useList } from "../ui";

const empty = { name: "", reference: "", category_id: "", subcategory: "", description: "", color: "", size: "", purchase_price: 0, sell_price: 0, initial_qty: 0, alert_threshold: 5, supplier_id: "", photo_url: "" };

export default function Products() {
  const { can } = useAuth(); const w = can("products.write");
  const [q, setQ] = useState(""); const [cat, setCat] = useState(""); const [status, setStatus] = useState(""); const [inactive, setInactive] = useState(false);
  const dq = useDebounced(q);
  const list = useList("/products", { q: dq, category_id: cat, status, active: inactive ? "0" : "1" });
  const [cats, setCats] = useState([]); const [sups, setSups] = useState([]);
  const [edit, setEdit] = useState(null); const [err, setErr] = useState("");
  const [addQty, setAddQty] = useState(""); const [rmQty, setRmQty] = useState(""); const [rmReason, setRmReason] = useState("");
  const [catOpen, setCatOpen] = useState(false); const [newCat, setNewCat] = useState("");
  const reloadCats = () => api("/categories").then(setCats);
  const addCat = async () => { if (!newCat.trim()) return; try { await api("/categories", { method: "POST", body: { name: newCat } }); setNewCat(""); reloadCats(); } catch (x) { setErr(x.message); } };
  const toggleCat = async (c) => { try { await api(`/categories/${c.id}`, { method: "PATCH", body: { is_active: !c.is_active } }); reloadCats(); } catch (x) { setErr(x.message); } };
  const addStock = async () => {
    setErr("");
    try { await api("/arrivals", { method: "POST", body: { items: [{ product_id: edit.id, qty: Number(addQty), unit_cost: Number(edit.purchase_price || 0) }] } }); setAddQty(""); setEdit(null); list.reload(); }
    catch (x) { setErr(x.message); }
  };
  const removeStock = async () => {
    setErr("");
    try { await api("/stock/adjust", { method: "POST", body: { product_id: edit.id, type: "CORRECTION", qty: -Math.abs(Number(rmQty)), reason: rmReason } }); setRmQty(""); setRmReason(""); setEdit(null); list.reload(); }
    catch (x) { setErr(x.message); }
  };
  useEffect(() => { api("/categories").then(setCats); if (can("suppliers.read")) api("/suppliers", { params: { per_page: 100 } }).then((r) => setSups(r.items)); }, []); // eslint-disable-line

  const save = async (e) => {
    e.preventDefault(); setErr("");
    const body = { ...edit }; delete body.id;
    ["category_id", "supplier_id"].forEach((k) => { body[k] = body[k] || null; });
    ["purchase_price", "sell_price", "initial_qty", "alert_threshold"].forEach((k) => { body[k] = Number(body[k] || 0); });
    try {
      if (edit.id) { delete body.initial_qty; await api(`/products/${edit.id}`, { method: "PATCH", body }); }
      else await api("/products", { method: "POST", body });
      setEdit(null); list.reload();
    } catch (x) { setErr(x.message); }
  };
  const toggle = async (p) => { await api(`/products/${p.id}`, p.is_active ? { method: "DELETE" } : { method: "PATCH", body: { is_active: true } }); setEdit(null); list.reload(); };
  const set = (k) => (e) => setEdit({ ...edit, [k]: e.target.value });
  const photo = async (e) => { if (e.target.files[0]) try { setEdit({ ...edit, photo_url: (await uploadImage(e.target.files[0])).url }); } catch (x) { setErr(x.message); } };

  return (
    <>
      <div className="toolbar">
        <h2>Produits</h2>
        <span>{can("categories.write") && <button className="btn ghost" onClick={() => { setErr(""); setCatOpen(true); }}>Catégories</button>} {w && <button className="btn" onClick={() => { setErr(""); setEdit({ ...empty }); }}>+ Ajouter un produit</button>}</span>
      </div>
      <div className="filters">
        <input placeholder="Rechercher (nom, référence, PRD-…)" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={cat} onChange={(e) => setCat(e.target.value)}><option value="">Toutes catégories</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tous statuts</option><option value="NORMAL">Normal</option><option value="FAIBLE">Faible</option><option value="RUPTURE">Rupture</option></select>
        <label className="chk"><input type="checkbox" checked={inactive} onChange={(e) => setInactive(e.target.checked)} /> Inactifs</label>
      </div>
      <Alert>{list.error}</Alert>
      <Table rows={list.items} onRowClick={w ? (p) => { setErr(""); setEdit({ ...empty, ...p, initial_qty: 0 }); } : undefined} columns={[
        { label: "Réf.", render: (p) => p.code }, { label: "Produit", render: (p) => <>{p.name}<br /><small>{[p.color, p.size].filter(Boolean).join(" · ")}</small></> },
        { label: "Catégorie", key: "category" }, { label: "Stock", render: (p) => p.stock_qty }, { label: "Prix vente", render: (p) => fmt(p.sell_price) },
        { label: "Statut", render: (p) => <StockBadge s={p.status} /> }]} />
      <Pager list={list} />
      {catOpen && (
        <Modal title="Catégories" onClose={() => setCatOpen(false)}>
          <Alert>{err}</Alert>
          {cats.map((c) => <p className="row" key={c.id}><span className={c.is_active ? "" : "muted"}>{c.name}</span><button className="btn ghost" onClick={() => toggleCat(c)}>{c.is_active ? "Désactiver" : "Activer"}</button></p>)}
          <div className="line pay"><input placeholder="Nouvelle catégorie" value={newCat} onChange={(e) => setNewCat(e.target.value)} /><span /><button className="btn" onClick={addCat}>Ajouter</button></div>
        </Modal>)}
      {edit && (
        <Modal title={edit.id ? `Modifier ${edit.code}` : "Nouveau produit"} onClose={() => setEdit(null)}>
          <form onSubmit={save} className="form">
            <Alert>{err}</Alert>
            <Field label="Nom du produit *"><input value={edit.name} onChange={set("name")} required /></Field>
            <div className="two"><Field label="Référence"><input value={edit.reference || ""} onChange={set("reference")} /></Field>
              <Field label="Catégorie"><select value={edit.category_id || ""} onChange={set("category_id")}><option value="">—</option>{cats.filter((c) => c.is_active).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field></div>
            <div className="two"><Field label="Sous-catégorie"><input value={edit.subcategory || ""} onChange={set("subcategory")} /></Field>
              <Field label="Fournisseur"><select value={edit.supplier_id || ""} onChange={set("supplier_id")}><option value="">—</option>{sups.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></Field></div>
            <div className="two"><Field label="Couleur"><input value={edit.color || ""} onChange={set("color")} /></Field><Field label="Taille"><input value={edit.size || ""} onChange={set("size")} /></Field></div>
            <div className="two"><Field label="Prix d'achat"><input type="number" min="0" value={edit.purchase_price} onChange={set("purchase_price")} /></Field>
              <Field label="Prix de vente"><input type="number" min="0" value={edit.sell_price} onChange={set("sell_price")} /></Field></div>
            <div className="two">{!edit.id && <Field label="Quantité initiale"><input type="number" min="0" value={edit.initial_qty} onChange={set("initial_qty")} /></Field>}
              <Field label="Seuil d'alerte"><input type="number" min="0" value={edit.alert_threshold} onChange={set("alert_threshold")} /></Field></div>
            <Field label="Description"><textarea rows="2" value={edit.description || ""} onChange={set("description")} /></Field>
            <Field label="Photo"><input type="file" accept="image/*" onChange={photo} /></Field>
            {edit.photo_url && <img className="thumb" src={edit.photo_url} alt="" />}
            {edit.id && <div className="card"><p>Stock actuel : <b>{edit.stock_qty}</b></p>
              {can("stock.entry") && <div className="line pay"><input type="number" min="1" placeholder="Quantité reçue" value={addQty} onChange={(e) => setAddQty(e.target.value)} /><span /><button type="button" className="btn" disabled={!addQty} onClick={addStock}>+ Ajouter au stock</button></div>}
              {can("stock.adjust") && <div className="line pay"><input type="number" min="1" placeholder="Quantité perdue" value={rmQty} onChange={(e) => setRmQty(e.target.value)} /><input placeholder="Motif (obligatoire)" value={rmReason} onChange={(e) => setRmReason(e.target.value)} /><button type="button" className="btn ghost danger" disabled={!rmQty || !rmReason} onClick={removeStock}>Retirer</button></div>}
            </div>}
            <div className="actions">
              {edit.id && <button type="button" className="btn ghost danger" onClick={() => toggle(edit)}>{edit.is_active ? "Désactiver" : "Réactiver"}</button>}
              <button className="btn">Enregistrer</button>
            </div>
          </form>
        </Modal>)}
    </>
  );
}
