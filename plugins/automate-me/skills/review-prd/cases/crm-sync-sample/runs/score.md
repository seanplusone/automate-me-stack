# Score: crm-sync-sample

| | run-1 |
|---|---|
| Scored by hand (`run-1/score.md`) | 16 of 21 |
| `score_case.py` with Terms | 15 of 21 |
| `score_case.py` without Terms | 21 of 21, a false pass |

The script and the hand score differ on G03. The hand score counted a scenario line, but the run never turned it into a gap, and the key scores gaps.

Without Terms, every key row with any gap on its point passed. For example, G06 asks what happens when the pull fails, and it passed on a gap about which version is newest. The Terms lines in `key.md` stop that.

Run-1 predates the current playbook. Its gaps pass `check.py gaps`, and its `comments.md` fails `check.py open-questions`. It stays as it was saved. Score at least two runs of one version before reading a difference between versions.
