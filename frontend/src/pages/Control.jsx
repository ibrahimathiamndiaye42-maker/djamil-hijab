import { useState } from "react";
import { Icon } from "../icons";
import { Alert, Pager, Table, dt, useList } from "../ui";

export default function Control() {
  const [tab, setTab] = useState("gaps"); const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const gaps = useList("/control/gaps", { date_from: from, date_to: to });
  const corr = useList("/stock/movements", { type: "CORRECTION", date_from: from, date_to: to });
  const l = tab === "gaps" ? gaps : corr;
  return (
    <>
      <div className="toolbar"><h2>Contrôle du stock</h2><div className="tabs"><button className={tab === "gaps" ? "on" : ""} onClick={() => setTab("gaps")}>Écarts d'inventaire</button><button className={tab === "corr" ? "on" : ""} onClick={() => setTab("corr")}>Corrections</button></div></div>
      <div className="filters"><input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /><input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></div>
      <Alert>{l.error}</Alert>
      {tab === "gaps" ? <Table rows={gaps.items} columns={[{ label: "Date", render: (g) => dt(g.date) }, { label: "Produit", render: (g) => <><Icon name="alert" size={16} /> {g.product}</> }, { label: "Théorique", key: "theoretical" }, { label: "Réel", key: "counted" }, { label: "Écart", render: (g) => <b className="neg">{g.diff}</b> }, { label: "Utilisateur", key: "user" }, { label: "Motif", key: "reason" }]} />
        : <Table rows={corr.items} columns={[{ label: "Date", render: (m) => dt(m.created_at) }, { label: "Produit", key: "product" }, { label: "Avant", key: "qty_before" }, { label: "Après", key: "qty_after" }, { label: "Variation", render: (m) => <b className="neg">{m.qty_delta}</b> }, { label: "Utilisateur", key: "user" }, { label: "Motif", key: "reason" }]} />}
      <Pager list={l} />
    </>
  );
}
