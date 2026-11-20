# Score: lunch-poll

A synthetic case. Run 1 was written by a fresh model that read only `SKILL.md` and `input.md`. The key was written from `input.md`. The 12 people are a firm limit on the constraints line. The stop is `done` on turn 3.

| | run-1 |
|---|---|
| Decisions | fresh model, turn 3 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 9 of 9 |

Output of `python3 check/score_case.py cases/lunch-poll/key.md cases/lunch-poll/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided output: found
decided verify: found
decided constraints: found
open close: found
open tie: found
parked diet: found
parked snacks: found
PASS 9/9 key items
```
