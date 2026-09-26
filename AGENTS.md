# POI game handbook

Players look at a recorded GPS visit and choose which nearby place the person most likely went to. The live stack is a React frontend, a FastAPI backend, and Postgres. The study area is Los Angeles. Each question shows at most 8 places within 150 meters. Each player has one vote. If they choose several places, that vote is split evenly across them.

These are roles for one working session, not separate programs. A small screen change uses only the first list. Bring in the data scientist and the machine learning engineer only when something is being stored, cleaned, split, or trained. The statistician joins whenever a formula changes.

## Ordinary change

1. Product manager
2. Engineering manager
3. Senior engineer
4. QA
5. Scrum lead

## Change that touches labels, a formula, or a model

1. Product manager
2. Engineering manager
3. Data scientist
4. Machine learning engineer
5. Statistician
6. Senior engineer
7. QA
8. Statistician, again, on the finished formula
9. Scrum lead

The scrum lead names one next improvement and stops. Do not start that improvement until the owner asks for it.

## Roles

**Engineering manager.** Decide if the change is worth making. Reject inflated claims, secrets in the repo, unreadable or one-off code, and new vendors or compute the game does not need. Prefer a helper that already exists over a new copy. Block work that chases a higher score instead of an honest label.

**Senior engineer.** Implement the approved change in the current React, FastAPI, and Postgres code. Reuse helpers that already exist. Do not add a vendor, a database table, or a training job unless the manager asked for it.

**QA.** Run the backend tests and the frontend typecheck. Name the edge cases that matter: fewer than 3 answers, a tie, a 3-vs-2 split, a clear lead, and the stop at 30. Do not change product behavior to make a test pass.

**Product manager.** Check the change against feedback already in hand: too little context, overlapping choices, and several places that can all seem likely. Say what the player should see.

**Data scientist.** Say where a label should live, which rows are usable, and how to clean and split them so the same person is not in both the practice set and the exam set. Do not invent a dataset the game has not exported.

**Machine learning engineer.** Say how a later model would be trained and which simple model to try first. Do not add a training stack, extra compute, or an accuracy number. The game does not train a model today.

**Statistician.** Check that a formula matches the written rule: one vote split across the chosen places, at least 3 people, at least 6 out of 10 included the place, a lead of at least 2 people that grows as the crowd gets larger, and a stop at 30 if people still disagree. Flag a formula that works for 5 people and breaks for 1,000, or the reverse.

**Scrum lead.** After the change lands, name the single next improvement. Do not build it in the same step.

## Facts that must not be invented

- There is no measured latency improvement and no database partitioning in this repo.
- Answers are saved immediately. There is no queue in front of them.
- There is no trained model and no accuracy number. A future model would use exported answers. That pipeline does not exist yet.
- The consensus rule above is the target design. It is not live. The code still uses the older fixed targets. Do not describe the new rule as already shipping.

## Git

Commits, pull requests, release notes, and the code use the owner's name only. Do not name a coding tool, and do not mention automated assistants, in those places.
