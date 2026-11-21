# Score: shared-template

A synthetic case. Run 1 flags that the shared template does not fit order-the-steps, and it checks the cards blind. Run 2 drops that flag and guesses a count. Run 3 keeps the words a loose key would accept, and says the opposite: no ban, the template works for order cards, not a blind check, and a full-page PDF. It also invents "four order-the-steps" and asks "4 or 5?". All three briefs were written by hand.

| | run-1 | run-2 | run-3 |
|---|---|---|---|
| Brief | flags the broken kind | template treated as fine, count guessed | denies the ban and skips the blind check |
| `check_brief.py` | PASS | PASS | PASS |
| `score_case.py` | PASS, 12 of 12 | FAIL, 8 of 12 | FAIL, 9 of 12 |

Run 2 and run 3 pass the shape check. They miss the point of the case.

- **Run 2 never says the template does not fit.** Evals has no pass or fail phrase about order-the-steps. Verification is not a blind check on the half-sheets. It writes "4 order-the-steps" instead of asking how many.
- **Run 3 says the opposite.** "No ban is a problem" and "works for order-the-steps" are not "does not fit". "Not blind" and "full-page" are not a blind check on a half-sheet. "four order-the-steps" and the question "4 or 5?" invent a count.

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
forbidden invented count or a denied check: clear
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
slot Evals: MISSED slot does not name: cannot show order-the-steps/breaks on order-the-steps/does not fit order-the-steps
slot Verification: MISSED slot does not name: cards blind, half-sheet
unknown how many order cards: MISSED no unknown or question names: how many, order-the-steps
forbidden invented count or a denied check: MISSED guessed a fact: '4 order-the-steps'
FAIL 8/12 key items
```

Output of `python3 check/score_case.py cases/shared-template/key.md cases/shared-template/runs/run-3/brief.md` (exit 1):

```
facts 24: found
facts name-the-tool: found
facts order-the-steps: found
facts sand: found
facts stain: found
facts seal: found
facts four labels: found
facts half-sheets: found
slot Evals: MISSED slot does not name: cannot show order-the-steps/breaks on order-the-steps/does not fit order-the-steps
slot Verification: MISSED slot does not name: cards blind, half-sheet
unknown how many order cards: found
forbidden invented count or a denied check: MISSED guessed a fact: 'four order-the-steps'
FAIL 9/12 key items
```
