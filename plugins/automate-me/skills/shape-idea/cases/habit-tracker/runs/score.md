# Score: habit-tracker

A synthetic case. Run 1 follows `SKILL.md` on `input.md` and stops on turn 1. Goal, the water habit, the streak, done, and constraints are Decided. Output and verify were not said, so they are Open slots, with reminders, the app name, and the day reset. That is 5 open items. The stop is `open-cap`.

| | run-1 |
|---|---|
| Decisions | following the skill, turn 1 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 12 of 12 |

Output of `python3 check/score_case.py cases/habit-tracker/key.md cases/habit-tracker/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided water: found
decided streak: found
decided done: found
decided limits: found
open output: found
open verify: found
open reminders: found
open name: found
open reset: found
parked friends: found
parked morning: found
PASS 12/12 key items
```
