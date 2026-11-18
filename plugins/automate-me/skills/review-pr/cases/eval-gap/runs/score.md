# Score: eval-gap

A synthetic case: the repo, PR, and drafts were written by hand to show the eval-gap lens findings. The drafts were not produced by a skill run, so this score shows the scorer working, not the skill's recall.

| | run-1 |
|---|---|
| Drafts | hand-written, one PR |
| `score_case.py` | PASS, 2 of 2 |
| Found by hand | K1, K2 |
| Unsupported | 0 |
| Traps hit | 0 |
| `check_drafts.py` | PASS |

What each row exercises:

- K1 is a PR-level row. The eval scored a different path than production, so the comment sits on the PR, not on a line in the diff. The comment names "gate" and "eval".
- K2 is a line row on the model registry. The comment sits on line 12 and names "default" and "eval".

Output of `python3 check/score_case.py cases/eval-gap/key.md cases/eval-gap/runs/run-1/drafts.md`:

```
K1 text-app#88 found
K2 text-app#88 found
PASS 2/2 key findings
```
