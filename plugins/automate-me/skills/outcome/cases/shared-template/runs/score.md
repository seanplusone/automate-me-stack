# Score: shared-template

A synthetic case. Run 1 flags the risk. Run 2 is run 1 with the flag removed, the blind check removed, and a guessed count of order cards. Both briefs were written by hand. There is no blind run yet.

| | run-1 | run-2 |
|---|---|---|
| Brief | hand-written, flags the broken kind | same deck, template treated as fine for every card |
| `check_brief.py` | PASS | PASS |
| `score_case.py` | PASS, 12 of 12 | FAIL, 8 of 12 |

Run 2 passes the shape check. It still misses the point of the case.

- **Risk not flagged.** Evals never says the shared template bans the cue that order-the-steps cards need. The key wants `order-the-steps`, `template`, and `ban` in Evals.
- **Check is not blind, and not on the half-sheets.** Verification only says each claim names a card.
- **Count guessed.** The speaker said "a few" order cards. Run 2 writes "4 order-the-steps" and does not ask.

Output of `python3 check/score_case.py cases/shared-template/key.md cases/shared-template/runs/run-1/brief.md` (exit 0):

```
facts 24: found
facts name-the-tool: found
facts order-the-steps: found
facts sand: found
facts stain: found
facts seal: found
facts four labels: found
facts half-sheets: found
slot Evals: found
slot Verification: found
unknown how many order cards: found
forbidden order count invented: clear
PASS 12/12 key items
```

Output of `python3 check/score_case.py cases/shared-template/key.md cases/shared-template/runs/run-2/brief.md` (exit 1):

```
facts 24: found
facts name-the-tool: found
facts order-the-steps: found
facts sand: found
facts stain: found
facts seal: found
facts four labels: found
facts half-sheets: found
slot Evals: MISSED slot does not name: order-the-steps, ban
slot Verification: MISSED slot does not name: blind, half-sheet
unknown how many order cards: MISSED no unknown or question names: how many, order-the-steps
forbidden order count invented: MISSED guessed a fact: '4 order-the-steps'
FAIL 8/12 key items
```
