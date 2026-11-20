# Score: lunch-poll

A synthetic case. Run 1 was written by a fresh model that read `SKILL.md` and `input.md`, including the later replies. It did not see this key. Turn 2 set output to the winner's name in the same chat. Turn 3 set verify. All five slots were then Decided, so the stop is `done` on turn 3. The close rule and the tie stayed open.

| | run-1 |
|---|---|
| Decisions | fresh model, turn 3 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 10 of 10 |

Output of `python3 check/score_case.py cases/lunch-poll/key.md cases/lunch-poll/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided output: found
decided verify: found
decided constraints: found
decided size: found
open close: found
open tie: found
parked diet: found
parked snacks: found
PASS 10/10 key items
```
