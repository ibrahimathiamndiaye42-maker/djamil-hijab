import { useState } from "react";
import { Alert, Pager, Table, dt, useDebounced, useList } from "../ui";

export default function Journal() {
  const [q, setQ] = useState(""); const [action, setAction] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const list = useList("/audit", { q: useDebounced(q), action: useDebounced(action), date_from: from, date_to: to });
  return (
    <>
      <h2>Journal d'activité</h2>
      <p className="muted">Ce journal est en lecture seule : personne ne peut le modifier ni l'effacer.</p>
      <div className="filters"><input placeholder="Utilisateur ou référence (FAC-…, PRD-…)" value={q} onChange={(e) => setQ(e.target.value)} /><input placeholder="Action exacte (ex : VENTE_CREEE)" value={action} onChange={(e) => setAction(e.target.value)} />
        <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /><input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></div>
      <Alert>{list.error}</Alert>
      <Table rows={list.items} columns={[{ label: "Date", render: (l) => dt(l.created_at) }, { label: "Utilisateur", key: "user" }, { label: "Action", key: "action" }, { label: "Élément", key: "entity_ref" },
        { label: "Détails", render: (l) => (l.details ? <details><summary>voir</summary><pre>{JSON.stringify(l.details, null, 1)}</pre></details> : "") }]} />
      <Pager list={list} />
    </>
  );
}
