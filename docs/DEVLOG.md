# POI Game — Development Log

This file is the history a new person reads. Git history still holds older
work that was never written here. Do not backfill those entries unless the
owner asks.

## How to write an entry

Every commit, including a one-line fix, gets **one new entry at the top of
this file** before the work is finished. Skip that only when the owner says
not to record the change. One git commit = one dated heading. If several
behaviors shipped together, keep them as subsections under that one commit;
do not invent extra dated headings that look like separate days of work.

Write in plain words. Name files only as lookup keys, not as a dumped diff.
Do not name coding tools. Do not invent latency, partitioning, queues, a
trained model, or an accuracy number. Do not describe first-pick majority,
split votes, or a stop at 30 as live. Live agreement is average pairwise
Jaccard of each player's selected set, fill to 5, extra sampling on low
Jaccard, hard stop at 10. Jaccard does not name a winning place.

Required sections for every later entry:

- **Why we chose this** — the owner request or research need, and why this
  option instead of the alternatives we considered.
- **What changed** — each behavior that moved, with the files that hold it.
- **What was affected** — players, researchers/exports, database, APIs,
  tests, and deploy, including knock-on effects.
- **What we did not change** — so later readers do not assume extra work.
- **Deploy / verification** — only when something shipped or was checked.

---

## 2026-10-29 — Celebrate campaign completion and record notification opt-ins

**Why we chose this.** Players who reach the end of the available questions
need a clear finish instead of returning to a generic empty state. The owner
asked for a congratulations message, confetti, and an email field for hearing
about the next campaign. We use a distinct server response for completion so
an ordinary loading error or a temporarily empty campaign cannot trigger the
celebration. Notification consent is stored separately from answers so it is
not mistaken for research annotation data, and only the signed-in account
email can be submitted.

**What changed.**

- `backend/app/routers/game_router.py` returns HTTP 410 when a returning
  player has completed every question currently available. First-time players
  with no available question and timer skips that find no replacement retain
  the existing HTTP 404 behavior.
- `frontend/src/pages/Play.tsx`, `frontend/src/components/PlayMapHud.tsx`, and
  `frontend/src/components/GameCompletion.tsx` show completion only for that
  410 response, wait for the account score to refresh after an answer, then
  show a focused congratulations heading, total account score, confetti, and
  the next-campaign notification choice. Confetti is hidden when reduced
  motion is requested.
- `backend/app/routers/campaign_router.py`, `backend/app/models.py`, and
  `backend/app/schemas.py` add authenticated endpoints to read, save, and
  remove a player's notification preference. Saving is repeatable and uses
  only the account email. The stored row includes a consent version and is
  deleted with its user account.
- `backend/alembic/versions/d4e9f6a1b307_add_campaign_subscriptions.py` adds
  the separate `campaign_subscriptions` table with unique account and email
  indexes, timestamps, consent version, and cascading user foreign key.
- `frontend/src/lib/api.ts` supports DELETE requests and empty HTTP 204
  responses. `frontend/src/index.css` provides the responsive completion,
  notification, and reduced-motion presentation.
- `backend/tests/test_campaign_subscriptions.py`, `backend/tests/test_game.py`,
  and `frontend/e2e/game-completion.spec.ts` cover completion versus ordinary
  empty states, final-score refresh, account-email enforcement, repeat saves,
  removal, export isolation, retry behavior, focus, reduced motion, and both
  desktop and mobile layouts.

**What was affected.**

- **Players:** returning players now get a clear end state and can opt in,
  review an existing preference, retry a failed save, or remove the preference.
- **Database / API:** deploy adds one table and three authenticated
  notification endpoints. `GET /game/next-question` gains a documented 410
  completion outcome in addition to its existing success, 401, and 404 paths.
- **Researchers / exports:** notification rows stay outside both label and
  consensus exports. Answer rows and their research fields are unchanged.
- **Deploy:** the new Alembic migration must run before traffic reaches the
  notification endpoints.

