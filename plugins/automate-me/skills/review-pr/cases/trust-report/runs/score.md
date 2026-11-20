# Score: trust-report

A synthetic case. The module, the diff and the PR body are invented. The codex CLI and the claude CLI were not on PATH. `check/attack_agents.py` printed `none`, so the current agent wrote the only pass.

The pass re-ran `python3 case_test_report.py`. It printed `2 passed` and exited 0. It then called `accept` on the inputs in `runs/run-1/trace.txt`. On the base, the failed case returns False. `merge_attacks.py` wrote `attack.md` from that pass.

The author's two tests held. A report with `passed` false held. An empty report held.

| | run-1 |
|---|---|
| Agent | current |
| `check_attack.py` | PASS |
| `score_case.py` | PASS, caught the planted bug |
| Verdict | needs fixes |

Output of `python3 check/check_attack.py cases/trust-report/runs/run-1/attack.md --key cases/trust-report/key.md`:

```
PASS attack: attack.md
```

Output of `python3 check/score_case.py cases/trust-report/key.md cases/trust-report/runs/run-1/attack.md`:

```
SKIP no agent CLI on PATH
caught
PASS caught planted bug
```
