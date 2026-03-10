# POI Game — Development Log

## 2026-03-09 — `chore/init-repo-structure`

**What:** Initialized repository structure for the POI Game full-stack application.

- Created top-level folders: `backend/`, `frontend/`, `infra/`, `docs/`
- Added root `README.md` with architecture overview, tech stack, and getting-started instructions
- Added `.gitignore` covering Python, Node, environment files, IDE artifacts
- Added MIT `LICENSE`
- Created `docs/DEVLOG.md` (this file)
- Chose **React + Vite + TypeScript** for frontend (fast HMR, simple config, production-ready)
- Backend will use **FastAPI** with **SQLAlchemy** + **Alembic** for migrations
- Added `backend/requirements.txt` and `frontend/` placeholder `package.json`

**Decision notes:**
- Frontend: React + Vite chosen over Next.js — we don't need SSR for a game UI, and Vite gives faster dev iteration. TypeScript for type safety.
- Backend: FastAPI with async SQLAlchemy for non-blocking DB access with PostGIS.

## 2026-03-09 — `feat/backend-core-setup`

**What:** Set up minimal FastAPI application with database connectivity.

- Created `app/main.py` with FastAPI instance, CORS middleware, and `GET /health` endpoint
- Created `app/config.py` using `pydantic-settings` for centralized env-based configuration
- Created `app/database.py` with async SQLAlchemy engine, session factory, and `get_db` dependency
- Initialized Alembic for async migrations with `app.models` auto-import
- Created placeholder `app/models.py` for future ORM models

**Technical choices:**
- `pydantic-settings` for config — validates env vars with type safety and defaults
- Async SQLAlchemy (`asyncpg` driver) — non-blocking DB access for FastAPI's async handlers
- Alembic configured with `async_engine_from_config` for async migration support

## 2026-03-09 — `feat/db-schema-core-models`

**What:** Defined core database models for the game entities.

- `User` — Google OAuth profile, cumulative score, admin flag
- `GpsPoint` — lat/lon/timestamp for GPS observations to be labeled
- `Question` — links a GPS point to a labeling session with status tracking
- `Answer` — records a user's POI selection for a question, with score awarded

**Schema decisions:**
- UUIDs as primary keys — avoids sequential ID enumeration, safe for public APIs
- `selected_poi_id` stored as string (references Overture Places table which we don't own/modify)
- `score_awarded` on Answer for audit trail; `User.score` is the running total
- `answers_count` on User for quick stats without COUNT queries
- No separate Leaderboard table — query `users ORDER BY score` is sufficient for v1

## 2026-03-09 — `feat/auth-google-oauth`

**What:** Implemented Google OAuth2 login flow and user profile endpoint.

- `GET /auth/google/login` — redirects to Google consent screen
- `GET /auth/google/callback` — exchanges code, upserts User, sets JWT cookie and redirects to frontend
- `GET /auth/me` — returns current user profile (requires auth)
- `POST /auth/logout` — clears auth cookie
- JWT-based auth with Bearer header and cookie support
- `get_current_user` and `require_admin` FastAPI dependencies for route protection

**Technical choices:**
- JWT (python-jose) over server-side sessions — stateless, simpler to scale, no session store needed
- Token passed both as httpOnly cookie and in redirect URL query param (frontend can store it)
- 30-day token expiry for game context (low-risk, high-convenience)
