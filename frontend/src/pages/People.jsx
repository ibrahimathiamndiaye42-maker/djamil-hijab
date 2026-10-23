import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Alert, Field, Modal, Pager, Table, dt, fmt, useDebounced, useList } from "../ui";

function Party({ path, title, readPerm, writePerm, label }) {
  const { can } = useAuth(); const w = can(writePerm);
  const [q, setQ] = useState(""); const dq = useDebounced(q);
  const list = useList(`/${path}`, { q: dq });
  const [f, setF] = useState(null); const [d, setD] = useState(null); const [err, setErr] = useState("");
  const save = async (e) => {
    e.preventDefault(); setErr("");
    try { await api(f.id ? `/${path}/${f.id}` : `/${path}`, { method: f.id ? "PATCH" : "POST", body: { name: f.name, phone: f.phone, address: f.address, notes: f.notes } }); setF(null); list.reload(); }
    catch (x) { setErr(x.message); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <>
      <div className="toolbar"><h2>{title}</h2>{w && <button className="btn" onClick={() => { setErr(""); setF({ name: "", phone: "", address: "", notes: "" }); }}>+ {label}</button>}</div>
      <div className="filters"><input placeholder="Nom, téléphone ou code" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      <Alert>{list.error}</Alert>
      <Table rows={list.items} onRowClick={async (x) => setD(await api(`/${path}/${x.id}`))} columns={[{ label: "Code", key: "code" }, { label: "Nom", key: "name" }, { label: "Téléphone", key: "phone" }, { label: "Adresse", key: "address" }]} />
      <Pager list={list} />
      {d && <Modal title={`${d.name} (${d.code})`} onClose={() => setD(null)} wide>
        <p>{d.phone} {d.address && `— ${d.address}`}</p>{d.notes && <p className="muted">{d.notes}</p>}
        {"purchases_count" in d && <><p><b>{d.purchases_count}</b> achats — total dépensé : <b>{fmt(d.total_spent)}</b></p>
          <Table rows={d.recent_sales} columns={[{ label: "Facture", render: (s) => s.invoice }, { label: "Date", render: (s) => dt(s.date) }, { label: "Total", render: (s) => fmt(s.total) }, { label: "Statut", key: "status" }]} /></>}
        {d.arrivals && <Table rows={d.arrivals} columns={[{ label: "Arrivage", key: "code" }, { label: "Date", key: "date" }, { label: "Total", render: (a) => fmt(a.total) }]} />}
        {w && <div className="actions"><button className="btn ghost" onClick={() => { setErr(""); setF(d); setD(null); }}>Modifier</button></div>}
      </Modal>}
      {f && <Modal title={f.id ? "Modifier" : label} onClose={() => setF(null)}><form className="form" onSubmit={save}><Alert>{err}</Alert>
        <Field label="Nom *"><input value={f.name} onChange={set("name")} required /></Field><Field label="Téléphone"><input value={f.phone || ""} onChange={set("phone")} /></Field>
        <Field label="Adresse"><input value={f.address || ""} onChange={set("address")} /></Field><Field label="Notes"><textarea rows="2" value={f.notes || ""} onChange={set("notes")} /></Field>
        <div className="actions"><button className="btn">Enregistrer</button></div></form></Modal>}
    </>
  );
}
export const Customers = () => <Party path="customers" title="Clients" readPerm="customers.read" writePerm="customers.write" label="Nouveau client" />;
export const Suppliers = () => <Party path="suppliers" title="Fournisseurs" readPerm="suppliers.read" writePerm="suppliers.write" label="Nouveau fournisseur" />;
