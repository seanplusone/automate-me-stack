# Score: tidy-downloads

A synthetic case. Run 1 was written by a fresh model that read `SKILL.md` and `input.md`, then the replies that settle the four open slots. It did not see this key. Turn 1 parked the cutoff question instead of dropping it. Turns 2 to 5 set done, output, verify, and constraints. The stop is `done` on turn 5. Watch, desktop, zip, and undo stayed open.

| | run-1 |
|---|---|
| Decisions | fresh model, turn 5 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 11 of 11 |

Output of `python3 check/score_case.py cases/tidy-downloads/key.md cases/tidy-downloads/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided done: found
decided output: found
decided verify: found
decided constraints: found
open watch: found
open desktop: found
open zip: found
open undo: found
parked cutoff: found
parked icons: found
PASS 11/11 key items
```
