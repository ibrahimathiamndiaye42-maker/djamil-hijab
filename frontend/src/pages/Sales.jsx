import { useEffect, useState } from "react";
import { api, openPdf } from "../api";
import { useAuth } from "../auth";
import { Alert, Field, Modal, ProductPicker, fmt, useDebounced } from "../ui";

function CustomerPicker({ value, onChange }) {
  const { can } = useAuth();
  const [q, setQ] = useState(""); const [res, setRes] = useState([]); const [nw, setNw] = useState(null); const [err, setErr] = useState("");
  const dq = useDebounced(q);
  useEffect(() => {
    if (!dq.trim() || !can("customers.read")) { setRes([]); return; }
    let live = true; api("/customers", { params: { q: dq, per_page: 6 } }).then((r) => live && setRes(r.items)).catch(() => {});
    return () => { live = false; };
  }, [dq]); // eslint-disable-line
  if (value) return <p className="row"><span>👤 <b>{value.name}</b> {value.phone}</span><button className="btn ghost" onClick={() => onChange(null)}>Changer</button></p>;
  const create = async (e) => {
    e.preventDefault(); setErr("");
    try { onChange(await api("/customers", { method: "POST", body: nw })); setNw(null); } catch (x) { setErr(x.message); }
  };
  return (
    <div className="picker">
      <input placeholder="Client (facultatif) : nom ou téléphone" value={q} onChange={(e) => setQ(e.target.value)} />
      {res.length > 0 && <ul>{res.map((c) => <li key={c.id} onClick={() => { onChange(c); setQ(""); }}><b>{c.name}</b> <small>{c.phone}</small></li>)}</ul>}
      {can("customers.write") && <button type="button" className="btn ghost" onClick={() => setNw({ name: q, phone: "" })}>+ Nouveau client</button>}
      {nw && <Modal title="Nouveau client" onClose={() => setNw(null)}><form className="form" onSubmit={create}><Alert>{err}</Alert>
        <Field label="Nom *"><input value={nw.name} onChange={(e) => setNw({ ...nw, name: e.target.value })} required /></Field>
        <Field label="Téléphone"><input value={nw.phone} onChange={(e) => setNw({ ...nw, phone: e.target.value })} /></Field><div className="actions"><button className="btn">Créer</button></div></form></Modal>}
    </div>
  );
}

export default function Sales() {
  const { settings } = useAuth(); const cur = settings?.currency || "FCFA"; const methods = settings?.payment_methods || ["Espèces"];
  const [cart, setCart] = useState([]); const [customer, setCustomer] = useState(null); const [discount, setDiscount] = useState(0);
  const [pays, setPays] = useState([{ method: methods[0], amount: "" }]); const [err, setErr] = useState(""); const [done, setDone] = useState(null); const [busy, setBusy] = useState(false);
  const subtotal = cart.reduce((a, l) => a + l.p.sell_price * l.qty, 0);
  const total = Math.max(0, subtotal - Number(discount || 0));
  const paid = pays.reduce((a, p) => a + Number(p.amount || 0), 0);
  const add = (p) => setCart((c) => { const i = c.findIndex((l) => l.p.id === p.id); return i >= 0 ? c.map((l, j) => (j === i ? { ...l, qty: l.qty + 1 } : l)) : [...c, { p, qty: 1 }]; });
  const setQty = (id, qty) => setCart((c) => c.map((l) => (l.p.id === id ? { ...l, qty: Math.max(1, Number(qty) || 1) } : l)));

  const validate = async () => {
    setErr(""); setBusy(true);
    try {
      const sale = await api("/sales", { method: "POST", body: { customer_id: customer?.id || null, discount: Number(discount || 0),
        items: cart.map((l) => ({ product_id: l.p.id, qty: l.qty })), payments: pays.filter((p) => Number(p.amount) > 0).map((p) => ({ method: p.method, amount: Number(p.amount) })) } });
      setDone(sale);
    } catch (x) { setErr(x.message); }
    setBusy(false);
  };
  const reset = () => { setCart([]); setCustomer(null); setDiscount(0); setPays([{ method: methods[0], amount: "" }]); setDone(null); setErr(""); };

  return (
    <>
      <h2>Nouvelle vente</h2>
      <ProductPicker onPick={add} />
      {cart.map((l) => (
        <div className="line" key={l.p.id}><span>{l.p.name}<br /><small>{fmt(l.p.sell_price)} {cur} · stock {l.p.stock_qty}</small></span>
          <input type="number" min="1" value={l.qty} onChange={(e) => setQty(l.p.id, e.target.value)} />
          <b>{fmt(l.p.sell_price * l.qty)}</b><button className="btn ghost" onClick={() => setCart(cart.filter((x) => x.p.id !== l.p.id))}>✕</button></div>))}
      {!cart.length && <p className="muted center">Recherchez un produit pour l'ajouter au panier.</p>}
      <div className="card">
        <CustomerPicker value={customer} onChange={setCustomer} />
        <Field label={`Remise (${cur})`}><input type="number" min="0" value={discount} onChange={(e) => setDiscount(e.target.value)} /></Field>
        <h4>Paiement</h4>
        {pays.map((p, i) => (
          <div className="line pay" key={i}><select value={p.method} onChange={(e) => setPays(pays.map((x, j) => (j === i ? { ...x, method: e.target.value } : x)))}>{methods.map((m) => <option key={m}>{m}</option>)}</select>
            <input type="number" min="0" placeholder="Montant" value={p.amount} onChange={(e) => setPays(pays.map((x, j) => (j === i ? { ...x, amount: e.target.value } : x)))} />
            <button className="btn ghost" onClick={() => setPays(pays.map((x, j) => (j === i ? { ...x, amount: total - (paid - Number(x.amount || 0)) } : x)))}>Tout</button></div>))}
        <button className="btn ghost" onClick={() => setPays([...pays, { method: methods[0], amount: "" }])}>+ Autre mode de paiement</button>
        <p className="row"><span>Sous-total</span><b>{fmt(subtotal)} {cur}</b></p>
        <p className="row"><span>Remise</span><b>-{fmt(discount)} {cur}</b></p>
        <p className="row big"><span>Total</span><b>{fmt(total)} {cur}</b></p>
        <p className="row"><span>Payé</span><b>{fmt(paid)} {cur}</b></p>
        <p className="row"><span>Reste</span><b className={total - paid > 0 ? "neg" : ""}>{fmt(Math.max(0, total - paid))} {cur}</b></p>
        <Alert>{err}</Alert>
        <button className="btn full" disabled={!cart.length || busy} onClick={validate}>{busy ? "Validation…" : "Valider la vente"}</button>
      </div>
      {done && (
        <Modal title="Vente enregistrée ✅" onClose={reset}>
          <p><b>{done.invoice}</b> — {fmt(done.total)} {cur}</p><p className="muted">Stock mis à jour. Opération enregistrée dans l'historique.</p>
          <div className="actions"><button className="btn" onClick={() => openPdf(done.invoice_id)}>Facture PDF</button><button className="btn ghost" onClick={reset}>Nouvelle vente</button></div>
        </Modal>)}
    </>
  );
}
