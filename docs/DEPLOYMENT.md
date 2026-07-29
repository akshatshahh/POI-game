# Deploying POI Game for free

Free-tier stack: **Neon** (Postgres) + **Render** (FastAPI backend) +
**Vercel** (static frontend). Total cost: $0. The one compromise: Render's
free tier puts the backend to sleep after ~15 minutes of inactivity, so the
first visit after a quiet period takes 30–60 seconds to wake up.

The repo is already prepared: `render.yaml` (backend blueprint),
`frontend/vercel.json` (SPA routing), and the backend translates managed-
Postgres connection strings (`sslmode=require`) for its async driver
automatically.

## 1. Database — Neon (free)

1. Sign up at https://neon.tech, create a project (pick a US-west/LA-adjacent
   region).
2. In the SQL editor run: `CREATE EXTENSION IF NOT EXISTS postgis;`
   (available on the free tier; needed by the places table geometry column).
3. Copy the connection string — it looks like
   `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`.
   Use it as-is everywhere below; the app handles the SSL params.

## 2. Backend — Render (free)

1. Sign up at https://render.com with your GitHub account.
2. New → Blueprint → select this repo. Render reads `render.yaml` and creates
   the `poi-game-backend` service.
3. Fill in the env vars it prompts for:
   - `DATABASE_URL` — the Neon string from step 1
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — from Google Cloud Console
   - `BACKEND_URL` — the service's own URL (shown after first deploy,
     `https://poi-game-backend.onrender.com`)
   - `FRONTEND_URL` — fill after step 3 (`https://<your-app>.vercel.app`)
4. The start command runs `alembic upgrade head` automatically on every
   deploy, so the schema is always current.

## 3. Frontend — Vercel (free)

1. Sign up at https://vercel.com with GitHub, import this repo.
2. Set **Root Directory** to `frontend` (framework auto-detects Vite).
3. Add env var `VITE_API_URL = https://poi-game-backend.onrender.com`
   (build-time env beats the tracked `.env.production`, which still points at
   the old Railway deploy).
4. Deploy, note the URL, and put it into Render's `FRONTEND_URL` — exact
   origin, no trailing slash (CORS is exact-match).

## 4. Google OAuth redirect

In Google Cloud Console → Credentials → your OAuth client, add:
- Authorized redirect URI: `https://poi-game-backend.onrender.com/auth/google/callback`
- Authorized JavaScript origin: `https://<your-app>.vercel.app`

## 5. Seed the production database (run locally)

The `places` table lives outside Alembic; seed it from your machine against
the Neon database:

```bash
cd backend && source .venv/bin/activate
DATABASE_URL='postgresql://...neon...?sslmode=require' python scripts/seed_production_data.py
```

(1–3 minutes; pulls Overture POIs and generates GPS visit points.)

## 6. Make yourself admin

In the Neon SQL editor:

```sql
UPDATE users SET is_admin = true WHERE email = 'you@example.com';
```

(Log in through the app once first so the row exists.)

## Notes and gotchas

- **Cold starts:** a free uptime monitor (e.g. UptimeRobot) pinging
  `GET /health` every 10–15 minutes keeps the backend warm during a study
  session. Render tolerates this but it burns your free instance hours
  (~750/month — fine for one service); turn the monitor off when not
  collecting data.
- **Sybil gate:** `CONSENSUS_MIN_ACCOUNT_AGE_MINUTES=60` is set in
  render.yaml — new accounts earn points immediately but their votes count
  toward consensus only after an hour.
- **Cookies:** login relies on `SameSite=None; Secure` cookies, derived from
  `BACKEND_URL` starting with `https` — both Render and Vercel URLs are
  https, so this works out of the box. If login "succeeds then bounces",
  re-check `FRONTEND_URL`/`BACKEND_URL` for typos or trailing slashes.
- **Free-tier limits:** Neon free = 0.5 GB storage (the LA places table +
  game data fit easily); Render free = 512 MB RAM single instance (the
  in-process rate limiter assumes exactly this).
- **Alternatives:** Cloudflare Pages instead of Vercel (same steps),
  Supabase instead of Neon (PostGIS included; free projects pause after a
  week of inactivity), Koyeb or an Oracle Cloud always-free VM instead of
  Render if cold starts become a problem.
