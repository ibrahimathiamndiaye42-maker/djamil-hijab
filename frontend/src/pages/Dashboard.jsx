import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Alert, dt, fmt } from "../ui";

const Card = ({ label, value, tone }) => <div className={"stat " + (tone || "")}><small>{label}</small><b>{value}</b></div>;

export default function Dashboard() {
  const { settings } = useAuth(); const cur = settings?.currency || "FCFA";
  const [d, setD] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { api("/dashboard").then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <Alert>{err}</Alert>;
  if (!d) return <p className="muted">Chargement…</p>;
  const max = Math.max(1, ...d.series.map((s) => s.revenue));
  return (
    <>
      <h2>Aujourd'hui</h2>
      <div className="stats">
        <Card label="Chiffre d'affaires" value={`${fmt(d.today.revenue)} ${cur}`} />
        <Card label="Ventes" value={d.today.sales} />
        <Card label="Produits vendus" value={d.today.units} />
        <Card label="Nouveaux clients" value={d.today.new_customers} />
        <Card label="Stock faible" value={d.low_stock} tone={d.low_stock ? "warn" : ""} />
        <Card label="Ruptures" value={d.out_of_stock} tone={d.out_of_stock ? "bad" : ""} />
        <Card label="Mouvements du jour" value={d.today.movements} />
        <Card label="Corrections (30 j)" value={d.corrections_30d} tone={d.corrections_30d ? "warn" : ""} />
      </div>
      <div className="stats">
        <Card label="Cette semaine" value={`${fmt(d.week_revenue)} ${cur}`} />
        <Card label="Ce mois" value={`${fmt(d.month_revenue)} ${cur}`} />
      </div>
      <h3>Chiffre d'affaires — 30 derniers jours</h3>
      <div className="bars">{d.series.map((s) => <div key={s.day} title={`${s.day} : ${fmt(s.revenue)} ${cur}`} style={{ height: `${(s.revenue / max) * 100}%` }} />)}</div>
      <div className="grid2">
        <div className="card"><h3>Produits les plus vendus</h3>{d.top_products.map((p) => <p key={p.name} className="row"><span>{p.name}</span><b>{p.qty}</b></p>)}</div>
        <div className="card"><h3>Catégories les plus vendues</h3>{d.top_categories.map((p) => <p key={p.name} className="row"><span>{p.name}</span><b>{p.qty}</b></p>)}</div>
        <div className="card"><h3>⚠️ Écarts récents</h3>
          {d.recent_gaps.length ? d.recent_gaps.map((g, i) => <p key={i}><b>{g.product}</b><br /><small>Théorique {g.theoretical} · Réel {g.counted} · Écart {g.diff} — {g.user}, {dt(g.date)}</small></p>) : <p className="muted">Aucun écart</p>}</div>
        <div className="card"><h3>Activité récente</h3>{d.recent_activity.map((a, i) => <p key={i}><b>{a.user}</b> — {a.action} {a.ref}<br /><small>{dt(a.date)}</small></p>)}</div>
      </div>
    </>
  );
}
