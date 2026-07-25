# AllocNCE

Gestion des allocations d'appareils EasyJet — base de Nice (NCE).

## Stack

| Couche | Tech |
|---|---|
| Backend | Python 3.13 / FastAPI / Uvicorn |
| ORM + migrations | SQLAlchemy 2 + Alembic |
| Base de données | SQLite (`data/alloc_nce.db`) |
| Génération DOCX | python-docx |
| Parsing PDF | pdfplumber |
| Frontend | React 18 + Vite + TailwindCSS v4 |

---

## Démarrage rapide (développement)

```bash
# 1. Installer toutes les dépendances
make install

# 2. Appliquer les migrations DB
make migrate

# 3. Créer le compte administrateur (une seule fois)
cd backend && .venv/bin/python create_admin.py \
    --email admin@allocnce.fr --name "Admin"

# 4. Lancer backend + frontend en parallèle
make dev
```

- Backend API : http://localhost:8000
- Swagger : http://localhost:8000/docs
- Frontend : http://localhost:5173

---

## Authentification

Toutes les routes `/allocations/*` et `/files/*` exigent un token JWT ;
chaque utilisateur ne voit que ses propres allocations.

`create_admin.py` crée (ou promeut) un compte `role="admin"`. Sans `--no-claim`,
il rattache aussi à ce compte les allocations sans propriétaire — c'est ce qui
rend visibles les allocations créées avant la mise en place de
l'authentification. Le mot de passe est demandé de façon interactive s'il n'est
pas passé via `--password`.

Les autres comptes se créent depuis `/register`, ou via l'écran
`/admin` (réservé aux administrateurs) pour changer un rôle ou désactiver un
compte. Un compte désactivé est refusé immédiatement, même si son token n'a pas
encore expiré.

**Clé de signature** : la variable d'environnement `SECRET_KEY` doit être
définie en production. En développement, une clé aléatoire est générée dans
`backend/.secret_key` (ignoré par git) afin que les sessions survivent aux
redémarrages d'uvicorn. Changer la clé invalide tous les tokens émis.

---

## Déploiement Docker (production)

AllocNCE est une application **full-stack** : le frontend React est servi par le
backend FastAPI, qui a besoin de Python pour parser les PDF, générer les DOCX et
gérer l'authentification. Un hébergement de fichiers statiques (GitHub Pages,
Netlify, S3 seul…) ne peut donc **pas** faire tourner l'application : les pages
de connexion s'afficheraient sans qu'aucun appel API ne fonctionne.

Créer d'abord un fichier `.env` à côté de `docker-compose.yml` :

```bash
echo "SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')" > .env
```

Sans lui, le conteneur refuse de démarrer — c'est volontaire : une clé
regénérée à chaque redémarrage déconnecterait tous les utilisateurs.

Puis :

```bash
./deploy.sh
```

Il effectue dans l'ordre :
1. `npm run build` — compile le frontend React
2. Copie le build dans `backend/static/` (servi par FastAPI via StaticFiles)
3. `docker compose build && docker compose up -d`

Au démarrage, le conteneur applique `alembic upgrade head` avant de lancer
uvicorn : un volume neuf est donc migré automatiquement.

L'application est alors disponible sur **http://localhost:8000**.

Créer le premier administrateur, une fois le conteneur lancé :

```bash
docker compose exec backend python create_admin.py --email admin@allocnce.fr --name "Admin"
```

### Volume persistant

PDFs sources et fichiers DOCX sont stockés dans le volume Docker `alloc_data` (`/app/data/`). La base SQLite y réside aussi.

```bash
# Voir les logs
docker compose logs -f

# Arrêter
docker compose down

# Arrêter et supprimer les données (irréversible)
docker compose down -v
```

---

## Migrations Alembic

```bash
# Appliquer les migrations en attente
make migrate

# Créer une nouvelle migration après modification de models.py
cd backend && ../.venv/bin/alembic revision --autogenerate -m "description"
```

---

## Utilisation

### Séquence typique pour une journée

| Étape | Action | Description |
|---|---|---|
| 1 | **Pré-allocation** | Upload du rapport EasyJet J-1, optionnellement la feuille de journée pour comparer |
| 2 | **Allocation finale** | Upload du rapport J, basé sur la pré-alloc — les différences sont surlignées |
| 3 | **Mise à jour** | Chaque nouveau rapport crée une version v2, v3… avec les nouveaux changements en surbrillance |

### Couleurs de surlignage

| Index | Couleur | Usage |
|---|---|---|
| 0 | Jaune | Pré-allocation (diff vs feuille de journée) |
| 1 | Vert | Allocation finale (diff vs pré-alloc) |
| 2 | Cyan | MAJ v2 |
| 3 | Rose | MAJ v3+ |

### Interface

- **Cliquer sur une carte** ouvre le panneau de détail (métadonnées, historique, téléchargement)
- **Recherche** : filtrer par date (`27JUN26`) ou label — raccourci `/` pour focus
- **Archiver** : masquer les anciennes allocations sans les supprimer (persisté en localStorage)
- **Voir archivées** : toggle visible uniquement si des allocations sont archivées

---

## API

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/allocations/` | Liste groupée par date |
| `GET` | `/allocations/stats` | `{total, by_type, last_date}` |
| `POST` | `/allocations/create` | Nouvelle allocation (PDF + date) |
| `POST` | `/allocations/prealloc` | Pré-allocation (PDF alloc + PDF FJ optionnel + date) |
| `POST` | `/allocations/finale` | Allocation finale (PDF + parent_id + date) |
| `POST` | `/allocations/{id}/update` | Mise à jour (nouveau PDF) |
| `GET` | `/allocations/{id}/download` | Télécharger le DOCX |
| `DELETE` | `/allocations/{id}` | Supprimer (DB + fichiers disque) |
| `GET` | `/health` | Health check |

---

## Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

186 tests — unitaires + intégration sur fichiers PDF réels.

---

## Structure

```
alloc-nce/
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── Makefile
├── backend/
│   ├── main.py              # App FastAPI + CORS + StaticFiles (prod)
│   ├── models.py            # ORM SQLAlchemy
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Engine + session
│   ├── routers/
│   │   ├── allocations.py   # CRUD /allocations + /stats
│   │   └── files.py         # Fichiers /files
│   ├── services/
│   │   ├── pdf_parser.py    # Parsing rapport EasyJet
│   │   ├── alloc_builder.py # Assemblage + generate_label
│   │   ├── docx_generator.py# Génération DOCX avec couleurs
│   │   └── comparator.py    # Diff entre allocations / feuille de journée
│   ├── tests/
│   │   ├── test_pdf_parser.py
│   │   ├── test_alloc_builder.py
│   │   ├── test_docx_generator.py
│   │   ├── test_comparator.py
│   │   └── test_integration.py
│   └── alembic/             # Migrations DB
├── frontend/
│   └── src/
│       ├── pages/MesAllocs.jsx    # Page principale
│       ├── components/
│       │   ├── AllocDetail.jsx    # Panneau latéral de détail
│       │   ├── FileDropZone.jsx   # Upload drag-and-drop
│       │   ├── Modal.jsx          # Overlay réutilisable
│       │   ├── ModalCreate.jsx
│       │   ├── ModalPrealloc.jsx
│       │   ├── ModalFinale.jsx
│       │   └── ModalUpdate.jsx
│       └── api.js                 # Client fetch
└── data/
    └── uploads/             # PDFs sources + DOCX générés
```
