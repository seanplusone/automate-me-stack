# Score: refund-endpoint

A synthetic case: the repo, PR, code and drafts were written by hand to show how a case is scored. The drafts were not produced by a skill run, so this score shows the scorer working, not the skill's recall.

| | run-1 |
|---|---|
| Drafts | hand-written, one PR |
| `score_case.py` | PASS, 3 of 3 |
| Found by hand | K1, K2, K3 |
| Unsupported | 0 |
| Traps hit | 0 |
| `check_drafts.py` | PASS |

What each row exercises:

- K1 is a line row with a `Terms:` line. The comment sits on line 44, the nearest changed line, which is inside the 3-line window around the key's line 42. The comment names "refunded" and "total", which meets `refunded | total/remaining`; "remaining" would have met it too.
- K2 is a directory-prefix row (`app/payments/`) with a minimum of 4 sites. The comment on `provider.py:27` carries `Sites: 4`, so it reaches the minimum. The copy on `ledger.py:15` repeats the text and counts once toward the cap.
- K3 is a PR-level row. Only a finding headed `PR` earns it, because the reconciliation job is code the diff does not touch.

Output of `python3 check/score_case.py cases/refund-endpoint/key.md cases/refund-endpoint/runs/run-1/drafts.md`:

```
K1 orders-api#214 found
K2 orders-api#214 found
K3 orders-api#214 found
PASS 3/3 key findings
```
