# Resume: trim drops tabs

- Goal: trim() strips tabs and newlines, not only spaces
- Branch: fix-trim-tabs
- Status: in progress
- Done and verified:
  - New test fails on the parent | evidence: script: trim/head/trim_tabs_test.py exit 1 log: logs/trim-parent.txt
  - Fix makes it pass | evidence: log: logs/trim-head.txt
- Not done: run the full suite
- Next step: run the full suite and record its log
- Key files: trim/head/trim.py, trim/head/trim_tabs_test.py
- Gotchas: the old trim_test.py passed on the buggy code, so it is not the repro
- Waiting on: none
- Repro test: trim/head/trim_tabs_test.py
- Repro at parent: exit 1 log: logs/trim-parent.txt
- Repro at head: exit 0 log: logs/trim-head.txt
