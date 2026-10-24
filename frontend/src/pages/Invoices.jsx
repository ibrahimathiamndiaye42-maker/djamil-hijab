import { useEffect, useState } from "react";
import { api, openPdf, shareInvoiceWhatsApp } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../icons";
import { Alert, Field, Modal, Pager, Table, dt, fmt, useDebounced, useList } from "../ui";

export default function Invoices() {
  const { can, settings } = useAuth(); const methods = settings?.payment_methods || [];
  const [q, setQ] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState(""); const [min, setMin] = useState(""); const [max, setMax] = useState(""); const [uid, setUid] = useState("");
  const dq = useDebounced(q);
  const list = useList("/invoices", { q: dq, date_from: from, date_to: to, min_amount: min, max_amount: max, user_id: uid });
  const [users, setUsers] = useState([]); const [v, setV] = useState(null); const [reason, setReason] = useState(""); const [err, setErr] = useState(""); const [pay, setPay] = useState({ method: methods[0], amount: "" });
  useEffect(() => { if (can("users.manage")) api("/users").then(setUsers); }, []); // eslint-disable-line
  const open = async (i) => { setErr(""); setReason(""); setV(await api(`/invoices/${i.invoice_id}`)); };
  const cancel = async () => { try { setV(await api(`/invoices/${v.invoice_id}/cancel`, { method: "POST", body: { reason } })); list.reload(); } catch (x) { setErr(x.message); } };
  const addPay = async () => { try { setV(await api(`/sales/${v.id}/payments`, { method: "POST", body: { method: pay.method, amount: Number(pay.amount) } })); setPay({ ...pay, amount: "" }); list.reload(); } catch (x) { setErr(x.message); } };
  return (
    <>
      <h2>Factures</h2>
      <div className="filters">
        <input placeholder="N° facture (FAC-…) ou client" value={q} onChange={(e) => setQ(e.target.value)} />
        <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /><input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        <input type="number" placeholder="Montant min" value={min} onChange={(e) => setMin(e.target.value)} /><input type="number" placeholder="Montant max" value={max} onChange={(e) => setMax(e.target.value)} />
        {users.length > 0 && <select value={uid} onChange={(e) => setUid(e.target.value)}><option value="">Tous les employés</option>{users.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}</select>}
      </div>
      <Alert>{list.error}</Alert>
      <Table rows={list.items} onRowClick={open} columns={[{ label: "Facture", key: "invoice" }, { label: "Date", render: (i) => dt(i.created_at) }, { label: "Client", render: (i) => i.customer || "—" },
        { label: "Total", render: (i) => fmt(i.total) }, { label: "Reste", render: (i) => (i.rest ? <b className="neg">{fmt(i.rest)}</b> : "—") }, { label: "Employé", key: "user" },
        { label: "Statut", render: (i) => <span className={"badge " + (i.status === "ANNULEE" ? "bad" : "ok")}>{i.status === "ANNULEE" ? "Annulée" : "Validée"}</span> }]} />
      <Pager list={list} />
      {v && (
        <Modal title={v.invoice} onClose={() => setV(null)} wide>
          <p>{dt(v.created_at)} — {v.customer || "Client de passage"} — vendeur : {v.user}</p>
          <Table rows={v.items} columns={[{ label: "Produit", key: "name" }, { label: "Qté", key: "qty" }, { label: "PU", render: (i) => fmt(i.unit_price) }, { label: "Total", render: (i) => fmt(i.line_total) }]} />
          <p className="row big"><span>Total</span><b>{fmt(v.total)}</b></p><p className="row"><span>Payé</span><b>{fmt(v.paid)}</b></p>
          <p className="muted">{v.payments.map((p) => `${p.method} ${fmt(p.amount)}`).join(" · ")}</p>
          <Alert>{err}</Alert>
          <div className="actions"><button className="btn" onClick={() => shareInvoiceWhatsApp(v, settings?.company_name || "", settings?.currency || "FCFA").catch((e) => setErr(e.message))}><Icon name="whatsapp" size={18} /> Envoyer par WhatsApp</button><button className="btn ghost" onClick={() => openPdf(v.invoice_id)}>Voir le PDF</button></div>
          {v.status === "VALIDEE" && v.rest > 0 && can("sales.create") && <div className="line pay"><select value={pay.method} onChange={(e) => setPay({ ...pay, method: e.target.value })}>{methods.map((m) => <option key={m}>{m}</option>)}</select>
            <input type="number" placeholder={`Reste ${fmt(v.rest)}`} value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} /><button className="btn" onClick={addPay}>Encaisser</button></div>}
          {v.status === "VALIDEE" && can("sales.cancel") && <Field label="Annuler cette facture (avoir + retour en stock)"><div className="line pay"><input placeholder="Motif obligatoire" value={reason} onChange={(e) => setReason(e.target.value)} /><button className="btn danger" disabled={!reason} onClick={cancel}>Annuler</button></div></Field>}
        </Modal>)}
    </>
  );
}
