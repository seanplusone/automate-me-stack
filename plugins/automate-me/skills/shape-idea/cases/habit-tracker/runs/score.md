# Score: habit-tracker

A synthetic case. Run 1 was written by a fresh model that read only `SKILL.md` and `input.md`. The key was written from `input.md`. The goal line is the want. Drinking water and the streak are their own decided lines. The stop is `done` on turn 3.

| | run-1 |
|---|---|
| Decisions | fresh model, turn 3 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 12 of 12 |

Output of `python3 check/score_case.py cases/habit-tracker/key.md cases/habit-tracker/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided water: found
decided streak: found
decided done: found
decided output: found
decided verify: found
decided constraints: found
open reminders: found
open name: found
open reset: found
parked friends: found
parked morning: found
PASS 12/12 key items
```
