// Jeu d'icônes maison (trait fin, 24x24) — remplace les emojis pour une interface plus sobre et professionnelle.
const P = {
  dashboard: <><rect x="3" y="3" width="7" height="9" rx="1.6" /><rect x="14" y="3" width="7" height="5" rx="1.6" /><rect x="14" y="12" width="7" height="9" rx="1.6" /><rect x="3" y="16" width="7" height="5" rx="1.6" /></>,
  products: <><path d="M21 8l-9-5-9 5 9 5 9-5z" /><path d="M3 8v8l9 5 9-5V8" /><path d="M12 13v8" /></>,
  sell: <><path d="M6 2L3 6v13a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 01-8 0" /></>,
  invoice: <><path d="M5 3h14v18l-2.5-1.5L14 21l-2-1.5L10 21l-2.5-1.5L5 21z" /><path d="M9 8h6M9 12h6" /></>,
  users: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" /><path d="M16 4.7a3.5 3.5 0 010 6.6" /><path d="M18 14.4c2.2.7 3.5 2.6 3.5 5.6" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" /></>,
  shield: <><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M9 12l2 2 4-4" /></>,
  settings: <><path d="M4 7h9M17 7h3M4 17h3M11 17h9" /><circle cx="15" cy="7" r="2" /><circle cx="9" cy="17" r="2" /></>,
  stock: <><path d="M12 3l9 5-9 5-9-5z" /><path d="M3 13l9 5 9-5" /></>,
  arrivals: <><path d="M2 6h11v10H2z" /><path d="M13 9h4l3 3v4h-7z" /><circle cx="6" cy="18" r="1.8" /><circle cx="17" cy="18" r="1.8" /></>,
  suppliers: <><path d="M4 21V5l8-2v18" /><path d="M12 9h8v12" /><path d="M8 8h.01M8 12h.01M8 16h.01M16 13h.01M16 17h.01" /></>,
  inventory: <><rect x="6" y="4" width="12" height="17" rx="2" /><path d="M9 4V3h6v1" /><path d="M9 13l2 2 4-4" /></>,
  control: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>,
  reports: <><path d="M5 20V11M12 20V4M19 20v-6" /><path d="M3 20h18" /></>,
  download: <><path d="M12 3v12" /><path d="M7 11l5 5 5-5" /><path d="M4 20h16" /></>,
  logout: <><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><path d="M16 17l5-5-5-5" /><path d="M21 12H9" /></>,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  share: <><circle cx="18" cy="5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="19" r="2.5" /><path d="M8.2 10.8l7.6-4.3M8.2 13.2l7.6 4.3" /></>,
  alert: <><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18h.01" /></>,
  whatsapp: <><path d="M3 21l1.7-5.2A9 9 0 1112 21a9 9 0 01-4.4-1.2z" /><path d="M9 8.5c0 3.8 2.7 6.5 6.5 6.5l1.3-1.7-2.2-1.1-1 .9c-1-.5-1.8-1.3-2.3-2.3l.9-1-1.1-2.2z" /></>,
  phone: <><rect x="7" y="2" width="10" height="20" rx="2.5" /><path d="M11 18h2" /></>,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
};

export function Icon({ name, size = 20 }) {
  return (
    <svg className="ico" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{P[name]}</svg>
  );
}
