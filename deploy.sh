#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> [1/3] Build du frontend React"
cd frontend
npm install --silent
npm run build
cd ..

echo "==> [2/3] Copie du build dans backend/static/"
rm -rf backend/static
cp -r frontend/dist backend/static

echo "==> [3/3] Build et lancement du conteneur Docker"
docker compose build --quiet
docker compose up -d

echo ""
echo "AllocNCE déployé sur http://localhost:8000"
echo "Logs : docker compose logs -f"
