# Score: word-score

A synthetic case. The module, the diff and the PR body are invented. The codex CLI and the claude CLI were not on PATH. `check/attack_agents.py` printed `none`, so the current agent wrote the only pass.

The pass re-ran `python3 case_test_score_review.py`. It printed `1 passed` and exited 0. It then called `passes` on the inputs in `runs/run-1/trace.txt`. On the base, `bug line bug line` returns False. `merge_attacks.py` wrote `attack.md` from that pass.

The author's test held. The sentence `bug at line 3` held. `all good` held. The empty string held.

| | run-1 |
|---|---|
| Agent | current |
| `check_attack.py` | PASS |
| `score_case.py` | PASS, caught the planted bug |
| Verdict | needs fixes |

Output of `python3 check/check_attack.py cases/word-score/runs/run-1/attack.md --key cases/word-score/key.md`:

```
PASS attack: attack.md
```

Output of `python3 check/score_case.py cases/word-score/key.md cases/word-score/runs/run-1/attack.md`:

```
SKIP no agent CLI on PATH
SKIP meaning
WEAK location only
```
