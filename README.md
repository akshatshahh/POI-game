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
| Frontend | React 18 + Vite + TypeScript | `frontend/` |
| Backend | FastAPI (Python 3.12) | `backend/` |
| Database | PostgreSQL 16 + PostGIS 3 | via Docker or external |
| POI Data | Overture Maps "Places" table | pre-imported in Postgres |
| Auth | Google OAuth 2.0 (server-side) | backend handles flow |
| Deployment | Docker Compose | `infra/` |

## Features (v1)

- **Login with Google** — server-side OAuth, persistent user profiles
- **Game Screen** — interactive map showing a GPS point and nearby candidate POIs
- **Answer Submission** — player picks the most likely POI; answer is recorded
- **Scoring** — consensus-based scoring algorithm
- **Leaderboard** — ranked display of top players
- **Admin Tools** — bulk GPS point import, label export for ML pipelines

## Project Structure

```
POI-game-cursor/
├── backend/          # FastAPI application
│   └── app/          # Application package
├── frontend/         # React + Vite + TypeScript
├── infra/            # Docker, Compose, deployment config
├── docs/             # DEVLOG, architecture notes
├── .gitignore
├── README.md
└── LICENSE
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 with PostGIS 3 extension
- Google OAuth 2.0 credentials

### Environment Variables

Create a `.env` file in the project root (see `.env.example` when available):

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/poi_game
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SECRET_KEY=your-session-secret-key
FRONTEND_URL=http://localhost:5173
```

### Running Locally

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**With Docker (once available):**
```bash
cd infra
docker compose up --build
```

## Development Workflow

- All work happens on feature branches
- PRs are opened per task with descriptions, checklists, and test notes
- Progress is tracked in `docs/DEVLOG.md`

## License

MIT — see [LICENSE](LICENSE) for details.
