# Score: badge-ramble

A synthetic case. Run 1 was written by hand to show how a case is scored. No blind run has been scored yet.
Its Output answers where the widget lives and what shares that space: the container, the overlays and the states.

| | run-1 |
|---|---|
| Brief | hand-written |
| `check_brief.py` | PASS |
| `score_case.py` | PASS, 13 of 13 |

Output of `python3 check/score_case.py cases/badge-ramble/key.md cases/badge-ramble/runs/run-1/brief.md` (exit 0):

```
facts bell: found
facts top bar: found
facts avatar menu: found
facts tooltip: found
facts 99+: found
slot Kind: found
slot Output: found
slot Done: found
slot Verification: found
unknown loading: found
unknown narrow screen: found
forbidden loading state invented: clear
parking pulse: found
PASS 13/13 key items
```
