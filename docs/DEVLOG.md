# POI Game — Development Log

## 2026-10-28 — Record the places each player actually saw

Each answer now stores the ordered list of places shown on that question, at most eight. The labels export includes that list and the question's frozen nearby-place set. The consensus export includes the frozen set and every answer's displayed list. Older answers leave the displayed list unset. Players still pick from the same map; the extra field is not shown on screen.

## 2026-10-28 — Store the ten-response completion cap on questions

Every question now records `answers_target = 10` in the database, matching the rule that a visit is complete after ten eligible answers. Open questions are updated to 10; already-locked rows keep the target they were collected under. Routing still fills questions to five first, then sends more people to the lowest Jaccard score, and stops presenting a question at ten.

## 2026-10-28 — Measure agreement with average pairwise Jaccard

Each answer is a set of places. Agreement is the mean Jaccard similarity of every pair of sets. Questions fill to five eligible answers, then more people are sent to the lowest-agreement questions until ten, when the question is complete. Jaccard does not name a winning place, so completed questions store the score and leave the place id empty. Players still get five points immediately; the old first-pick lock and consensus bonus are gone.

## 2026-10-28 — Include every chosen place in the labels export

Players already pick more than one place, and answers already store that list. The labels export now includes `selected_poi_ids` so the full set can be downloaded. A submit is limited to eight places, matching the number shown on a question. Consensus still uses the first pick only until a later formula change.

## 2026-10-07 — Fill rating stars up to the selected value

Feedback now fills all stars up to the chosen rating and outlines the remaining stars. Selecting a lower rating clears the extra filled stars. Native radio controls, keyboard navigation and the single saved rating remain unchanged. Added browser checks for increasing and decreasing ratings and keyboard selection.

## 2026-10-07 — Make feedback available during play

Added Feedback beside Leaderboard for signed-in players. It reuses the existing rating, comments and optional email form without ending the session. Successful submission shows a confirmation; closing the form keeps the player signed in. The Logout entry retains its original submit-or-skip behavior. The game timer pauses for either form mode. No backend or database changes were needed.

Standalone requests can be cancelled without trapping the player in a pending save. Closing restores keyboard focus and ignores late responses; the confirmation clears after five seconds. Added desktop/mobile regression checks for both entry points, retries, reopening, cancellation and timer pause/resume.

## 2026-10-07 — Simplify navigation and feedback controls

Moved About, Play and Leaderboard beside the text-only POI Game brand, with account controls on the right. About reuses the same project information shown on Home. Navigation wraps on small screens, and the game fills the remaining viewport without assuming a fixed header height. Feedback actions use three distinct yellow treatments with dark text and keyboard focus, and rating stars no longer show adjacent numbers. No annotation or storage behavior changed.

## 2026-10-07 — Clarify review responsibilities

Updated the local working handbook to require independent product, engineering, QA, data/research and delivery reviews, with additional statistical review for formula changes. Kept approval boundaries and private notes local. No application behavior changed.

## 2026-10-07 — Make logout feedback shorter and clearer

Centered the feedback dialog, rating choices and buttons. Explained that 1 is least liked and 5 is best. Moved the comments guidance into the text box as a placeholder while retaining its label and accessible description. Added desktop/mobile checks for the scale, hint and dialog position. No storage or consensus rules changed.

## 2026-10-07 — Ask for optional feedback at logout

Added a logout dialog with a five-star rating, optional comments and optional reply email. Players can submit, skip, or keep playing; a failed save retains the form and allows retry or logout. Feedback lives in a separate Postgres table with administrator-only reading and is never joined into research-label exports. Apply the new Alembic migration before deployment.

The question timer pauses while the dialog is open. Verified 45 backend tests, frontend lint/typechecking/build, and desktop/mobile browser checks for saving, retrying, skipping, cancellation, and timer pause. Replaced the empty leftover local feedback schema and applied the new migration locally; no production database was changed.

## 2026-10-07 — Fix Next Question after submitting

Wrapped the Next Question callback so a button click cannot pass its event as an excluded question ID. Previously the browser sent `exclude_question_id=[object Object]`, which the backend correctly rejected with 422. Timer-based skipping still passes the actual question ID.

Verified with 36 backend tests and 18 desktop/mobile browser tests, including a submit-then-next regression check. Frontend typechecking, lint, and the production build passed. Automated checks now also run lint, build, and the browser suite.

## 2026-10-07 — Use the latest home-page update

Removed the uncommitted About and Feedback implementation at the owner's request and pulled the latest home-page project-information change from the remote branch. Preserved earlier local notes and documents; saved the removed work in a temporary backup.

## 2026-10-07 — Reviewed recent gameplay and multi-select changes

Checked the current commits, answer storage, consensus, exports, question selection, and frontend flow. Recorded unresolved multi-select counting, export completeness, candidate filtering, concurrency, and browser-test coverage problems in the local issues list. Backend tests passed (36 tests), and the frontend typecheck passed. Browser tests could not run because the local Playwright executable was unavailable. No gameplay rules were changed.

## 2026-09-25 — Private notes stay local

**What:** `AGENTS.md`, `RULES.md`, and `ISSUES.md` are notes for the owner only. They are not committed and they are not pushed to `main`.

## 2026-09-25 — Issues list and change log

**What:** The handbook now says how later work is written down.

- The engineering manager adds a problem to `ISSUES.md` when it is seen but not fixed in the same step.
- Every change, including a small one, gets a short entry at the top of this file so a new person can see what changed and why.
- Older work that was never written here stays in git history.

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

## 2026-03-09 — `chore/tests-and-polish-v1`

**What:** Added test suite, manual test checklist, and documentation polish for v1.

- 15 automated backend tests using pytest + pytest-asyncio + SQLite in-memory
- Tests cover: health, auth (4 tests), game (4 tests), leaderboard (2 tests), admin (4 tests)
- `docs/TESTING.md` with full manual test checklist
- Updated `README.md` with comprehensive API reference, scoring algorithm docs, project structure
- All test dependencies added to `requirements.txt`

**v1 status:** All 12 tasks complete. App is demoable with:
- Google login
- Map-based game screen with POI selection
- Consensus-based scoring
- Leaderboard
- Admin tools for GPS import and label export
- Docker setup for local orchestration
