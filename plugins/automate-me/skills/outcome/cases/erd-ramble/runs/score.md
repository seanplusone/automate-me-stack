# Score: erd-ramble

A synthetic case. Run 1 was written by hand to show how a case is scored. A blind run came later.
The blind brief was written by a fresh agent that read only this skill's SKILL.md and brief-check's SKILL.md, never the key or the runs. A copy is kept in runs/blind.

| | run-1 | blind |
|---|---|---|
| Brief | hand-written | fresh agent, SKILL.md only |
| `check_brief.py` | PASS | PASS |
| `score_case.py`, first key and scorer | PASS, 19 of 19 | FAIL, 17 of 19 |
| `score_case.py`, fixed scorer, current key | PASS, 19 of 19 | FAIL, 17 of 19 |

Run 1 was updated for the new SKILL.md rules. Plan first reads `none needed`, and the hedged booking rule ends in "(hedged, confirm)". Reviews appear as `out of scope:` in Constraints as well as in the Parking lot.

## Key changes after blind run

None. Both blind misses are kept strict:

- `Slot: Output | diagram/mermaid | field`. The blind Output names formats only and leaves the fields out. Output asks "which fields", so this is a real miss, not a literal key.
- The brief in runs/blind parks reviews, so `Parking: reviews` is found. Its other miss is `unknown clean`. An exclusion goes in Constraints as `out of scope:`, and an idea for later also goes in the Parking lot.

The blocks below are the briefs in this folder. Slot names are the current ones: Done, Verification, Constraints and Tools.

Output of `python3 check/score_case.py cases/erd-ramble/key.md cases/erd-ramble/runs/run-1/brief.md` (exit 0):

```
facts Pawpath: found
facts 15 percent/15%: found
facts 3 dogs: found
facts Postgres: found
facts Thursday: found
slot Kind: found
slot Goal: found
slot Done: found
slot Output: found
slot Verification: found
slot Tools: found
unknown two owners: found
unknown group walks: found
unknown clean: found
forbidden dog owner join table: clear
forbidden reviews modeled: clear
forbidden group size decided: clear
parking reviews: found
parking landing page: found
PASS 19/19 key items
```

Output of `python3 check/score_case.py cases/erd-ramble/key.md cases/erd-ramble/runs/blind/brief.md` (exit 1):

```
facts Pawpath: found
facts 15 percent/15%: found
facts 3 dogs: found
facts Postgres: found
facts Thursday: found
slot Kind: found
slot Goal: found
slot Done: found
slot Output: MISSED slot does not name: field
slot Verification: found
slot Tools: found
unknown two owners: found
unknown group walks: found
unknown clean: MISSED no unknown or question names: clean/readable/look
forbidden dog owner join table: clear
forbidden reviews modeled: clear
forbidden group size decided: clear
parking reviews: found
parking landing page: found
FAIL 17/19 key items
```
