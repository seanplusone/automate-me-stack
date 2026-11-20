# Score: tidy-downloads

A synthetic case. Run 1 follows `SKILL.md` on `input.md`. There is a goal and one firm choice, and no done line. Six gaps are in the ramble. The five that change the shape most are kept, so the stop is `open-cap` on turn 1. The dropped gap is whether 30 days is fixed or passed each time, because "30 days" already sits in the delete question. The one pushback is that a partner uses the same laptop, so a move can touch their files. It is not written down, because it was not decided.

| | run-1 |
|---|---|
| Decisions | following the skill, turn 1 |
| `check_decisions.py` | PASS |
| `score_case.py` | PASS, 8 of 8 |

Output of `python3 check/score_case.py cases/tidy-downloads/key.md cases/tidy-downloads/runs/run-1/decisions.md` (exit 0):

```
decided goal: found
decided files: found
open watch: found
open delete: found
open zip: found
open scope: found
open undo: found
parked icons: found
PASS 8/8 key items
```
