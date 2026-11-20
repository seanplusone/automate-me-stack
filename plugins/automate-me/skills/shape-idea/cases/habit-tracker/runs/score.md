# Score: habit-tracker

A synthetic case. Run 1 was written by a fresh model that read `SKILL.md` and `input.md`, then two replies. It did not see this key. Output and verify were still open after the ramble, so the run continued. Turn 2 set output to the current streak on the phone. Turn 3 set verify. All five slots were then Decided, so the stop is `done` on turn 3. Reminders, the name, and the day reset stayed open.

| | run-1 |
|---|---|
| Decisions | fresh model, turn 3 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 10 of 10 |

Output of `python3 check/score_case.py cases/habit-tracker/key.md cases/habit-tracker/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided output: found
decided verify: found
decided constraints: found
open reminders: found
open name: found
open reset: found
parked friends: found
parked morning: found
PASS 10/10 key items
```
