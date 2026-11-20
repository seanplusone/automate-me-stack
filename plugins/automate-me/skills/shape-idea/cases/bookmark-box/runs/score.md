# Score: bookmark-box

A synthetic case. Run 1 was written by a fresh model that read only `SKILL.md` and `input.md`. The key was written from `input.md`. Output stays open, and turn 2 adds one more question. The stop is `open-cap` on turn 2.

| | run-1 |
|---|---|
| Decisions | fresh model, turn 2 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 7 of 7 |

Output of `python3 check/score_case.py cases/bookmark-box/key.md cases/bookmark-box/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided verify: found
decided constraints: found
open output: found
open share: found
parked native: found
PASS 7/7 key items
```
