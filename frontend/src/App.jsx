import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { useAuth } from "./auth";
import { Alert, Field, Modal } from "./ui";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Products from "./pages/Products.jsx";
import Stock from "./pages/Stock.jsx";
import Arrivals from "./pages/Arrivals.jsx";
import Sales from "./pages/Sales.jsx";
import Invoices from "./pages/Invoices.jsx";
import { Customers, Suppliers } from "./pages/People.jsx";
import Employees from "./pages/Employees.jsx";
import Inventories from "./pages/Inventories.jsx";
import Control from "./pages/Control.jsx";
import Journal from "./pages/Journal.jsx";
import Reports from "./pages/Reports.jsx";
import Settings from "./pages/Settings.jsx";

const NAV = [
  ["/", "🏠", "Dashboard", ["reports.read"], Dashboard], ["/produits", "📦", "Produits", ["products.read"], Products],
  ["/stock", "📊", "Stock", ["stock.read"], Stock], ["/arrivages", "🚚", "Arrivages", ["stock.entry"], Arrivals],
  ["/ventes", "🛒", "Ventes", ["sales.create"], Sales], ["/factures", "🧾", "Factures", ["sales.read", "sales.read_all"], Invoices],
  ["/clients", "👥", "Clients", ["customers.read"], Customers], ["/fournisseurs", "🏭", "Fournisseurs", ["suppliers.read"], Suppliers],
  ["/employes", "👩🏾‍💼", "Employés", ["users.manage"], Employees], ["/inventaires", "📋", "Inventaires", ["inventories.run", "control.read"], Inventories],
  ["/controle", "🔎", "Contrôle", ["control.read"], Control], ["/historique", "📜", "Historique", ["audit.read"], Journal],
  ["/rapports", "📈", "Rapports", ["reports.read"], Reports], ["/parametres", "⚙️", "Paramètres", ["settings.write"], Settings],
];

function Password({ onClose }) {
  const [o, setO] = useState(""); const [n, setN] = useState(""); const [err, setErr] = useState(""); const [ok, setOk] = useState(false);
  const go = async (e) => { e.preventDefault(); setErr(""); try { await api("/auth/change-password", { method: "POST", body: { old_password: o, new_password: n } }); setOk(true); } catch (x) { setErr(x.message); } };
  return <Modal title="Mon mot de passe" onClose={onClose}><form className="form" onSubmit={go}><Alert>{err}</Alert>{ok && <div className="ok-msg">Mot de passe modifié</div>}
    <Field label="Ancien"><input type="password" value={o} onChange={(e) => setO(e.target.value)} required /></Field><Field label="Nouveau (8 caractères min.)"><input type="password" minLength={8} value={n} onChange={(e) => setN(e.target.value)} required /></Field>
    <div className="actions"><button className="btn">Modifier</button></div></form></Modal>;
}

export default function App() {
  const { user, ready, can, logout, settings } = useAuth();
  const [open, setOpen] = useState(false); const [pw, setPw] = useState(false);
  if (!ready) return <p className="muted center">Chargement…</p>;
  if (!user) return <Login />;
  const items = NAV.filter((n) => can(...n[3]));
  const home = can("reports.read") ? "/" : "/ventes";
  return (
    <div className="app">
      <header><button className="burger" onClick={() => setOpen(!open)}>☰</button><b>{settings?.company_name || "DJAMIL HIJAB"}</b><span className="who" onClick={() => setPw(true)}>{user.full_name}</span><button className="btn ghost" onClick={logout}>Quitter</button></header>
      <nav className={open ? "open" : ""} onClick={() => setOpen(false)}>{items.map((n) => <NavLink key={n[0]} to={n[0]} end={n[0] === "/"}><span>{n[1]}</span> {n[2]}</NavLink>)}</nav>
      <main>
        <Routes>
          {items.map(([path, , , , Comp]) => <Route key={path} path={path} element={<Comp />} />)}
          <Route path="*" element={<Navigate to={home} replace />} />
        </Routes>
      </main>
      {pw && <Password onClose={() => setPw(false)} />}
    </div>
  );
}
