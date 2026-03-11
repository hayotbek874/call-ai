#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-chatbot}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

if [[ -z "${GHCR_USERNAME:-}" || -z "${GHCR_TOKEN:-}" ]]; then
  echo "GHCR_USERNAME va GHCR_TOKEN majburiy"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker topilmadi"
  exit 1
fi

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  COMPOSE_CMD=(docker compose)
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "Repo topilmadi: $APP_DIR"
  exit 1
fi

cd "$APP_DIR"
git fetch --all --prune
git checkout "$DEPLOY_BRANCH"
git pull --ff-only origin "$DEPLOY_BRANCH"

echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

"${COMPOSE_CMD[@]}" -f docker-compose.prod.yml pull api worker telegram-bot nginx
"${COMPOSE_CMD[@]}" -f docker-compose.prod.yml up -d --remove-orphans
docker image prune -af --filter "until=168h"

echo "Deploy tugadi"
