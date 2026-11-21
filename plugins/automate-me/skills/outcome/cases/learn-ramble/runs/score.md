# Score: learn-ramble

A synthetic case. Run 1 was written by hand to show how a case is scored. A blind run came later.
The blind brief was written by a fresh agent that read only this skill's SKILL.md and brief-check's SKILL.md, never the key or the runs. A copy is kept in runs/blind.

| | run-1 | blind |
|---|---|---|
| Brief | hand-written | fresh agent, SKILL.md only |
| `check_brief.py` | PASS | PASS |
| `score_case.py`, first key and scorer | PASS, 18 of 18 | FAIL, 16 of 18 |
| `score_case.py`, fixed scorer, current key | PASS, 18 of 18 | FAIL, 17 of 18 |

Run 1 was updated for the new SKILL.md rules: Plan first reads `none needed`.

## Key changes after blind run

- `Slot: Must-haves | composite/multicolumn/two-column | customer_id | created_at` became `Slot: Done | customer_id | created_at`. The key put the answer in the brief. Which index fits is what the explanation finds out. A brief that names it before the run is guessing.
- `Unknown: version | version` became `Unknown: version | postgres version/version of postgres/which version`. Tightened. The bare word matched "the standup version" in the blind brief, a word that means something else there. The blind brief never asks the Postgres version, so this is now a miss.
- Kept strict: `unknown data size`. The blind brief asks whether the example uses made-up or real data, but never how big the table is. Data size is now in SKILL.md's "Check even if unsaid" table for learn.

Those slot names were renamed with the brief. Must-haves is Done, Verify is Verification, and If stuck is Constraints. The brief in runs/blind asks the Postgres version and the row count. Its remaining miss is the word cite in Verification, so the score is 17 of 18.

The blocks below are the briefs in this folder. Slot names are the current ones: Done, Verification, Constraints and Tools.

Output of `python3 check/score_case.py cases/learn-ramble/key.md cases/learn-ramble/runs/run-1/brief.md` (exit 0):

```
facts 4 seconds: found
facts customer_id: found
facts created_at: found
facts Postgres: found
facts standup: found
slot Kind: found
slot Goal: found
slot Output: found
slot Verification: found
slot Done: found
slot Constraints: found
unknown version: found
unknown data size: found
unknown where to run: found
forbidden version invented: clear
forbidden row count invented: clear
forbidden index created on a real database: clear
parking other database: found
PASS 18/18 key items
```

Output of `python3 check/score_case.py cases/learn-ramble/key.md cases/learn-ramble/runs/blind/brief.md` (exit 1):

```
facts 4 seconds: found
facts customer_id: found
facts created_at: found
facts Postgres: found
facts standup: found
slot Kind: found
slot Goal: found
slot Output: found
slot Verification: MISSED slot does not name: cite
slot Done: found
slot Constraints: found
unknown version: found
unknown data size: found
unknown where to run: found
forbidden version invented: clear
forbidden row count invented: clear
forbidden index created on a real database: clear
parking other database: found
FAIL 17/18 key items
```
