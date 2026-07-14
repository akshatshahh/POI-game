# POI Game — USC IMSC

A gamified web application for collecting human-labeled training data for **POI (Point of Interest) Attribution**. Players are shown GPS points on a map and asked to identify which nearby POI the person was most likely visiting.

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
| Database | PostgreSQL 16 + PostGIS 3 | via Docker or external |
| POI Data | Overture Maps "Places" table | seeded via `backend/scripts/` (see Data Pipeline) |
| Auth | Google OAuth 2.0 + local username/password | backend handles both flows |
| Maps | Leaflet + CARTO/OSM tiles | frontend |
| Deployment | Railway (prod); Docker Compose for local db/backend | `infra/` |

## Features (v1)

- **Auth** — Google OAuth (server-side) or local register/login; sessions in HttpOnly cookies
- **Game Screen** — interactive Leaflet map showing GPS point and nearby candidate POIs
- **Answer Submission** — player picks the most likely POI; answer is recorded
- **Scoring** — base + distance bonus, plus a retroactive consensus bonus (see Scoring Algorithm)
- **Leaderboard** — ranked display of top players with medals (login required)
- **Admin Tools** — bulk GPS point import (JSON/CSV), label export (CSV/JSON)

## Project Structure

```
POI-game-cursor/
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
│   ├── tests/             # Pytest test suite
│   ├── requirements.txt   # Runtime deps (requirements-dev.txt for tests)
│   └── Dockerfile
├── frontend/              # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/         # Home, Play, Leaderboard, Login, Register
│   │   ├── components/    # Navbar, GameMap, PlayMapHud, ClockPanel, ...
│   │   ├── hooks/         # useAuth
│   │   └── lib/           # API client, types, time helpers
│   └── nginx.conf         # Production SPA routing
├── infra/
│   └── docker-compose.yml # Full-stack local orchestration
├── docs/
│   ├── DEVLOG.md          # Development log with decisions
│   └── TESTING.md         # Test guide and manual checklist
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 with PostGIS 3 extension (or use Docker)
- Google OAuth 2.0 credentials ([setup guide](https://console.cloud.google.com/apis/credentials))

### Environment Variables

Copy `.env.example` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Set to `production` to enforce long `SECRET_KEY`, require Google OAuth, and disable `/docs` | `development` |
| `DATABASE_URL` | Async Postgres connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/poi_game` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | (required) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | (required) |
| `SECRET_KEY` | JWT signing key | `change-me-in-production` |
| `FRONTEND_URL` | Frontend origin (CORS + redirects) | `http://localhost:5173` |
| `BACKEND_URL` | Backend origin (OAuth callback) | `http://localhost:8000` |
| `POI_SEARCH_RADIUS_METERS` | Spatial search radius | `150` |
| `POI_MAX_CANDIDATES` | Max POI candidates per question | `30` |
| `H3_RESOLUTION` | H3 hex grid resolution (7-12) | `9` |
| `USE_H3_DEDUP` | Enable H3-based question de-duplication | `false` |
| `RESTRICT_GPS_TO_LA` | Only serve GPS probes inside the Greater LA bbox ([`app/regions.py`](backend/app/regions.py)) | `true` |

### Running Locally

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head  # run migrations
python scripts/seed_production_data.py  # load POIs + GPS points (see Data Pipeline)
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Running with Docker

```bash
cd infra
cp ../.env.example .env  # edit with your values
docker compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Database: localhost:5432
```

### Data Pipeline (required before the game works)

Alembic only creates the app tables (`users`, `gps_points`, `questions`,
`answers`). The `places` table — the POI catalog the whole game runs on —
lives **outside** the migrations and is created/populated by the seed script:

```bash
cd backend && source .venv/bin/activate
python scripts/seed_production_data.py            # canonical pipeline
python scripts/seed_production_data.py --gps-count 50
```

The script queries the Overture Maps S3 parquet release directly via DuckDB
(1–3 minutes, needs network), upserts POIs into `places`, and generates
realistic GPS "visit" points with timestamps and H3 cells. The Overture
release is pinned in `backend/scripts/overture_common.py`.

Other scripts:
- `scripts/load_overture_places.py` — reload POIs only (no GPS points)
- `scripts/backfill_h3.py` — fill `h3_cell` on GPS rows that predate H3

Without seeding, `/game/next-question` and `/pois/nearby` fail on the
missing `places` table.

### Creating an Admin User

There is no admin UI or endpoint; promote a user directly in SQL:

```sql
UPDATE users SET is_admin = true WHERE email = 'you@example.com';
```

### Running Tests

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt  # pytest, pytest-asyncio, aiosqlite
python -m pytest tests/ -v
```

See `docs/TESTING.md` for the full manual test checklist.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check with DB verification |
| POST | `/auth/register` | No | Create a local account (username/email/password) |
| POST | `/auth/login` | No | Local login (username or email + password) |
| GET | `/auth/google/login` | No | Start Google OAuth flow |
| GET | `/auth/google/callback` | No | OAuth callback (internal) |
| GET | `/auth/me` | Yes | Current user profile |
| POST | `/auth/logout` | No | Clear HttpOnly session cookie (JSON `{"ok":true}`) |
| GET | `/pois/nearby` | Yes | Query nearby POIs by lat/lon |
| GET | `/game/next-question` | Yes | Get next question for user |
| POST | `/game/answer` | Yes | Submit POI selection |
| GET | `/leaderboard` | Yes | Ranked player list (players with ≥1 answer) |
| POST | `/admin/gps-points/bulk` | Admin | Import GPS points (JSON) |
| POST | `/admin/gps-points/upload-csv` | Admin | Import GPS points (CSV) |
| GET | `/admin/export/labels` | Admin | Export labels (CSV/JSON) |
| GET | `/admin/poi-quality` | Admin | POI candidate density report |

## Security notes

- **Sessions**: After login (password, register, or Google), the JWT is stored in an **HttpOnly** cookie (`access_token`). The response body returns only `{ "user": ... }` — no token in JSON or URL query strings.
- **Google OAuth**: Uses a random `state` parameter and a short-lived HttpOnly cookie to mitigate login CSRF. Use **HTTPS** in production so `SameSite=None; Secure` cookies work for cross-origin SPA + API hosts.
- **CORS**: `FRONTEND_URL` must exactly match the browser origin (scheme + host + port).
- **Production**: Set `ENVIRONMENT=production`, `SECRET_KEY` (32+ random bytes), and real Google credentials. Never commit `.env` or OAuth client JSON (see `.gitignore`).
- **Still recommended**: rate limiting (e.g. reverse proxy), WAF, `pip audit` / `npm audit`, structured security logging, and rotating secrets after any leak.

## Scoring Algorithm (v2)

Implemented in `backend/app/services/scoring_service.py`:

- **Base: 5 points** for every valid answer (participation)
- **Distance bonus: 1–5 points** — the closer the selected POI is to the GPS
  point, the higher the bonus (≤50m → 5 … >350m → 1)
- **Consensus bonus: 10 points** — applied **retroactively** to everyone who
  picked the most popular POI, once 2+ players have answered the question
- If consensus shifts to a different POI later, bonuses are re-assigned, so a
  player's total **can go down**

A single player therefore sees 6–10 points immediately; agreement with other
players bumps that to 16–20.

## Development Workflow

- All work happens on feature branches
- PRs are opened per task with descriptions, checklists, and test notes
- Progress is tracked in `docs/DEVLOG.md`

## License

MIT — see [LICENSE](LICENSE) for details.
