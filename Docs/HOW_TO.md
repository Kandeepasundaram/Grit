# Grit — How-To Guide

## Running the Application

Grit has three runnable components. You only need all three for enterprise org management.
Day-to-day Git identity switching only needs the **daemon**.

| Component | What it does | When you need it |
|-----------|-------------|-----------------|
| Grit daemon | Resolves profiles, intercepts commits | Always |
| Admin UI | Browser UI for org/SSO/audit management | Enterprise / team admin |
| Backend API | Auth, cloud sync, licensing, org data | Admin UI + Pro/Enterprise |

---

## 1 — Grit Daemon (always required)

### Install

```bash
pip install grit
```

### First-time setup

```bash
grit setup
```

Walks you through creating your first profile and installs the daemon autostart entry for your OS. After this, the daemon starts automatically on every login.

### Manual start / stop

```bash
grit daemon start            # background (normal use)
grit daemon start --foreground --verbose   # foreground (debugging)
grit daemon status           # check it's running + active sessions
grit daemon stop
grit daemon restart          # after config changes
```

### Verify IPC is working

```bash
grit daemon status
# Expected output:
#   Daemon running (PID xxxxx)
#     Version:         0.1.0-alpha
#     Active sessions: 0
#     Profiles:        2
```

On **Windows**, the daemon uses a loopback TCP socket. The port is written to:
```
%LOCALAPPDATA%\grit\data\grit.port
```

On **macOS / Linux**, it uses a Unix domain socket at:
```
~/.local/share/grit/grit.sock
```

---

## 2 — Admin UI (enterprise / team admin)

### Prerequisites

- Node.js 18+ and npm
- The backend API must be running (see section 3) for login and live data

### Install dependencies (once)

```bash
cd admin-ui
npm install
```

### Start the dev server

```bash
npm run dev
# → http://localhost:3000
```

The dev server proxies all `/v1`, `/oauth`, and `/webhooks` requests to `http://localhost:8000` (the backend).

### Production build

```bash
npm run build        # output goes to admin-ui/dist/
npm run type-check   # TypeScript validation before building
```

Serve `admin-ui/dist/` from any static host (nginx, Caddy, S3 + CloudFront, etc.).

---

## 3 — Backend API (required for Admin UI)

### Prerequisites

- Docker and Docker Compose, **or** Python 3.8+ with pip
- A GitHub OAuth App (for login) — see [GitHub docs](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)

### Environment setup

```bash
cd backend
cp .env.example .env
```

Edit `.env` and fill in:

```env
GRIT_GITHUB_CLIENT_ID=your_github_client_id
GRIT_GITHUB_CLIENT_SECRET=your_github_client_secret
GRIT_SECRET_KEY=a-long-random-string-change-in-production
GRIT_DATABASE_URL=postgresql+psycopg://grit:grit@localhost:5432/grit
GRIT_REDIS_URL=redis://localhost:6379/0
```

### Generate RSA license keys (once)

```bash
python ../scripts/generate_license_keys.py
# Writes:
#   backend/license_private.pem   (keep secret)
#   src/grit/cloud/license_public.pem  (bundled in client)
```

### Start with Docker Compose (recommended)

```bash
docker-compose up
# Starts: postgres:16 + redis:7 + uvicorn (FastAPI)
```

The API is available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### Start without Docker

```bash
pip install -e ".[dev]"
pip install fastapi uvicorn sqlalchemy asyncpg pydantic-settings httpx stripe
cd backend
uvicorn app.main:app --reload --port 8000
```

You'll need a running PostgreSQL and Redis instance separately.

---

## Logging in to the Admin UI

The Admin UI uses **GitHub OAuth device flow** proxied through the backend.

### Full login (backend running)

1. Open `http://localhost:3000`
2. Click **Sign in with GitHub**
3. A GitHub page opens — enter the displayed code
4. Click **OK** in the browser prompt
5. You're logged in — the JWT is stored in `localStorage`

> **GitHub OAuth App settings:**
> - Authorization callback URL: `http://localhost:8000/oauth/github/callback`
> - No specific scope needed — Grit only reads your email

### Setting your org (after login)

The admin UI needs to know which organisation to manage. After signing in, open the browser console and run:

```js
localStorage.setItem('grit_org_id', 'your-org-uuid-here')
location.reload()
```

The org UUID is returned when you create an organisation via the API:

```bash
curl -X POST http://localhost:8000/v1/enterprise/orgs \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "slug": "acme"}'
# → {"id": "xxxxxxxx-...", "name": "Acme Corp", ...}
```

### Dev login (no backend needed)

When the backend is not running, use one of these two shortcuts available in development mode (`npm run dev`):

**Option A — `VITE_DEV_TOKEN` in `.env.local`**

Create `admin-ui/.env.local`:

```env
VITE_DEV_TOKEN=any-string-you-like
```

Restart the dev server. A yellow **Dev: auto-login** button appears on the login page — click it to bypass OAuth and enter the app immediately.

> Note: without a real backend token, API calls will fail with 401. This is only useful for working on the UI layout and static pages (like Help).

**Option B — paste a token manually**

A small **"Paste a token manually"** link appears below the GitHub button in dev mode. Click it and paste any bearer token — useful when you have a real backend token from a previous session or a test token generated with:

```bash
# Generate a test token using the backend's secret key
python - <<'EOF'
import jwt, datetime
payload = {
    "sub": "test-user-id",
    "email": "you@example.com",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8),
}
print(jwt.encode(payload, "change-me-in-production", algorithm="HS256"))
EOF
```

---

## Typical Development Workflow

### Working on the Grit CLI / daemon

```bash
# Terminal 1 — daemon in foreground so you see logs
grit daemon start --foreground --verbose

# Terminal 2 — test CLI commands
cd /any/git/repo
grit profile add          # interactive flow
grit session show
git commit -m "test"      # triggers the hook → daemon applies profile
```

### Working on the Admin UI only (no backend)

```bash
# Set a dev token so the login screen is bypassed
echo "VITE_DEV_TOKEN=dev" > admin-ui/.env.local

# Start the UI
cd admin-ui && npm run dev
# → http://localhost:3000  (click the yellow dev-login button)
```

### Full stack

```bash
# Terminal 1 — backend
cd backend && docker-compose up

# Terminal 2 — daemon
grit daemon start --foreground --verbose

# Terminal 3 — admin UI
cd admin-ui && npm run dev
```

---

## Stopping Everything

```bash
# Daemon
grit daemon stop

# Admin UI dev server — Ctrl+C in its terminal

# Backend (Docker)
cd backend && docker-compose down

# Backend (without Docker) — Ctrl+C in its terminal
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Install Grit | `pip install grit` |
| First-time setup | `grit setup` |
| Start daemon | `grit daemon start` |
| Stop daemon | `grit daemon stop` |
| Daemon status | `grit daemon status` |
| Add a profile (interactive) | `grit profile add` |
| Add a profile (flags) | `grit profile add --name Work --email x@y.com` |
| List profiles | `grit profile list` |
| Show active session | `grit session show` |
| Switch profile for repo | `grit session set Work` |
| Start Admin UI (dev) | `cd admin-ui && npm run dev` |
| Start backend (Docker) | `cd backend && docker-compose up` |
| Backend API docs | `http://localhost:8000/docs` |
| Admin UI | `http://localhost:3000` |
