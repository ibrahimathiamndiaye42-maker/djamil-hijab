import { useState } from "react";
import { useAuth } from "../auth";
import { Alert, Field } from "../ui";
import InstallButton from "../Install.jsx";

export default function Login() {
  const { login } = useAuth();
  const [u, setU] = useState(""); const [p, setP] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { await login(u, p); } catch (x) { setErr(x.message); }
    setBusy(false);
  };
  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <h1>DJAMIL HIJAB</h1><p className="muted">Gestion de la boutique</p>
        <Alert>{err}</Alert>
        <Field label="Identifiant"><input value={u} onChange={(e) => setU(e.target.value)} autoCapitalize="none" autoFocus required /></Field>
        <Field label="Mot de passe"><input type="password" value={p} onChange={(e) => setP(e.target.value)} required /></Field>
        <button className="btn" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
      </form>
      <div className="login-install"><InstallButton className="btn ghost install" label="Installer l'application sur mon téléphone" /></div>
    </div>
  );
}
