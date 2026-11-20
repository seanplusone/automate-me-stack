# Score: item-cap

A synthetic case. The module, the diff and the PR body are invented. The codex CLI and the claude CLI were not on PATH. `check/attack_agents.py` printed `none`, so the current agent wrote the only pass.

The pass re-ran `python3 test_cap.py`. It printed `2 passed` and exited 0. It then called `within_cap` on 4, 5, 6 and 0. On the base, `within_cap(5)` returns True. `merge_attacks.py` wrote `attack.md` from that pass.

The author's two tests held. Counts 4, 6 and 0 held. Count 5 did not.

| | run-1 |
|---|---|
| Agent | current |
| `check_attack.py` | PASS |
| `score_case.py` | PASS, caught the planted bug |
| Verdict | needs fixes |

Output of `python3 check/check_attack.py cases/item-cap/runs/run-1/attack.md --key cases/item-cap/key.md`:

```
PASS attack: attack.md
```

Output of `python3 check/score_case.py cases/item-cap/key.md cases/item-cap/runs/run-1/attack.md`:

```
F1 caught
PASS caught planted bug
```