**What we did not change.** Question selection, answer storage, scoring,
average pairwise Jaccard, fill-to-5 routing, low-agreement sampling, the stop
at 10, or admin export schemas. This stores notification consent only; it does
not send campaign email, add an email delivery vendor, or create a campaign
management or model-training system.

**Deploy / verification.** Backend: 72 tests passed. Frontend: lint passed,
the TypeScript production build passed, and all 52 browser tests passed across
desktop and mobile Chromium. Alembic reports `d4e9f6a1b307` as the single head,
and the full PostgreSQL upgrade rendered successfully in offline mode. The
migration was not applied to the production database during local testing.

---

## 2026-10-29 — Publish the working handbook in docs and expand the change log

**Why we chose this.** The Jaccard and shown-places work needed a detailed
change-log entry so a later reader can see why we chose set similarity,
fill-to-5 then stop at 10, and storing the eight shown places — and what
each of those choices affected. Short one-line notes were not enough. The
owner also asked to push that log, and to put the agent handbook on GitHub
the same way: another person cloning onto their own laptop should get the
same instructions so their coding agents spin up the product, engineering,
QA, data/ML, research, and scrum reviewers instead of inventing a different
process. Keeping the handbook only as a gitignored root file meant a fresh
clone had `docs/DEVLOG.md` but no agent brief.

Alternatives considered: leave `AGENTS.md` private (blocks collaborators);
put the handbook only under `docs/` (humans find it, but some editors only
auto-load a root `AGENTS.md`); put it only at the root (easy for tools,
easy to miss next to the other docs). We publish the full text in
`docs/AGENTS.md` and `docs/RULES.md`, mirror the same files at the
repository root, and add a small always-apply editor rule that points at
those paths. `ISSUES.md` stays a private open-problems list on each
machine — it can hold unfinished local notes and must not be pushed.

**What changed.**

- `docs/DEVLOG.md` — standing “How to write an entry” template (why / what
  changed / what was affected / what we did not change / deploy). The
  October 28 Jaccard work is rewritten as two commit-level entries
  (`bd7a1d5`, then `e20fbdc`) with subsections for agreement, sampling,
  shown places, exports, and HUD copy. The 10th eligible submit is
  documented as 200 + lock; a further submit is 409.
- `docs/AGENTS.md` and root `AGENTS.md` — committed handbook: required
  reviewer agents, roles, facts that must not be invented, DEVLOG duty,
  private `ISSUES.md`. Same content in both places.
- `docs/RULES.md` and root `RULES.md` — short project rules, including
  detailed DEVLOG entries and launching real reviewer agents.
- `.gitignore` — stop ignoring the handbook; ignore `ISSUES.md`, Word
  drafts under `docs/*.docx`, and Word lock files. Stop tracking
  `ISSUES.md` in git so it does not return on `main`.
- `.cursor/rules/devlog.mdc` and `.cursor/rules/handbook.mdc` — always-apply
  reminders to follow the DEVLOG template and the handbook when someone
  opens the repo in Cursor.
- `README.md` — project tree lists the handbook and rules files; opening
  blurb matches live Jaccard (no named place, no trained model yet); a
  short “Working on this repo” read order points at DEVLOG, TESTING,
  AGENTS, RULES, and DEPLOYMENT.

**What was affected.**

- **Collaborators / other laptops:** a clone now includes the agent
  handbook beside the change log. Coding agents that load root `AGENTS.md`
  or the Cursor rules get the same reviewer spin-up instructions. Humans
  get a read order on the README before diving into agent process.
- **GitHub `main`:** gains the expanded DEVLOG, handbook, rules, and
  editor rules. Loses `ISSUES.md` as a tracked file (local copies remain).
- **Players / scoring / exports / database:** none. Documentation and
  process only.
- **Private notes:** `ISSUES.md` remains local; do not commit secrets or
  tool names there.

**What we did not change.** Gameplay, Jaccard, sampling, `displayed_poi_ids`,
admin export columns, Render/Vercel config, or any training pipeline. DATA-1
and LABEL-1 stay open and unstarted. Word onboarding files stay untracked.

