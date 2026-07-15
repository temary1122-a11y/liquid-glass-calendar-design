# 🚀 Liquid Glass — How It's Actually Deployed

## Architecture

| Component | Where | How |
|-----------|-------|-----|
| **Frontend** (React + Vite) | GitHub Pages | `.github/workflows/deploy.yml` on push to `main` |
| **Backend API** (FastAPI) | Render Free Tier | `backend/render.yaml` — Web Service |
| **Telegram Bot** (aiogram 3) | Render Free Tier | Same service as backend, webhook-based |
| **Database** | Supabase (Neon PostgreSQL) | `DATABASE_URL` env var → connection string |
| **Scheduler** (APScheduler) | Render Free Tier | Runs inside the same backend process |

**Deprecated / removed:**
- ~~Netlify~~ — never used (root `render.yaml` was a leftover comment)
- ~~Vercel~~ — DEPLOYMENT.md was out of date, frontend lives on GitHub Pages
- ~~Railway~~ — in `.gitignore`, never deployed
- ~~Dockerfile~~ — not present, Render uses Python native build

---

## Render Setup

**Backend Web Service** configured via `backend/render.yaml`:
- Runtime: Python 3.x
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health: `GET /health`

**Environment Variables (set in Render Dashboard, NOT in code):**

| Variable | Purpose | Notes |
|----------|---------|-------|
| `BOT_TOKEN` | Telegram Bot API token | From @BotFather |
| `ADMIN_ID` | Telegram user ID of admin | From @userinfobot |
| `ADMIN_SECRET_KEY` | HMAC secret for admin auth | Random 32-char string |
| `DATABASE_URL` | Supabase PostgreSQL URL | `postgres://...` or `postgresql://...` |
| `WEBHOOK_URL` | Telegram webhook URL | `https://<render-app>.onrender.com/webhook` |
| `MINI_APP_URL` | Frontend URL | `https://temary1122-a11y.github.io/liquid-glass-calendar-design/` |

**⚠️ All secrets MUST be configured in Render Dashboard. Never commit to git.**

---

## GitHub Pages (Frontend)

**Workflow:** `.github/workflows/deploy.yml`
- Triggered on push to `main`
- Builds with `npm run build`
- Publishes `dist/` to GitHub Pages
- Sets `VITE_BACKEND_URL` and `VITE_WS_URL` during build

---

## Supabase Database

**Schema:** `time_slots`, `work_days`, `bookings` tables
- `time_slots`: `id, day_date, slot_time, is_booked`
- `work_days`: `id, day_date, is_closed`
- `bookings`: `id, user_id, username, client_name, phone, day_date, slot_time, status, note, created_at, is_cancelled, cancel_reason, cancelled_at, service_id`

Key design decision: NO foreign keys between tables (denormalized day_date/slot_time). Models match this exactly — no ORM relationship traversal needed, all queries use direct field lookups.

---

## Post-Deploy Verification

1. `GET https://<render-app>.onrender.com/health` → `{"status":"healthy"}`
2. `GET https://<render-app>.onrender.com/api/booking/available-dates` → returns JSON array
3. Open Mini App in Telegram → calendar loads, slots visible
4. Make a test booking → admin receives notification
