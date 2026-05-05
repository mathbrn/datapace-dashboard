#!/usr/bin/env bash
# deploy.sh — Copie le dashboard genere vers main + gh-pages en une commande.
# Usage: bash deploy.sh [commit message]
set -e

SRC="C:/Users/mathi/Documents/6. DATA PACE/0. Dashboard/Fichiers sources/datapace_dashboard.html"
REPO="C:/Users/mathi/Documents/GitHub/datapace-dashboard"
MSG="${1:-update dashboard}"

cd "$REPO"

# 1. Copier vers main
cp "$SRC" index.html
cp "$SRC" datapace_dashboard.html
git add index.html datapace_dashboard.html
git commit -m "$MSG

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>" || echo "Nothing to commit on main"
git push origin main

# 2. Deployer sur gh-pages
COMMIT=$(git rev-parse --short HEAD)
git checkout gh-pages
git checkout main -- index.html
git commit -m "deploy: $COMMIT" || echo "Nothing to commit on gh-pages"
git push origin gh-pages
git checkout main

echo "Deploye sur main + gh-pages ($COMMIT)"
