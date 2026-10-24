// Gestion de l'installation de l'application (PWA). Importé tôt (main.jsx) pour ne pas rater l'événement du navigateur.
import { useEffect, useState } from "react";

let deferred = null;
const listeners = new Set();
const notify = () => listeners.forEach((f) => f());
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; notify(); });
window.addEventListener("appinstalled", () => { deferred = null; notify(); });

export const isStandalone = () => window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
export const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);

export async function promptInstall() {
  if (!deferred) return false;
  deferred.prompt();
  const choice = await deferred.userChoice;
  deferred = null; notify();
  return choice.outcome === "accepted";
}

export function usePwa() {
  const [, tick] = useState(0);
  useEffect(() => { const f = () => tick((n) => n + 1); listeners.add(f); return () => listeners.delete(f); }, []);
  return { canPrompt: !!deferred, installed: isStandalone(), ios: isIOS() };
}
