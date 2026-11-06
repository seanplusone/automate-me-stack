# Score: learn-ramble

A synthetic case. Run 1 was written by hand to show how a case is scored. A blind run came later.
The blind brief was written by a fresh agent that read only this skill's SKILL.md and brief-check's SKILL.md, never the key or the runs. It lives outside the repo, in the session scratch folder, and is not copied here.

| | run-1 | blind |
|---|---|---|
| Brief | hand-written | fresh agent, SKILL.md only |
| `check_brief.py` | PASS | PASS |
| `score_case.py`, first key and scorer | PASS, 18 of 18 | FAIL, 16 of 18 |
| `score_case.py`, fixed scorer, current key | PASS, 18 of 18 | FAIL, 16 of 18 |

Run 1 was updated for the new SKILL.md rules: Plan first reads `none needed`.

## Key changes after blind run

- `Slot: Must-haves | composite/multicolumn/two-column | customer_id | created_at` became `Slot: Must-haves | customer_id | created_at`. The key put the answer in the brief. Which index fits is what the explanation finds out. A brief that names it before the run is guessing.
- `Unknown: version | version` became `Unknown: version | postgres version/version of postgres/which version`. Tightened. The bare word matched "the standup version" in the blind brief, a word that means something else there. The blind brief never asks the Postgres version, so this is now a miss.
- Kept strict: `unknown data size`. The blind brief asks whether the example uses made-up or real data, but never how big the table is. Data size is now in SKILL.md's "Check even if unsaid" table for learn.

The blind score stays 16 of 18, but the misses changed. Before, they were the composite index (a key fault) and data size. Now they are version and data size, both real skill misses.

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
slot Verify: found
slot Must-haves: found
slot If stuck: found
unknown version: found
unknown data size: found
unknown where to run: found
forbidden version invented: clear
forbidden row count invented: clear
forbidden index created on a real database: clear
parking other database: found
PASS 18/18 key items
```

Output of `python3 check/score_case.py cases/learn-ramble/key.md <blind>/learn-ramble/brief.md` (exit 1):

```
facts 4 seconds: found
facts customer_id: found
facts created_at: found
facts Postgres: found
facts standup: found
slot Kind: found
slot Goal: found
slot Output: found
slot Verify: found
slot Must-haves: found
slot If stuck: found
unknown version: MISSED no unknown or question names: postgres version/version of postgres/which version
unknown data size: MISSED no unknown or question names: rows/table size/how big
unknown where to run: found
forbidden version invented: clear
forbidden row count invented: clear
forbidden index created on a real database: clear
parking other database: found
FAIL 16/18 key items
```
