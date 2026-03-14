#!/usr/bin/env bash
set -euo pipefail

# Usage:
# REMOTE_HOST=198.163.207.194 REMOTE_USER=uz-user REMOTE_PASSWORD=... \
# VITE_GEMINI_API_KEY=... VITE_API_BASE_URL=https://api.example.com \
# ./scripts/deploy_remote.sh

REMOTE_HOST="${REMOTE_HOST:?REMOTE_HOST is required}"
REMOTE_USER="${REMOTE_USER:?REMOTE_USER is required}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:?REMOTE_PASSWORD is required}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/home/${REMOTE_USER}/stratix-call-operator}"
REMOTE_PORT="${REMOTE_PORT:-8080}"
IMAGE_NAME="${IMAGE_NAME:-stratix-call-operator:latest}"

VITE_GEMINI_API_KEY="${VITE_GEMINI_API_KEY:?VITE_GEMINI_API_KEY is required}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-}"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR" /tmp/.codex_askpass.sh' EXIT

cat > /tmp/.codex_askpass.sh <<ASKPASS
#!/bin/sh
echo "$REMOTE_PASSWORD"
ASKPASS
chmod 700 /tmp/.codex_askpass.sh

run_ssh() {
  DISPLAY=:999 SSH_ASKPASS=/tmp/.codex_askpass.sh SSH_ASKPASS_REQUIRE=force \
    setsid ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$@"
}

run_scp() {
  DISPLAY=:999 SSH_ASKPASS=/tmp/.codex_askpass.sh SSH_ASKPASS_REQUIRE=force \
    setsid scp -o StrictHostKeyChecking=no "$@"
}

# Create minimal deployment bundle (frontend only)
rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'dist' \
  --exclude '.env' \
  --exclude '.env.local' \
  ./ "$WORKDIR/app/"

cat > "$WORKDIR/app/.env.production" <<ENV
VITE_GEMINI_API_KEY=$VITE_GEMINI_API_KEY
VITE_API_BASE_URL=$VITE_API_BASE_URL
VITE_DEV_HTTPS=false
ENV

tar -C "$WORKDIR" -czf "$WORKDIR/app.tar.gz" app

run_ssh "mkdir -p '$REMOTE_APP_DIR'"
run_scp "$WORKDIR/app.tar.gz" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_APP_DIR/app.tar.gz"

run_ssh "
  set -e
  cd '$REMOTE_APP_DIR'
  rm -rf app && mkdir -p app
  tar -xzf app.tar.gz -C .
  cd app
  docker build -t '$IMAGE_NAME' .
  docker rm -f stratix-call-operator >/dev/null 2>&1 || true
  docker run -d --name stratix-call-operator --restart unless-stopped -p '$REMOTE_PORT':80 '$IMAGE_NAME'
"

echo "Deployment completed: http://$REMOTE_HOST:$REMOTE_PORT"
