<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Stratix AI Call Operator (Frontend)

This project is a Vite + React web client for AI voice calls.

## 1) Local development

**Prerequisites:** Node.js 20+

1. Install dependencies:
   ```bash
   npm install
   ```
2. Create local env file:
   ```bash
   cp .env.example .env.local
   ```
3. Set `VITE_GEMINI_API_KEY` in `.env.local`.
4. (Optional) If backend is separate during development, set `VITE_DEV_API_PROXY_TARGET`.
5. Start dev server:
   ```bash
   npm run dev
   ```

> If your environment has file-watcher limits, run:
> ```bash
> CHOKIDAR_USEPOLLING=true npm run dev
> ```

## 2) Production build

1. Create production env file:
   ```bash
   cp .env.example .env.production
   ```
2. Set production values:
   - `VITE_GEMINI_API_KEY`
   - `VITE_API_BASE_URL` (for example `https://api.your-domain.uz`)
   - `VITE_DEV_HTTPS=false` (optional; only affects dev)
3. Build static assets:
   ```bash
   npm run build
   ```
4. Test locally:
   ```bash
   npm run preview
   ```

## 3) Deploy to real server (Docker + Nginx)

This repo includes a production `Dockerfile` and `deploy/nginx/default.conf`.

### Option A — Manual deploy

```bash
docker build -t stratix-call-operator:latest .
docker run -d --name stratix-call-operator -p 8080:80 stratix-call-operator:latest
```

Then open: `http://<server-ip>:8080`

### Option B — Remote deploy script (recommended)

A ready script is provided at `scripts/deploy_remote.sh`.

```bash
REMOTE_HOST=198.163.207.194 \
REMOTE_USER=uz-user \
REMOTE_PASSWORD='your-password' \
VITE_GEMINI_API_KEY='your-gemini-key' \
VITE_API_BASE_URL='https://api.your-domain.uz' \
REMOTE_PORT=8080 \
./scripts/deploy_remote.sh
```

The script will:
- create a clean deployment bundle,
- upload it to the remote host,
- build Docker image on the server,
- restart container `stratix-call-operator`.

## 4) Environment variables

See `.env.example` for all supported variables.

- `VITE_GEMINI_API_KEY` — required
- `VITE_API_BASE_URL` — optional but recommended in production
- `VITE_DEV_HTTPS` — local-only
- `VITE_DEV_API_PROXY_TARGET` — local-only
