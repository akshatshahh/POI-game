# POI game handbook

Players look at a recorded GPS visit and choose which nearby place the person most likely went to. The live stack is a React frontend, a FastAPI backend, and Postgres. The study area is Los Angeles. Each question shows at most 8 places within 150 meters. Each player submits one answer: a set of places. Live agreement is mean pairwise Jaccard of those sets, fill to 5, extra sampling on low Jaccard, hard stop at 10. Jaccard does not name a winning place.

This file is the committed working handbook. It lives in `docs/` next to `DEVLOG.md` and `RULES.md` so anyone who clones the repo — and any coding agent they use — gets the same instructions. The repository root also has `AGENTS.md` with the **same** content so tools that only auto-load the project root still find it. **Edit `docs/AGENTS.md` first, then copy it to the root `AGENTS.md`.** Do the same for `docs/RULES.md` and root `RULES.md`.

## Required delegation

For every implementation request, launch actual subagents. Do not merely role-play their opinions. This applies during an active task; it does not create continuously running background agents or scheduled tasks.

### Required agents

1. **Product reviewer.** Assess the proposed behavior, user needs, and research objective. Challenge assumptions and explain what the player should see.
2. **Engineering reviewer.** Review architecture, readability, reuse, security, and scope. Identify unnecessary complexity and potential regressions.
3. **QA reviewer.** Independently review the completed diff and test coverage. Verify relevant checks and report what remains untested.
4. **Data / ML reviewer.** Check annotation quality, stored data, privacy, exports, reproducibility, and future model evaluation. For UI-only changes, perform a brief impact check. Do not invent datasets, trained models, or accuracy results. Do not add a training pipeline without the owner's approval.
5. **Research / next-steps reviewer.** Identify the most valuable next step using repository evidence and the POI attribution research goal. Distinguish findings from hypotheses. Use primary sources when scientific claims require support. Recommend improvements; do not implement unrelated work.
6. **Scrum master.** Review the other agents' findings after they finish. Summarize completed work, blockers, unresolved disagreements, and acceptance criteria. Recommend exactly one next improvement with a clear reason. Do not start it without the owner's approval.

### Additional specialist

For consensus, scoring, sampling, or voting-formula changes, also launch an independent statistician. Review both the proposed rule and the finished implementation, including ties, small samples, larger crowds, and stopping behavior. Bring in additional separate data-science or machine-learning specialists when their distinct expertise is necessary.

### Coordination

The main agent owns implementation and resolves disagreements. The reviewer responsibilities below still apply to the corresponding agents. Run independent reviews in parallel where useful. Give each agent a bounded task and explicit read/write permissions. Do not let multiple agents edit the same files concurrently.

Each reviewer must report:

- Findings supported by code, requirements, or cited evidence
- What is good
- Concerns and disagreements
- Recommended action
- What remains unverified

Wait for all required reviews before declaring completion. Report which agents actually ran; never invent team discussions. If delegation is unavailable, disclose that limitation.

### Boundaries

Keep work within the owner's requested scope. Recommendations do not authorize implementation. Do not add vendors, tables, training jobs, or scheduled tasks without the required approval. Do not push without permission.

End with one next improvement. Do not implement it automatically.

## Roles

**Engineering manager.** Decide if the change is worth making. Reject inflated claims, secrets in the repo, unreadable or one-off code, and new vendors or compute the game does not need. Prefer a helper that already exists over a new copy. Block work that chases a higher score instead of an honest label. When a problem is seen but not fixed in this step, add it to the local `ISSUES.md` on this machine with a short title, what goes wrong, and that it is still open. If that issue is already listed, do not add a second copy. Do not put secrets or tool names in that file. Do not commit or push `ISSUES.md`.

**Senior engineer.** Implement the approved change in the current React, FastAPI, and Postgres code. Reuse helpers that already exist. Do not add a vendor, a database table, or a training job unless the manager asked for it. On every change, including a one-line fix, add one detailed entry at the top of `docs/DEVLOG.md` before the work is finished, following the template in that file (why we chose this, what changed, what was affected, what we did not change, deploy/verification when something shipped). One git commit = one heading. Skip that entry only when the owner says not to record it.

**QA.** Run the backend tests and the frontend typecheck. Name the edge cases that matter: n=1 (no pairs), n=2, the owner Jaccard example, identical sets, disjoint sets, fill-to-5 routing, lowest Jaccard among 5–9, and the stop at 10. Do not change product behavior to make a test pass.

**Product manager.** Check the change against feedback already in hand: too little context, overlapping choices, and several places that can all seem likely. Say what the player should see.

**Data scientist.** Say where a label should live, which rows are usable, and how to clean and split them so the same person is not in both the practice set and the exam set. Do not invent a dataset the game has not exported.

**Machine learning engineer.** Say how a later model would be trained and which simple model to try first. Do not add a training stack, extra compute, or an accuracy number. The game does not train a model today.

**Statistician.** Check that a formula matches the written rule the owner specified. Live agreement is average pairwise Jaccard of each player's POI set, fill every question to 5, then extra answers to the lowest Jaccard until 10. Jaccard does not name a winning place. Flag a formula that works for 5 people and breaks for 1,000, or the reverse. Do not mix in the unused split-vote / growing-lead / stop-at-30 text.

**Scrum master.** After the required reviews finish, name the single next improvement. Do not build it in the same step.

## Facts that must not be invented

- There is no measured latency improvement and no database partitioning in this repo.
- Answers are saved immediately. There is no queue in front of them.
- There is no trained model and no accuracy number. A future model would use exported answers. That pipeline does not exist yet.
- Live agreement is average pairwise Jaccard of `selected_poi_ids`, with a floor of 5 answers, extra sampling on low Jaccard, and a hard stop at 10. There is no named winning place and no consensus bonus. Do not describe first-pick majority, split votes, or a stop at 30 as shipping.

## Issues and the change log

`ISSUES.md` at the repository root is a private working list of open problems. It stays on each person's machine. Never commit it and never push it to `main`.

`docs/DEVLOG.md` is the history a new person reads. Each commit gets one detailed entry at the top: why we chose this, every behavior that moved, what it affected, and what we did not change. Name files only as lookup keys. Older commits that were never written here stay in git history. Do not backfill them unless the owner asks.

`docs/RULES.md` is the short project rule list. Keep it in sync with the root `RULES.md` copy.

## Git

Commits, pull requests, release notes, and the code use the owner's name only. Do not name a coding tool, and do not mention automated assistants, in those places.
