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
  rejection of POIs outside the frozen candidate set, stored displayed
  slice, rejection of a pick that was not shown
- Consensus: pairwise Jaccard (owner example 2/3), n<2 undefined,
  fill-to-5 then lowest Jaccard, lock at 10 with no named place or bonus,
  Sybil-gated young accounts, locked-row immutability
- Leaderboard: auth required, hidden zero-answer users, ranked entries
- Admin: non-admin rejection, bulk GPS import, label and consensus
  exports including selected sets, displayed ids, and frozen candidates

Happy-path submission is testable in SQLite because answers validate against
the candidate set frozen on the question — no `places` table needed.

### Frontend
```bash
cd frontend
npm ci
npx playwright install chromium
npm run lint      # ESLint
npm run build     # TypeScript + production build
npm run test:e2e  # Desktop and mobile browser checks
```

The Playwright suite verifies that the first-time tutorial highlights each
game control, stays inside desktop and mobile viewports, and remains dismissed
after completion.

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
- [ ] Unanimous sets stay open through 9 answers; the 10th locks as
      `no_consensus` with a null place id and no bonus
- [ ] Mean pairwise Jaccard for {A,B}/{A,B}/{A} is 2/3
- [ ] Questions with fewer than 5 answers are served before 5–9
- [ ] Once every open question has at least 5, the lowest Jaccard is served
- [ ] Submitting to a locked question returns 409
- [ ] Locked rows never change; scores never decrease
- [ ] `/admin/export/consensus` includes status, Jaccard confidence, vote
      distribution, and candidate density for every question
