# Score: habit-tracker

A synthetic case. Run 1 follows `SKILL.md` on `input.md`. The opening message already has a goal, a done line, and other firm choices, so the stop is `done` on turn 1. The three open questions stay in the file and are not asked. Nothing clashes, so there is no pushback.

| | run-1 |
|---|---|
| Decisions | following the skill, turn 1 |
| `check_decisions.py` | PASS |
| `score_case.py` | PASS, 10 of 10 |

Output of `python3 check/score_case.py cases/habit-tracker/key.md cases/habit-tracker/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided water: found
decided streak: found
decided done: found
decided accounts: found
open reminders: found
open name: found
open reset: found
parked friends: found
parked morning: found
PASS 10/10 key items
```
