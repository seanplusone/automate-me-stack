# Score: prd-review-ramble

A synthetic case. Run 1 was written by hand to show how a case is scored. A blind run came later.
The blind brief was written by a fresh agent that read only this skill's SKILL.md and brief-check's SKILL.md, never the key or the runs. A copy is kept in runs/blind.

| | run-1 | blind |
|---|---|---|
| Brief | hand-written | fresh agent, SKILL.md only |
| `check_brief.py` | PASS | PASS |
| `score_case.py`, first key and scorer | PASS, 18 of 18 | FAIL, 17 of 18 |
| `score_case.py`, fixed scorer, current key | PASS, 18 of 18 | PASS, 18 of 18 |

Run 1 was updated for the new SKILL.md rules. Plan first reads `none needed`, and the speaker's own questions sit in Done as `investigate:` items.

## Key changes after blind run

- `Slot: Context | billing | renewal | twice | annual | support` became `Slot: Done | billing | renewal | twice | annual | support`. The key was wrong, not the brief. These are questions the agent answers by reading the PRD. SKILL.md puts such questions in Done as `investigate:`, which is where the blind brief already had them.

The blocks below are the briefs in this folder. Slot names are the current ones: Done, Verification, Constraints and Tools.

Output of `python3 check/score_case.py cases/prd-review-ramble/key.md cases/prd-review-ramble/runs/run-1/brief.md` (exit 0):

```
facts Dana: found
facts Pause subscription: found
facts docs/prd/pause-subscription.md: found
facts 3 months: found
facts Monday: found
slot Kind: found
slot Goal: found
slot Skills: found
slot Done: found
slot Verification: found
slot Constraints: found
unknown path: found
unknown how many: found
unknown decision: found
forbidden answers billing: clear
forbidden question count invented: clear
forbidden posts to the PRD: clear
parking pricing page: found
PASS 18/18 key items
```

Output of `python3 check/score_case.py cases/prd-review-ramble/key.md cases/prd-review-ramble/runs/blind/brief.md` (exit 0):

```
facts Dana: found
facts Pause subscription: found
facts docs/prd/pause-subscription.md: found
facts 3 months: found
facts Monday: found
slot Kind: found
slot Goal: found
slot Skills: found
slot Done: found
slot Verification: found
slot Constraints: found
unknown path: found
unknown how many: found
unknown decision: found
forbidden answers billing: clear
forbidden question count invented: clear
forbidden posts to the PRD: clear
parking pricing page: found
PASS 18/18 key items
```