**Deploy / verification.** After push: confirm `docs/AGENTS.md`,
`docs/RULES.md`, and the expanded `docs/DEVLOG.md` are on `origin/main`,
and that `ISSUES.md` is no longer a tracked path. No backend or frontend
rebuild is required for docs-only changes.

---

## 2026-10-28 — Keep admin exports importing on current FastAPI (`bd7a1d5`)

**Why we chose this.** After the Jaccard and shown-places work was on
`main`, GitHub Checks failed because the backend process could not import.
FastAPI 0.162 dropped `Query(..., enum=...)`. Both admin export endpoints
used that flag for `format=csv|json`. Local tests had passed on an older
FastAPI, so the break showed up only in CI. Without a running app there are
no labels to download, so this was a deploy blocker, not a style cleanup.

We kept the same query parameter and the same two values. Changing the URL
shape or adding a new dependency would have been extra scope. `Literal` on
the parameter is the supported replacement and still rejects anything other
than `csv` or `json`.

**What changed.**

- `backend/app/routers/admin_router.py` — `GET /admin/export/labels` and
  `GET /admin/export/consensus` now declare
  `format: Literal["csv", "json"] = Query("csv")`.
- This file — recorded the import fix.

**What was affected.**

- **Deploy / CI:** the backend pytest job can import the app again. GitHub
  Checks on this commit passed (backend tests plus frontend typecheck,
  lint, build, and browser suite).
- **Admin downloads:** same URLs, default still CSV, JSON still available.
  Column meaning did not change.
- **Players:** none. These routes are admin-only.

**What we did not change.** Export columns, Jaccard, `displayed_poi_ids`,
auth, or FastAPI’s version pin beyond using the API the installed version
already required.

**Deploy / verification.** Production Render `/health` stayed
`{"status":"healthy","database":"connected"}`. Vercel homepage stayed 200.
OpenAPI `/docs` is disabled in production, so the parameter change was
confirmed from code and from CI, not from a live Swagger page.

---

## 2026-10-28 — Store shown places and complete questions at ten answers (`e20fbdc`)

This commit is the live labeling rule: each answer is a set of places,
agreement is mean pairwise Jaccard, every question fills to five eligible
answers then extra people go to the lowest Jaccard until ten, and each
answer stores the ordered places that player actually saw. Nineteen files
moved together; the subsections below are that one commit, not separate
days.

### Why we chose this overall

Players already pick more than one place, and several nearby places can all
look likely. A first-pick majority would throw away the rest of the set and
pretend there is one winner. The owner specified set similarity instead:

`J(A,B) = |A ∩ B| / |A ∪ B|`, then the mean over all `n(n−1)/2` unordered
pairs. Worked example: two people pick `{McDonald's, Starbucks}` and one
picks `{McDonald's}` → mean Jaccard `2/3`.

Jaccard measures overlap. It does not elect a place. Inventing a winner
here would have been a different labeling rule, and researchers still need
a written place-level rule if training should use one. Until that exists,
completed questions lock as `no_consensus` with an empty `consensus_poi_id`
and the mean Jaccard stored as `consensus_confidence`. There is no
consensus bonus, because there is no place to match; paying one would
reward chasing a score instead of an honest set.

Sampling follows the same research need: every visit should get a usable
crowd, extra annotators should go where people disagree, and collection
must stop. Fill every question to 5 eligible answers first. Then send more
people to the lowest mean Jaccard among questions that already have 5–9.
At 10, complete the visit regardless of Jaccard and stop presenting it.
Eligible means Sybil-gated answers (account-age filter in production), not
raw row count.

The frozen nearby list on a question can hold up to 400 places. The player
sees at most eight. Prior primary picks can also be hidden on later
questions, so two players can see different slices of the same freeze.
Exports cannot reconstruct that screen from `questions.candidates` alone.
Each answer now stores `displayed_poi_ids`.

### Agreement: average pairwise Jaccard

