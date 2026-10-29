# Project rules

1. Change only what was asked.
2. Keep the search radius at 150 meters unless the owner says otherwise.
3. Do not show the exact distance to the player before they submit.
4. Do not add a paid maps product for street or mall names.
5. Tests must pass before a push to `main`.
6. Do not commit `.env`, the Word lock file, Word onboarding drafts, or secrets.
7. The working handbook and rules live in `docs/AGENTS.md` and `docs/RULES.md` (with matching copies at the repository root so coding tools that only load the root still find them). Keep those pairs in sync. `ISSUES.md` is a private open-problems list on this machine — never commit it and never push it.
8. Do not mention AI, or the name of any AI tool, in a GitHub commit, a pull request, a release note, or anywhere in the code. The author and committer stay the owner's name and email only.
9. Live agreement is average pairwise Jaccard of each player's selected set, with a floor of 5 answers and a stop at 10. Do not silently replace it with first-pick majority, split votes, or a stop at 5 or 30.
10. Do not add a training job, a new data store, or a claimed model score. Clean and split labels only when the owner asks, and only after the statistician agrees the formula matches `docs/AGENTS.md`.
11. When a problem is seen but not fixed in this step, the engineering manager adds it to the local `ISSUES.md`. Do not duplicate an issue that is already listed. That file is never committed or pushed.
12. Every change, including a one-line fix, gets one detailed entry at the top of `docs/DEVLOG.md` before the work is finished. Follow the template in that file: why we chose this, what changed, what was affected, what we did not change, and deploy/verification when something shipped. One git commit = one heading. Skip it only when the owner says not to record the change.
13. For every implementation request, launch the real reviewer agents listed in `docs/AGENTS.md` (product, engineering, QA, data/ML, research, scrum; plus a statistician for formula changes). Do not role-play them.
