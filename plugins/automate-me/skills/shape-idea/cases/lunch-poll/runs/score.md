# Score: lunch-poll

A synthetic case. Run 1 follows `SKILL.md`. Turn 1 records goal, done, and constraints, and leaves output, verify, the close rule, and the tie open. Turn 2 sets output to the winner's name in the same chat. Turn 3 sets verify to starting a poll with three choices and seeing the winner come back. All five slots are then Decided, so the stop is `done` on turn 3. The close rule and the tie stay open. One pushback is spoken and not written down. A tie has no single winner, and the done line says the winner is posted back.

| | run-1 |
|---|---|
| Decisions | following the skill, turn 3 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 9 of 9 |

Output of `python3 check/score_case.py cases/lunch-poll/key.md cases/lunch-poll/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided limits: found
decided output: found
decided verify: found
open close: found
open tie: found
parked diet: found
parked snacks: found
PASS 9/9 key items
```
