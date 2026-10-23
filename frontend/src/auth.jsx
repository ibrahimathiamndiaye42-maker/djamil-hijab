import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [settings, setSettings] = useState(null);
  const [ready, setReady] = useState(false);

  const boot = async () => {
    try { setUser((await api("/auth/me")).user ?? null); setSettings(await api("/settings")); } catch { setUser(null); }
    setReady(true);
  };
  useEffect(() => {
    if (getToken()) boot(); else setReady(true);
    const out = () => setUser(null);
    window.addEventListener("dh-logout", out);
    return () => window.removeEventListener("dh-logout", out);
  }, []);

  const login = async (username, password) => {
    const r = await api("/auth/login", { method: "POST", body: { username, password } });
    setToken(r.token); setUser(r.user); setSettings(await api("/settings"));
  };
  const logout = () => { setToken(null); setUser(null); };
  const can = (...perms) => !!user && perms.some((p) => user.permissions.includes(p));
  const reloadSettings = async () => setSettings(await api("/settings"));
  return <Ctx.Provider value={{ user, settings, ready, login, logout, can, reloadSettings }}>{children}</Ctx.Provider>;
}
