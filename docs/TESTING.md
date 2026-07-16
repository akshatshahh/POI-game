# POI Game — Testing Guide

## Automated Tests

### Backend
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest, pytest-asyncio, aiosqlite
python -m pytest tests/ -v
```

Tests cover:
- Health endpoint (mocked DB)
- Auth: unauthenticated access, authenticated profile, Google redirect,
  logout, Google-callback account-linking rules (mocked token exchange)
- Game: unauthenticated access, no questions available, invalid question,
  full happy-path submission, duplicate answer 409, locked question 409,
  rejection of POIs outside the frozen candidate set
- Consensus: unanimous 3-vote lock, disagreement escalation to 5,
  no-consensus lock, difficulty bonus, locked-label immutability
- Leaderboard: auth required, hidden zero-answer users, ranked entries
- Admin: non-admin rejection, bulk GPS import, label export

Happy-path submission is testable in SQLite because answers validate against
the candidate set frozen on the question — no `places` table needed.

### Frontend
```bash
cd frontend
npx tsc --noEmit  # TypeScript type checking
npm run build     # Build verification
```

## Manual Test Checklist

### Prerequisites
- [ ] PostgreSQL with PostGIS running
- [ ] Database created and migrations applied (`alembic upgrade head`)
- [ ] Google OAuth credentials configured
- [ ] Backend running (`uvicorn app.main:app --reload`)
- [ ] Frontend running (`npm run dev`)

### Auth Flow
- [ ] Visit home page — see "Sign in with Google" button
- [ ] Click sign in — redirected to Google consent screen
- [ ] Complete Google login — redirected back to app with user info displayed
- [ ] Navbar shows user name, avatar, and score
- [ ] Refresh page — still logged in (token persisted)
- [ ] Click Logout — returned to unauthenticated state

### Game Flow
- [ ] Import GPS points via admin API (or directly in DB)
- [ ] Navigate to /play — see map with GPS point and nearby POIs
- [ ] GPS point shown as red marker
- [ ] POI candidates shown as blue markers
- [ ] Click a POI on map — marker turns green, sidebar highlights
- [ ] Click a POI in sidebar — same marker turns green
- [ ] Click "Submit Answer" — score feedback shown (+N points)
- [ ] Click "Next Question" — new question loads
- [ ] After answering all questions — "No more questions" message

### Leaderboard
- [ ] Navigate to /leaderboard — see table of players
- [ ] Top 3 players have medal emojis
- [ ] Scores and answer counts are accurate
- [ ] Table is sorted by score descending

### Admin
- [ ] POST /admin/gps-points/bulk — creates GPS points (requires admin)
- [ ] POST /admin/gps-points/upload-csv — uploads CSV (requires admin)
- [ ] GET /admin/export/labels?format=csv — downloads CSV
- [ ] GET /admin/export/labels?format=json — downloads JSON
- [ ] Non-admin users get 403 on admin endpoints

### Consensus & Scoring
- [ ] Any answer awards 5 participation points immediately (no distance bonus)
- [ ] With 3 matching answers from 3 users, the question locks as
      `consensus_reached` and each matching answer gains +10
- [ ] A 2–1 split at 3 answers escalates the target to 5 instead of deciding
- [ ] A 3–2 split at 5 answers locks as `no_consensus` with no bonus
- [ ] Escalated questions that reach consensus pay +15 (consensus + difficulty)
- [ ] Submitting to a locked question returns 409
- [ ] Locked labels never change; scores never decrease
- [ ] `/admin/export/consensus` includes status, label, confidence, vote
      distribution, and candidate density for every question
