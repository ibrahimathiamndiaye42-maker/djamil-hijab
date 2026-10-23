# DJAMIL HIJAB — Application de gestion de boutique

Application web (PWA) de gestion : produits, stock, arrivages, ventes, factures PDF, clients, fournisseurs,
employés/permissions, inventaires, contrôle des écarts, journal d'activité, tableau de bord, rapports, paramètres.

**Règle centrale : aucune modification importante du stock n'est invisible.** Le stock ne change que par des
*mouvements* (table `stock_movements`) qui enregistrent : qui, quoi, quand, quantité avant/après, motif. Cette table et
`audit_logs` sont protégées par des triggers PostgreSQL : impossible de les modifier ou supprimer, même pour l'administrateur.

```
djamil-hijab/
├── backend/    API Flask + SQLAlchemy + PostgreSQL (routes → services → modèles), triggers.sql, tests, scripts
└── frontend/   React + Vite, PWA (manifest, service worker, icônes), interface mobile d'abord
```

## 1. Prérequis
Python 3.11+, Node.js 18+, PostgreSQL 14+ (local ou managé : Neon, Supabase, Railway…).

## 2. Variables d'environnement
Copier `backend/.env.example` vers `backend/.env` et renseigner :

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL (`postgresql://user:pass@hote:5432/base`) |
| `SECRET_KEY` | Clé de signature des sessions JWT — **obligatoire en production** (`python -c "import secrets;print(secrets.token_hex(32))"`) |
| `JWT_EXPIRES_MIN` | Durée de session en minutes (480 = 8 h) |
| `CORS_ORIGINS` | URL(s) du frontend autorisées |
| `APP_ENV` | `development` ou `production` (en production, `seed-dev` est interdit) |
| `STORAGE_BACKEND` | `local` (dev) ou `s3` (production) |
| `S3_*` | Bucket, endpoint, clés, URL publique (Cloudflare R2, Supabase Storage, AWS S3…) |

Frontend : `frontend/.env` avec `VITE_API_URL` (laisser vide en local, le proxy Vite redirige `/api`).

## 3. Création de la base et initialisation
```bash
createdb djamil_hijab                      # ou créer la base chez Neon/Supabase
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
export FLASK_APP=wsgi.py
flask init-db        # tables + triggers d'immuabilité + index de recherche + rôles/permissions/paramètres
flask create-admin   # crée le premier compte administrateur (mot de passe 8 caractères min.)
```
`init-db` démarre avec une **base propre** : catégories par défaut (Voiles, Hijabs, Robes, Accessoires, Autres),
coordonnées DJAMIL HIJAB (modifiables dans Paramètres), aucun produit.

### Migrations
Flask-Migrate (Alembic) est branché. Pour versionner les évolutions du schéma :
```bash
flask db init                          # une seule fois (crée backend/migrations)
flask db migrate -m "description"      # génère la migration
flask db upgrade                       # applique
flask apply-triggers                   # réapplique triggers.sql (idempotent)
```
Sur une base créée par `init-db`, lancer une fois `flask db init && flask db stamp head` avant la première migration.

## 4. Lancement local
```bash
# Terminal 1 — API (http://localhost:5000)
cd backend && flask run
# Terminal 2 — Interface (http://localhost:5173)
cd frontend && npm install && npm run dev
```
Données de test (jamais en production) : `flask seed-dev` crée 30 produits fictifs.

## 5. Tests
```bash
cd backend && pytest -v                 # tests automatisés (SQLite en mémoire)
python scripts/seed_perf.py --products 5000 --customers 5000 --sales 100000   # base de TEST PostgreSQL : volume + temps de réponse
```
Les tests couvrent : connexion, permissions refusées aux employés, création de produit, stock non modifiable
directement, vente (stock, mouvement, facture, journal), stock insuffisant, annulation avec avoir, corrections avec motif,
arrivages, inventaire/écarts, absence de route de suppression des journaux, pagination bornée, compte désactivé.
Les triggers PostgreSQL (immuabilité) ne s'exécutent que sur PostgreSQL : les vérifier avec
`UPDATE stock_movements SET qty_delta = 1;` → doit échouer.

## 6. Déploiement (GitHub + Vercel + PostgreSQL + stockage)
1. Pousser le dossier sur GitHub.
2. **Base** : créer une base PostgreSQL managée (Neon ou Supabase), utiliser l'URL *poolée* dans `DATABASE_URL`.
   Depuis votre poste, avec cette URL : `flask init-db` puis `flask create-admin`.
3. **Fichiers** : créer un bucket (Cloudflare R2 / Supabase Storage / S3), le rendre lisible publiquement, renseigner `S3_*`
   et `STORAGE_BACKEND=s3`. Les photos et logos ne sont jamais stockés dans PostgreSQL.
4. **API (projet Vercel n°1)** : *Root Directory* = `backend`. `vercel.json` et `api/index.py` sont fournis.
   Variables : `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS` (URL du frontend), `APP_ENV=production`, `STORAGE_BACKEND=s3`, `S3_*`.
5. **Interface (projet Vercel n°2)** : *Root Directory* = `frontend`, *Framework* = Vite. Variable : `VITE_API_URL=https://<api>.vercel.app/api/v1`.
6. Si la génération de PDF dépasse les limites des fonctions serverless, héberger l'API sur Render/Railway
   (`gunicorn wsgi:app`) : le frontend ne change pas.

## 7. Sauvegardes
- Hébergeur managé : activer les sauvegardes automatiques / restauration à un instant donné (Neon, Supabase).
- En complément : `backend/scripts/backup.sh` (pg_dump compressé, rétention 30 jours, à planifier en cron) puis copier
  le fichier hors du serveur. Restauration : `pg_restore --clean --no-owner -d "$DATABASE_URL" fichier.dump`.
- Les données ne sont jamais stockées uniquement sur le téléphone.

## 8. Installer l'application sur téléphone (PWA)
Ouvrir l'adresse de l'interface (HTTPS) dans Chrome sur Android → menu ⋮ → **Installer l'application** /
**Ajouter à l'écran d'accueil**. L'icône « Djamil Hijab » apparaît comme une application. Sur ordinateur : icône
d'installation dans la barre d'adresse. Le service worker ne met en cache que l'interface ; **les données viennent
toujours du serveur** (pas de stock périmé).

## 9. Sécurité — points à connaître
- Mots de passe hashés (Werkzeug), sessions JWT signées, **permissions vérifiées côté API** sur chaque route.
- Le jeton est conservé dans le navigateur (`localStorage`) : ne pas utiliser l'application sur un appareil partagé sans se déconnecter.
- Pas de limitation de tentatives de connexion intégrée : ajouter un pare-feu applicatif ou un rate-limit (ex. Flask-Limiter + Redis) avant une exposition large.
- Pas de refresh token : la session expire après `JWT_EXPIRES_MIN` et l'utilisateur se reconnecte.
- Les jours (tableau de bord, rapports) sont calculés en UTC, identique à l'heure de Dakar.

## 10. Extensions prévues (architecture compatible)
Codes-barres/QR, impression Bluetooth, multi-boutiques, dépenses et bénéfice réel, export Excel/CSV, notifications,
commandes en ligne, WhatsApp : ajouter des tables/routes/services sans toucher au cœur `services/stock.py`.