**Why this formula, not the unused alternatives.** First-pick majority
ignores multi-select. Split-vote / growing-lead / stop-at-30 text in older
notes is not the owner’s rule and is not implemented. Pairwise Jaccard
treats each player’s set equally, works for n=2 through large crowds, and
is undefined for n<2 (no pairs), which we store as `consensus_confidence =
NULL` rather than a fake 0 or 1.

**What changed.**

- `backend/app/services/scoring_service.py` — `answer_selection_set` reads
  `selected_poi_ids` and falls back to `{selected_poi_id}` for older rows.
  `mean_pairwise_jaccard` averages Jaccard over `itertools.combinations`.
  `evaluate_consensus` writes `votes_total`, sets `answers_target` to the
  live cap of 10, stores rounded mean Jaccard (four decimals) or `NULL`
  when n<2, and at n≥10 locks `status = no_consensus`,
  `consensus_poi_id = NULL`, `locked_at` now. `BASE_POINTS` stays 5.
  `consensus_bonus` is always 0. Historical status name
  `consensus_reached` remains in `TERMINAL_STATUSES` so old locked rows
  stay terminal.
- `backend/tests/test_scoring.py` — owner 2/3 example, identical sets → 1,
  disjoint sets → 0, n<2 → `None`, lock at 10 with no named place and no
  bonus, Sybil-gated young accounts excluded from the sets, a legacy
  `answers_target = 3` row is raised to 10 on evaluate.

**What was affected.**

- **Players:** still +5 immediately on submit. No later bonus, no score
  drop. The HUD no longer promises “+10 if others confirm your picks.”
- **Question routing:** uses the same eligible sets and the same mean
  Jaccard. A visit with n≥10 is skipped even if Jaccard is 1.0.
- **Database:** `questions.consensus_confidence` now means mean Jaccard, not
  confidence in a winning POI. New completes leave `consensus_poi_id`
  empty. Older locked rows can still hold a named id from the previous
  rule; filter on era (`locked_at`, `answers_target`, empty vs filled place
  id) before treating that column as one scheme.
- **Researchers:** do not read Jaccard as a gold POI. Unanimous overlap can
  still lock with confidence `1.0` and no place id. That empty id is the
  live rule, not a failed election.

### Sampling: fill to five, then lowest Jaccard until ten

**Why fill-to-5 first.** A Jaccard of two people is noisy. The owner’s
floor is five eligible answers on every question. While any open visit is
under 5, those are served first, highest n first, so a stream of new GPS
points (n=0) cannot starve visits that already have 1–4 answers.

**Why then lowest Jaccard among 5–9.** Once every open visit has a usable
sample, extra people should go where overlap is weakest. We ignore Jaccard
until the floor, so a lonely pair with Jaccard 0 does not jump the queue
ahead of visits that still need their fifth answer.

**Why a hard stop at 10.** Jaccard never names a winner, so there is no
“wait until we are sure.” Ten is the completion cap, not a majority
threshold. We store that cap on `questions.answers_target` so exports can
see what rule the row was collected under.

**Why we did not rewrite locked rows.** A blanket `UPDATE answers_target =
10` would relabel historical completes that used the old majority-vote
floor of 3. The migration only updates `WHERE locked_at IS NULL`.

**What changed.**

- `backend/app/config.py` — `consensus_min_answers = 5`,
  `consensus_max_answers = 10`. `dense_candidate_threshold = 7` is kept as
  a difficulty covariate and no longer changes how many answers a question
  collects.
- `.env.example` — documents `CONSENSUS_MIN_ANSWERS` and
  `CONSENSUS_MAX_ANSWERS`. The old min/max names that described majority
  lock are gone.
- `backend/app/models.py` — `Question.answers_target` default and
  `server_default` are 10. Comments on `consensus_confidence` say mean
  Jaccard.
- `backend/alembic/versions/b2c7d4e8f013_set_question_answers_target_to_ten.py`
  — `SET DEFAULT 10`; `UPDATE questions SET answers_target = 10 WHERE
  locked_at IS NULL`. Revises `e7c9a1d3f502`.
