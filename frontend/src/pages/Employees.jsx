import { useEffect, useState } from "react";
import { api } from "../api";
import { Alert, Field, Modal } from "../ui";

export default function Employees() {
  const [users, setUsers] = useState([]); const [perms, setPerms] = useState([]); const [f, setF] = useState(null); const [err, setErr] = useState("");
  const load = () => api("/users").then(setUsers).catch((e) => setErr(e.message));
  useEffect(() => { load(); api("/permissions").then(setPerms); }, []);
  const save = async (e) => {
    e.preventDefault(); setErr("");
    try {
      const body = { full_name: f.full_name, role: f.role, permissions: f.extra_permissions, is_active: f.is_active };
      if (f.password) body.password = f.password;
      if (f.id) await api(`/users/${f.id}`, { method: "PATCH", body });
      else await api("/users", { method: "POST", body: { ...body, username: f.username, password: f.password } });
      setF(null); load();
    } catch (x) { setErr(x.message); }
  };
  const toggle = (code) => setF({ ...f, extra_permissions: f.extra_permissions.includes(code) ? f.extra_permissions.filter((c) => c !== code) : [...f.extra_permissions, code] });
  return (
    <>
      <div className="toolbar"><h2>Employés</h2><button className="btn" onClick={() => { setErr(""); setF({ username: "", full_name: "", password: "", role: "EMPLOYE", extra_permissions: [], is_active: true }); }}>+ Nouvel employé</button></div>
      <Alert>{err && !f ? err : ""}</Alert>
      {users.map((u) => <div className="card click" key={u.id} onClick={() => { setErr(""); setF({ ...u, password: "" }); }}><p className="row"><b>{u.full_name}</b><span className={"badge " + (u.is_active ? "ok" : "bad")}>{u.is_active ? u.role : "Désactivé"}</span></p><small>@{u.username}</small></div>)}
      {f && (
        <Modal title={f.id ? f.full_name : "Nouvel employé"} onClose={() => setF(null)} wide>
          <form className="form" onSubmit={save}><Alert>{err}</Alert>
            {!f.id && <Field label="Identifiant *"><input value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} required autoCapitalize="none" /></Field>}
            <Field label="Nom complet *"><input value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} required /></Field>
            <Field label={f.id ? "Nouveau mot de passe (laisser vide pour conserver)" : "Mot de passe * (8 caractères min.)"}><input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} required={!f.id} minLength={f.password ? 8 : undefined} /></Field>
            <Field label="Rôle"><select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="EMPLOYE">Employé</option><option value="ADMIN">Administrateur (tous les droits)</option></select></Field>
            {f.role === "EMPLOYE" && <><p className="muted">Droits de base d'un employé : consulter produits/stock/clients, créer des ventes. Droits supplémentaires :</p>
              {perms.map((p) => <label className="chk" key={p.code}><input type="checkbox" checked={f.extra_permissions.includes(p.code)} onChange={() => toggle(p.code)} /> {p.label}</label>)}</>}
            {f.id && <label className="chk"><input type="checkbox" checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} /> Compte actif</label>}
            <div className="actions"><button className="btn">Enregistrer</button></div></form>
        </Modal>)}
    </>
  );
}
