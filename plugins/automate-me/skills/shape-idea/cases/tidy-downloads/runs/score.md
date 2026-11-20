# Score: tidy-downloads

A synthetic case. Run 1 follows `SKILL.md` on `input.md` and stops on turn 1. Goal and the move rule are Decided. The four missing slots are Open, and so is the delete question, because it holds "30 days" and it can remove files. That is 5 open items. The stop is `open-cap`. Watching the folder, zip files, the desktop, and undo were not written. The one pushback is that a partner uses the same laptop, so a move can touch their files. It is not written down.

| | run-1 |
|---|---|
| Decisions | following the skill, turn 1 |
| `check_decisions.py` | PASS |
| `check_writing.py` | PASS |
| `score_case.py` | PASS, 8 of 8 |

Output of `python3 check/score_case.py cases/tidy-downloads/key.md cases/tidy-downloads/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided files: found
open done: found
open output: found
open verify: found
open limits: found
open delete: found
parked icons: found
PASS 8/8 key items
```