- `backend/app/services/question_service.py` — `_selection_rank_key` band
  0 is n<5 (higher n first); band 1 is 5–9 (lowest Jaccard, then higher n);
  a random tie-break remains. `_next_question` skips n ≥
  `max(answers_target, consensus_max_answers)`. New questions store
  `answers_target = 10` in `_set_candidate_metadata`.
- `backend/tests/test_selection.py` — fill-to-5, lowest Jaccard among
  5–9, skip n=10, do not serve `no_consensus`, new questions persist 10.
- `backend/tests/test_game.py` — the 10th eligible submit returns 200 and
  completes the question; a further submit returns 409.

**What was affected.**

- **Players:** they are routed toward unfinished and then disagreeing
  visits. They still see the map, up to eight places, and “N others.” They
  do not see Jaccard, the 5/10 counters, or a winning pin.
- **HUD “N others”:** still raw `COUNT(answers)`, including young accounts
  the Sybil gate ignores for Jaccard. That can disagree with `votes_total`.
- **Database / Neon:** Render start command runs `alembic upgrade head`, so
  production questions pick up default 10. Local Postgres was not running
  when this was written; production schema is the live migrate-on-start
  path.
- **Config:** production already used
  `CONSENSUS_MIN_ACCOUNT_AGE_MINUTES=60`. Local default stays 0 so tests
  and a laptop game count every account.

### Shown places: persist the ordered slice of at most eight

**Why store the screen, not only the freeze.** `questions.candidates` is the
nearby set at creation (capped at 400). Play shows
`displayed_candidates(frozen, excluded)` — frozen order, minus this
player’s prior **primary** `selected_poi_id` values, then the first 8. That
is the choice set the person actually judged. Without it, a later model
cannot tell whether a missing pick was unseen or rejected.

**Why the client sends the list, with a server recompute fallback.** The
Play page already has the exact order on screen. Posting
`displayed_poi_ids` records that render. If an older client omits the
field, the server recomputes the current slice so we still store something
rather than null on new rows. Empty or whitespace-only lists are treated as
omit. Both paths then require every selected id to be in the frozen set
**and** in the displayed list, so a player cannot submit a place that was
not shown.

**Why nullable, no backfill.** We cannot reconstruct historical screens.
Null means missingness, not “saw nothing” and not `[]`. Consensus export
keeps `null` in the per-answer list for those rows.

**What changed.**

- `backend/app/models.py` — `Answer.displayed_poi_ids` nullable JSON/JSONB.
- `backend/alembic/versions/c3d8e5f9a124_add_displayed_poi_ids_to_answers.py`
  — `ADD COLUMN` JSONB, no backfill. Revises `b2c7d4e8f013`.
- `backend/app/schemas.py` — `AnswerRequest.displayed_poi_ids` optional;
  cap at `poi_max_candidates` (8). `selected_poi_ids` already had the same
  cap so a submit cannot name more places than a question shows.
- `backend/app/routers/game_router.py` — validate displayed ⊆ frozen;
  otherwise recompute; then selected ⊆ frozen and ⊆ displayed; persist on
  `Answer`.
- `backend/app/services/question_service.py` —
  `displayed_candidates()` is the shared slice helper used at next-question
  time and on omit-recompute.
- `frontend/src/pages/Play.tsx` — POST
  `displayed_poi_ids: question.candidates.map(c => c.id)` (the list the
  player was given).
- `backend/tests/test_game.py` — store client list; omit recomputes;
  reject displayed outside frozen; reject selected not shown.

**What was affected.**

- **Players:** same map and same multi-select. The extra field is not drawn
  on screen.
- **Submit API:** new optional body field. Invalid displayed ids → 400.
  Pick not among shown places → 400. Existing clients that omit the field
  still work.
- **DATA-1 still open:** we still hide prior primary POIs before taking
  eight. Storing the slice makes that effect measurable; it does not stop
  the hiding.

