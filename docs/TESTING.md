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
- Auth: unauthenticated access, authenticated profile, Google redirect, logout
- Game: unauthenticated access, no questions available, invalid question submission
- Leaderboard: auth required, hidden zero-answer users, ranked entries
- Admin: non-admin rejection, bulk GPS import, label export
- Scoring: distance-bonus tiers, score-range invariants (unit tests, no DB)

Note: happy-path answer-submission tests need Postgres with a seeded `places`
table — the SQLite fixture has no `places`, so those flows are manual for now.

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

### Scoring
- [ ] Any answer awards base 5 points + distance bonus 1–5 (closer = more)
- [ ] When a second player picks the same POI, both gain the +10 consensus bonus
- [ ] Scores update retroactively when consensus shifts (totals can decrease)
- [ ] User total score reflects sum of all awarded points
