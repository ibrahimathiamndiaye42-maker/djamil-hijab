import { useEffect, useState } from "react";
import { api } from "../api";
import { Alert, Table, fmt } from "../ui";

const csv = (name, rows) => {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const body = [keys.join(";"), ...rows.map((r) => keys.map((k) => String(r[k]).replace(/;/g, ",")).join(";"))].join("\n");
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["\ufeff" + body], { type: "text/csv" })); a.download = name + ".csv"; a.click();
};

export default function Reports() {
  const [from, setFrom] = useState(""); const [to, setTo] = useState(""); const [d, setD] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { api("/reports/sales", { params: { date_from: from, date_to: to } }).then(setD).catch((e) => setErr(e.message)); }, [from, to]);
  const Block = ({ title, rows, cols, file }) => <div className="card"><div className="row"><h3>{title}</h3><button className="btn ghost" onClick={() => csv(file, rows)}>CSV</button></div><Table rows={rows} columns={cols} /></div>;
  return (
    <>
      <h2>Rapports de ventes</h2>
      <div className="filters"><input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /><input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></div>
      <p className="muted">Sans dates : 30 derniers jours.</p><Alert>{err}</Alert>
      {d && <>
        <Block title="Par jour" file="ventes_par_jour" rows={d.by_day} cols={[{ label: "Jour", key: "day" }, { label: "Ventes", key: "sales" }, { label: "CA", render: (r) => fmt(r.revenue) }]} />
        <Block title="Par employé" file="ventes_par_employe" rows={d.by_user} cols={[{ label: "Employé", key: "user" }, { label: "Ventes", key: "sales" }, { label: "CA", render: (r) => fmt(r.revenue) }]} />
        <Block title="Par mode de paiement" file="ventes_par_paiement" rows={d.by_method} cols={[{ label: "Mode", key: "method" }, { label: "Montant", render: (r) => fmt(r.amount) }]} /></>}
    </>
  );
}
