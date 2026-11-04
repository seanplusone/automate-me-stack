# Playbook: Spike before the EDD

Use this while the PM is still answering questions. It turns the unknowns in the reviewed PRDs and their test plans into evidence files, so the EDD starts from facts instead of waiting. Output is an evidence dir, two validation files and one spike doc. Status: draft, from one real run. Improve it after each use.

Copy these steps into the todolist word for word. A skipped step stays as `skip: <reason>`.

## Steps

1. **Scope.** List spike candidates only from the PRDs in this run. Sources: each map's unsure (U) points, each "verify" note, each PM question a fact could inform, and each test plan's setup and cases. One line per candidate: the question, and the PRD point or test case it serves. A candidate owned by a later PRD is parked, not run.
2. **Sort by what it needs.** Public sources (vendor docs, public sample services), code reading at a pinned commit, a sandbox the team owns, or production read access. Only the first two run unattended. Write the others as PLANNED, or BLOCKED when someone outside the team holds the key, with an exact METHOD, WHERE and owner. A production read is `RUNNER: person` and read-only.
3. **Run the read-only spikes.** One agent per group, in parallel, each writing evidence files in `templates/evidence.md` format. Code reading uses `git show <sha>:<path>`, never the working tree. Never run the project's app, tests or commands, never sign in, never write to a vendor service.
4. **Check the test plans.** For each test case: does it pass on today's code, what does it need, and can it be run as written? A case that cannot be run as written becomes a correction for the PM, posted as a comment like any other.
5. **Check the files.** Run `check_edd.py evidence <dir>` and fix until it passes.
6. **Validate.** A different model family tries to prove each claim wrong. It reopens every cited source, reruns at least two queries per probe, rereads every file:line, and looks for missed callers and hooks. It writes `VALIDATION-<group>.md` with one row per claim: HOLDS, WEAKER, WRONG or UNCHECKABLE, what it found, and the PRD point. It never edits an evidence file.
7. **Apply the verdicts.** Correct each WEAKER or WRONG claim in its evidence file and add a line saying what changed and why. Rerun step 5.
8. **Write the spike doc.** One doc per run, not one per spike. Load `../shared/writing-rules.md` first. Each spike gets the question, what it settles (PRD point, test case or design choice), how it was run, the answer, and how sure (measured, read in code, read in docs, or not yet run). Planned and blocked spikes list their owner and what unblocks them. The doc lands in the same PR as the EDD, and the EDD cites spikes by id.
9. **Hand off.** The report names what only a person can unblock: sandbox access, production reads, another team's code, and PM corrections from step 4.

## Stop rules

- A candidate with no PRD point or test case behind it: drop it.
- A spike that would write to a vendor service, run the project's code, or read production unattended: write it as PLANNED and stop there.

## After the run

Note what this playbook got wrong in the run's decision log, then fold it back here.
