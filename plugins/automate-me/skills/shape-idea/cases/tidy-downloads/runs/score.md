# Score: tidy-downloads

A synthetic case. Run 1 was written by a fresh model that read only `SKILL.md` and `input.md`. The key was written from `input.md`. Constraints says never delete a file. The 30 day cutoff stays an open question. The partner is parked, and the desktop icons are parked. The stop is `done` on turn 5.

| | run-1 |
|---|---|
| Decisions | fresh model, turn 5 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 8 of 8 |

Output of `python3 check/score_case.py cases/tidy-downloads/key.md cases/tidy-downloads/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided output: found
decided verify: found
decided constraints: found
any cutoff: found
any partner: found
parked icons: found
PASS 8/8 key items
```
