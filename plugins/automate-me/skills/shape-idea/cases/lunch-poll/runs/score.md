# Score: lunch-poll

A synthetic case. Run 1 follows `SKILL.md` on `input.md`. The opening message already has a goal, a done line, and other firm choices, so the stop is `done` on turn 1. The close rule and the tie stay open. One pushback is spoken and not written down: a tie has no single winner, and the done line says the winner is posted back.

| | run-1 |
|---|---|
| Decisions | following the skill, turn 1 |
| `check_decisions.py` | PASS |
| `score_case.py` | PASS, 8 of 8 |

Output of `python3 check/score_case.py cases/lunch-poll/key.md cases/lunch-poll/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided size: found
decided pay: found
open close: found
open tie: found
parked diet: found
parked snacks: found
PASS 8/8 key items
```