### Exports: selected sets, shown lists, and the frozen nearby set

**Why both exports.** Labels are one row per answer (the annotation).
Consensus is one row per question (the agreement summary). Researchers
need the full selected set on labels, the shown slice on each answer, and
the frozen nearby set on the question. They do not get a named winning
place from Jaccard.

**Why `vote_distribution` stayed first-pick.** Changing it in the same step
would mix a new counting rule into a Jaccard change. It still groups
`Answer.selected_poi_id` (the stored primary / first of the list). That is
not Jaccard and not a split-vote. The earlier short log line “Consensus
still uses the first pick only until a later formula change” was about
lock behavior; Jaccard replaced that lock. The export column did not
switch.

**What changed.**

- `backend/app/routers/admin_router.py` — `_candidate_snapshot` (id, name,
  category, lat, lon, optional distance). Labels add `displayed_poi_ids`
  (`null` if unset) and frozen `candidates`. Consensus adds frozen
  `candidates` and `displayed_poi_ids` as a chronological list-of-lists
  (null entries for old answers). Docstring states Jaccard does not name a
  place.
- `backend/tests/test_admin.py` — labels include displayed + candidates;
  consensus with no answers has `displayed_poi_ids = []`; two answers keep
  order of shown lists.
- `README.md` — agreement lifecycle, 5/10 sampling, no named place, no
  bonus, shown-slice storage. Admin table still describes the consensus
  file as a dataset with label + confidence + vote distribution; confidence
  is overlap, not confidence in a winning POI.
- `docs/TESTING.md` — Jaccard cases, displayed-slice submit cases, export
  coverage.

**What was affected.**

- **Researchers:** new columns on both files. Join carefully:
  `votes_total` / Jaccard use eligible (age-gated) sets;
  `vote_distribution` counts every answer’s primary pick.
  `displayed_poi_ids` ≠ `candidates`. Null displayed is missing history.
- **CSV:** lists are JSON-encoded strings in CSV cells, same pattern as
  `selected_poi_ids`.
- **Privacy:** still opaque `user_id`, no email in these files. Feedback
  stays in its own table and is not joined in.

### Play HUD: remove the false consensus-bonus line

**Why.** The HUD still awarded +5 and listed the picked names. It also
promised a +10 bonus if other players confirmed the picks. That bonus is
gone, so the sentence was false. We did not put Jaccard or “complete at
10” on the HUD: those are sampling internals, and the owner did not ask to
surface them. We left “N others” in place so players still have a little
social context.

**What changed.** `frontend/src/components/PlayMapHud.tsx` — deleted the
bonus sentence. Score feedback is `+{score_awarded} points` (5).

**What was affected.** Post-submit copy only. Home, About, tutorial, and
leaderboard were not edited. Tutorial “final matches” wording and the home
subtitle about training models are leftover copy, not part of this commit.

### What we did not change in `e20fbdc`

- Search radius stays 150 meters; at most eight places on screen.
- One answer per player per question (unique constraint).
- Answers still save immediately; there is no queue.
- No named winning place, no consensus bonus, no distance bonus.
- No training job, no accuracy number, no new vendor.
- `vote_distribution` still first-pick counts.
- Prior primary POIs are still hidden on later questions (DATA-1).
- Concurrent submit locking (DB-1) is still unserialized.
- `.env.example` / README still list `POI_MAX_CANDIDATES=12` while live
  `config.py` defaults to 8. Play uses the settings value.

### Deploy / verification

Render start command is `alembic upgrade head && uvicorn ...`, so Neon
received both new revisions (`answers_target` default 10, then
`displayed_poi_ids`). Local `alembic upgrade` could not run because
Postgres was not listening on `127.0.0.1:5432`. Backend tests: 66 passed.
Frontend typecheck was part of the later CI run on `bd7a1d5`. Production
health: Render `/health` 200, Vercel homepage 200. First Render curl can
take tens of seconds on a cold free-tier dyno; that is wake time, not a
measured latency improvement.

---

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
