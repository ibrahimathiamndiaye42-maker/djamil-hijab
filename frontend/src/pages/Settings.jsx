import { useEffect, useState } from "react";
import { api, uploadImage } from "../api";
import { useAuth } from "../auth";
import { Alert, Field } from "../ui";

export default function Settings() {
  const { settings, reloadSettings } = useAuth();
  const [f, setF] = useState(null); const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [cats, setCats] = useState([]); const [nc, setNc] = useState("");
  useEffect(() => { if (settings) setF({ ...settings, phones: settings.phones.join("\n"), payment_methods: settings.payment_methods.join(", ") }); }, [settings]);
  const loadCats = () => api("/categories").then(setCats);
  useEffect(() => { loadCats(); }, []);
  if (!f) return null;
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault(); setErr(""); setMsg("");
    try {
      await api("/settings", { method: "PATCH", body: { company_name: f.company_name, address: f.address, currency: f.currency, invoice_footer: f.invoice_footer, logo_url: f.logo_url,
        phones: f.phones.split("\n").map((s) => s.trim()).filter(Boolean), payment_methods: f.payment_methods.split(",").map((s) => s.trim()).filter(Boolean) } });
      await reloadSettings(); setMsg("Paramètres enregistrés");
    } catch (x) { setErr(x.message); }
  };
  const logo = async (e) => { if (e.target.files[0]) try { setF({ ...f, logo_url: (await uploadImage(e.target.files[0], "logos")).url }); } catch (x) { setErr(x.message); } };
  const addCat = async () => { if (!nc.trim()) return; try { await api("/categories", { method: "POST", body: { name: nc } }); setNc(""); loadCats(); } catch (x) { setErr(x.message); } };
  const patchCat = async (c, body) => { try { await api(`/categories/${c.id}`, { method: "PATCH", body }); loadCats(); } catch (x) { setErr(x.message); } };
  return (
    <>
      <h2>Paramètres</h2>
      <form className="card form" onSubmit={save}><Alert>{err}</Alert>{msg && <div className="ok-msg">{msg}</div>}
        <Field label="Nom de l'entreprise"><input value={f.company_name} onChange={set("company_name")} /></Field>
        <Field label="Téléphones (un par ligne)"><textarea rows="3" value={f.phones} onChange={set("phones")} /></Field>
        <Field label="Adresse"><input value={f.address} onChange={set("address")} /></Field>
        <Field label="Devise"><input value={f.currency} onChange={set("currency")} /></Field>
        <Field label="Modes de paiement (séparés par des virgules)"><input value={f.payment_methods} onChange={set("payment_methods")} /></Field>
        <Field label="Texte en bas de facture"><input value={f.invoice_footer} onChange={set("invoice_footer")} /></Field>
        <Field label="Logo"><input type="file" accept="image/*" onChange={logo} /></Field>{f.logo_url && <img className="thumb" src={f.logo_url} alt="logo" />}
        <div className="actions"><button className="btn">Enregistrer</button></div></form>
      <div className="card"><h3>Catégories</h3>
        {cats.map((c) => <p className="row" key={c.id}><span className={c.is_active ? "" : "muted"}>{c.name}</span><span>
          <button className="btn ghost" onClick={() => { const n = prompt("Nouveau nom", c.name); if (n) patchCat(c, { name: n }); }}>Renommer</button>
          <button className="btn ghost" onClick={() => patchCat(c, { is_active: !c.is_active })}>{c.is_active ? "Désactiver" : "Activer"}</button></span></p>)}
        <div className="line pay"><input placeholder="Nouvelle catégorie" value={nc} onChange={(e) => setNc(e.target.value)} /><button className="btn" onClick={addCat}>Ajouter</button></div></div>
    </>
  );
}
