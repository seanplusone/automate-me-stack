# Resume: lint the counter module

- Goal: the counter module passes lint with no warnings
- Branch: lint-counter
- Status: in-progres
- Done and verified:
  - Lint runs clean on the counter module | evidence: script: checks/lint.sh exit 0 log: logs/lint.txt
- Not done: add lint to the pre-commit hook
- Next step: add checks/lint.sh to the pre-commit hook and run it once
- Key files: checks/lint.sh, src/counter.py
- Gotchas: none
- Waiting on: none
- Repro test: none
- Repro at parent: none
- Repro at head: none
