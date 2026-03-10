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
