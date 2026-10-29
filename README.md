# POI Game — USC IMSC

Internal project for **USC IMSC** — a gamified web app to collect human-labeled
training data for **POI (Point of Interest) Attribution**. Players are shown
GPS visits on a map and asked to identify which nearby POI the person was
most likely visiting; their answers become consensus-labeled training data.

Live: **https://poi-game.vercel.app**

## Architecture

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│   Frontend   │──────▶│   Backend API    │──────▶│  PostgreSQL/PostGIS  │
│  React+Vite  │◀──────│    FastAPI       │◀──────│  + Overture Places   │
└─────────────┘       └──────────────────┘       └──────────────────────┘
       │                       │
       │  Google OAuth 2.0     │
       └───────────────────────┘
```

### Components

| Layer | Tech | Location |
|-------|------|----------|
| Frontend | React 19 + Vite + TypeScript | `frontend/` |
| Backend | FastAPI (Python 3.12) | `backend/` |
| Database | PostgreSQL 16 + PostGIS 3 | Neon (prod), local Postgres.app for dev |
| POI Data | Overture Maps "Places" table | seeded via `backend/scripts/` (see Data Pipeline) |
| Auth | Google OAuth 2.0 + local username/password | backend handles both flows |
| Maps | Leaflet + CARTO/OSM tiles | frontend |
| Deployment | Vercel (frontend) + Render (backend) + Neon (Postgres) | `render.yaml`, `frontend/vercel.json` |

## Features

- **Auth** — Google OAuth (server-side) or local register/login; sessions in HttpOnly cookies
- **Game Screen** — full-page Leaflet map with numbered candidate pins and a bottom candidate list
- **Answer Submission** — pick the most likely POI; answer is stored and scored server-side
- **Agreement tracking** — questions collect set answers, store mean pairwise Jaccard, and complete at 10 answers without naming a winning place
- **Scoring** — 5 participation points per answer; proximity is recorded but not scored
- **Leaderboard** — ranked view of players with at least one answer (login required)
- **Admin Exports** — raw annotations *and* consensus dataset (CSV/JSON) for ML training
- **Data Pipeline** — Overture Maps import + synthetic GPS visit generation from real POIs

## Project Structure

```
POI-game/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── main.py        # App entry point, routes, middleware
│   │   ├── config.py      # Environment-based settings
│   │   ├── database.py    # Async SQLAlchemy engine & sessions
│   │   ├── models.py      # ORM models (User, GpsPoint, Question, Answer)
│   │   ├── schemas.py     # Pydantic request/response schemas
│   │   ├── auth.py        # JWT creation, verification, dependencies
│   │   ├── geo.py         # Shared geo helpers (H3, haversine)
│   │   ├── routers/       # Route handlers (auth, game, admin, etc.)
│   │   └── services/      # Business logic (POI queries, questions, scoring)
│   ├── alembic/           # Database migrations (users/gps_points/questions/answers)
│   ├── scripts/           # Data pipeline: Overture seed + H3 backfill
│   └── tests/             # Pytest test suite
├── frontend/              # React + Vite + TypeScript
│   └── src/
│       ├── pages/         # Home, Play, Leaderboard, Login, Register
│       ├── components/    # Navbar, GameMap, PlayMapHud, ClockPanel, ...
│       ├── hooks/         # useAuth
│       └── lib/           # API client, types, time helpers
├── infra/                 # docker-compose for local db+backend
├── render.yaml            # Backend blueprint (Render)
├── frontend/vercel.json   # Frontend routing + /api proxy (Vercel)
├── docs/
│   ├── DEPLOYMENT.md      # Live-stack setup notes
│   ├── DEVLOG.md          # Development log with decisions
│   └── TESTING.md         # Test guide and manual checklist
└── README.md
```

## Configuration

Backend settings live in `backend/app/config.py`; `.env.example` mirrors them.
The knobs that actually shape gameplay/consensus:

| Variable | Purpose | Default |
|----------|---------|---------|
| `ENVIRONMENT` | `production` enforces long `SECRET_KEY`, requires Google OAuth, disables `/docs` | `development` |
| `DATABASE_URL` | Async Postgres (managed-Postgres URLs like Neon's `sslmode=require` are auto-translated) | local Postgres |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth client (see Cloud Console) | (required in prod) |
| `SECRET_KEY` | JWT signing key (≥32 chars in prod) | dev placeholder |
| `FRONTEND_URL` / `BACKEND_URL` | Exact origins for CORS + OAuth callback (trailing slashes stripped) | localhost |
| `POI_SEARCH_RADIUS_METERS` | Nearby-POI radius | `150` |
| `POI_MAX_CANDIDATES` | Max options shown per question | `12` |
| `H3_RESOLUTION` | H3 hex resolution (7–12) | `9` |
| `USE_H3_DEDUP` | Skip GPS points in H3 cells the user already answered | `true` |
| `CONSENSUS_MIN_ANSWERS` | Fill every question to this many eligible answers before Jaccard routing | `5` |
| `CONSENSUS_MAX_ANSWERS` | Complete the question and stop presenting it | `10` |
| `DENSE_CANDIDATE_THRESHOLD` | Candidate count kept as a difficulty covariate (no longer changes the answer cap) | `7` |
| `CONSENSUS_MIN_ACCOUNT_AGE_MINUTES` | Sybil gate for vote counting (0 = off, `60` in prod) | `0` |
| `RESTRICT_GPS_TO_LA` | Only serve GPS probes inside the LA bbox (`app/regions.py`) | `true` |

## Data Pipeline

Alembic manages the app tables (`users`, `gps_points`, `questions`, `answers`).
The `places` table — the POI catalog the whole game runs on — lives **outside
Alembic** and is populated by the seed script:

```bash
cd backend && source .venv/bin/activate
python scripts/seed_production_data.py
python scripts/seed_production_data.py --gps-count 50
```

The script queries the Overture Maps S3 parquet release directly via DuckDB
(1–3 minutes, needs network), upserts POIs into `places`, and generates
realistic GPS "visit" points with timestamps and H3 cells. The Overture
release is pinned in `backend/scripts/overture_common.py`.

Other scripts:
- `scripts/load_overture_places.py` — reload POIs only (no GPS points)
- `scripts/backfill_h3.py` — fill `h3_cell` on GPS rows that predate H3

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check with DB verification |
| POST | `/auth/register` | No | Create a local account (username/email/password) |
| POST | `/auth/login` | No | Local login (username or email + password) |
| GET | `/auth/google/login` | No | Start Google OAuth flow |
| GET | `/auth/google/callback` | No | OAuth callback (internal) |
| GET | `/auth/me` | Yes | Current user profile |
| POST | `/auth/logout` | No | Clear HttpOnly session cookie |
| GET | `/pois/nearby` | Admin | Query nearby POIs by lat/lon (includes distances) |
| GET | `/game/next-question` | Yes | Get next question for user (includes `prior_answers`) |
| POST | `/game/answer` | Yes | Submit POI selection |
| GET | `/leaderboard` | Yes | Ranked player list (players with ≥1 answer) |
| POST | `/admin/gps-points/bulk` | Admin | Import GPS points (JSON) |
| POST | `/admin/gps-points/upload-csv` | Admin | Import GPS points (CSV) |
| GET | `/admin/export/labels` | Admin | Raw annotations, one row per answer (CSV/JSON, no PII) |
| GET | `/admin/export/consensus` | Admin | Consensus dataset, one row per question with label + confidence + vote distribution (CSV/JSON) |
| GET | `/admin/poi-quality` | Admin | POI candidate density report |

## Security Notes

- **Sessions**: after login (password, register, or Google) the JWT lives in an **HttpOnly** cookie (`access_token`). Response bodies never contain a token.
- **Google OAuth**: uses a random `state` + short-lived HttpOnly cookie to mitigate login CSRF. Google callback refuses to auto-link a Google identity onto an existing password account (avoids takeover) and requires `verified_email`.
- **Distances**: candidate POIs sent to players deliberately omit `distance_meters`; only the server sees the true distance (used as an ML covariate, never scored).
- **Consensus lock**: questions become immutable after they reach `consensus_reached` or `no_consensus`, so exports are reproducible.
- **CORS**: `FRONTEND_URL` must exactly match the browser origin (scheme + host + port). Trailing slashes are stripped so the exact-match check can't be broken by accident.
- **Rate limiting**: register/login are IP rate-limited (`app/rate_limit.py`).
- **Cookies in prod**: `SameSite=None; Secure` — requires HTTPS on both frontend and backend, which the Vercel + Render setup provides.

## Consensus & Scoring

Implemented in `backend/app/services/scoring_service.py`. Each answer is a
set of places. Agreement is the mean pairwise Jaccard similarity of those
sets. Jaccard does not name a single winning place.

**Agreement lifecycle (per question):**

1. Every question collects at least **5 eligible answers** (one per user, enforced by a DB unique constraint).
2. Pairwise Jaccard is `|A∩B| / |A∪B|`. The question score is the mean over all `n(n−1)/2` pairs.
3. While any open question has fewer than 5 answers, those are served first. After that, more answers go to the **lowest** average Jaccard among questions with 5–9 answers.
4. At **10** eligible answers the question **locks** as `no_consensus` with a null place id and the mean Jaccard stored as `consensus_confidence`. Locked rows are immutable.

The nearby-place list is frozen on the question at creation
(`questions.candidates`). Each player is shown at most eight of those places;
that ordered slice is stored on the answer as `displayed_poi_ids`. Both the
frozen set and the displayed slice are included in the admin exports.

**Scoring:**

- **5 points** per answer, immediately (participation)
- No consensus bonus: Jaccard measures set overlap and does not elect a place
- No distance bonus: proximity is recorded as an ML covariate (`answers.selected_distance_meters`) but never scored. Scores never go down.

**Abuse protection:** `CONSENSUS_MIN_ACCOUNT_AGE_MINUTES` can exclude
brand-new accounts from vote counting (they still earn participation
points). Set to `60` in the live Render config.

## License

MIT — see [LICENSE](LICENSE).
