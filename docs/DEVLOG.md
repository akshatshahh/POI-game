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

## 2026-03-09 — `feat/frontend-scaffold-and-auth`

**What:** Scaffolded React + Vite + TypeScript frontend with Google auth integration.

- Bootstrapped with `create-vite` (react-ts template)
- Added `react-router-dom` for client-side routing
- Implemented auth flow: Google login button → backend redirect → token capture from URL → stored in localStorage
- Created `useAuth` hook, API client (`lib/api.ts`), type definitions
- Built `Navbar` with auth-aware rendering (login button vs user info)
- Pages: Home (with stats), Play (placeholder), Leaderboard (placeholder)
- Modern dark-themed UI with CSS custom properties, no component library needed for v1

## 2026-03-09 — `feat/api-nearby-pois-for-gps-point`

**What:** Added nearby POI query API using PostGIS spatial functions.

- `GET /pois/nearby?lat=...&lon=...&radius=...&limit=...` returns candidate POIs sorted by distance
- Uses `ST_DWithin` for efficient spatial filtering on the Overture Maps `places` table
- Service layer (`poi_service.py`) handles JSONB parsing for Overture `names` and `categories` fields
- Configurable defaults via `POI_SEARCH_RADIUS_METERS` and `POI_MAX_CANDIDATES` env vars

## 2026-03-09 — `feat/api-next-question-endpoint`

**What:** Implemented next-question selection logic and game endpoint.

- `GET /game/next-question` returns a question with GPS point and candidate POIs
- Selection strategy: prefer GPS points with fewest answers, skip already-answered by user, require minimum 3 candidates
- Creates Question records on demand (lazy creation per GPS point)
- Added schemas for game responses (`NextQuestionResponse`, `AnswerRequest`, `AnswerResponse`, `LeaderboardEntry`)

## 2026-03-09 — `feat/api-submit-answer-and-scoring`

**What:** Added answer submission endpoint with consensus-based scoring.

- `POST /game/answer` validates POI is a candidate, creates Answer, computes score
- Consensus scoring: 10 points if answer matches most popular choice, 2 points otherwise
- Retroactive score updates when consensus shifts (keeps all scores accurate)
- Prevents duplicate answers per user per question
- User score and answers_count updated atomically

**Scoring algorithm (v1):**
- FULL_POINTS (10) if selected POI == consensus POI (most-chosen)
- PARTICIPATION_POINTS (2) otherwise or if < 2 answers exist
- After each new answer, all answers for that question are re-evaluated

## 2026-03-09 — `feat/frontend-game-screen`

**What:** Implemented the main game screen with interactive map and POI selection.

- Interactive Leaflet map showing GPS point (red marker) and candidate POIs (blue/green markers)
- Clickable POI list sidebar with name, category, and distance
- Full game loop: load question → select POI → submit → see score → next question
- Loading, error, and empty states handled
- Responsive layout (sidebar stacks below map on mobile)
- Added Leaflet + react-leaflet dependencies

## 2026-03-09 — `feat/leaderboard`

**What:** Added leaderboard API endpoint and frontend page.

- `GET /leaderboard?limit=50` returns ranked users with score and answers count
- Frontend leaderboard page with styled table, rank badges, and top-3 highlighting
- Only shows users who have submitted at least one answer
- Linked from navbar for both authenticated and unauthenticated users

## 2026-03-09 — `feat/admin-and-export-tools`

**What:** Added admin endpoints for GPS point ingestion and label export.

- `POST /admin/gps-points/bulk` — JSON bulk import of GPS points
- `POST /admin/gps-points/upload-csv` — CSV file upload for GPS points
- `GET /admin/export/labels?format=csv|json` — export all labels for ML pipelines
- All admin endpoints protected by `require_admin` dependency (checks `User.is_admin` flag)
- Added `python-multipart` dependency for file upload support

## 2026-03-09 — `chore/docker-and-local-env`

**What:** Added Docker setup for the full stack.

- `backend/Dockerfile` — Python 3.12 slim image with uvicorn
- `frontend/Dockerfile` — multi-stage build (Node builder → nginx for static files)
- `frontend/nginx.conf` — SPA-friendly nginx config with caching
- `infra/docker-compose.yml` — orchestrates db (PostGIS), backend, frontend
- `.env.example` — template for all required environment variables
- `.dockerignore` files for backend and frontend
