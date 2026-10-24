import { useState } from "react";
import { Icon } from "./icons";
import { promptInstall, usePwa } from "./pwa";
import { Modal } from "./ui";

/** Bouton « Installer l'application » : installation directe si le navigateur le permet, sinon mode d'emploi. */
export default function InstallButton({ className = "btn ghost install", label = "Installer l'application" }) {
  const { canPrompt, installed, ios } = usePwa();
  const [help, setHelp] = useState(false);
  if (installed) return null;
  const click = async () => { if (canPrompt) await promptInstall(); else setHelp(true); };
  return (
    <>
      <button type="button" className={className} onClick={click}><Icon name="download" size={18} /> <span>{label}</span></button>
      {help && (
        <Modal title="Installer l'application" onClose={() => setHelp(false)}>
          {ios ? (
            <ol className="steps">
              <li>Ouvrez cette page dans <b>Safari</b>.</li>
              <li>Touchez le bouton <b>Partager</b> (le carré avec une flèche vers le haut).</li>
              <li>Choisissez <b>« Sur l'écran d'accueil »</b>, puis <b>Ajouter</b>.</li>
            </ol>
          ) : (
            <ol className="steps">
              <li>Ouvrez cette page dans <b>Google Chrome</b> (pas depuis WhatsApp).</li>
              <li>Touchez le menu <b>⋮</b> en haut à droite.</li>
              <li>Choisissez <b>« Installer l'application »</b> ou <b>« Ajouter à l'écran d'accueil »</b>.</li>
            </ol>
          )}
          <p className="muted">L'icône de la boutique apparaît ensuite sur l'écran d'accueil, comme une application classique.</p>
        </Modal>)}
    </>
  );
}
