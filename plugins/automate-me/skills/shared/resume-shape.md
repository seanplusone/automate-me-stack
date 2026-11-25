# RESUME.md shape

`RESUME.md` holds a paused run's state, so a new session can pick it up from the file and not the chat. Every claim of done work carries a pointer a script can resolve. Self-report is never proof.

Check a file with `python3 "$SKILL_DIR"/../shared/check_resume.py <RESUME.md> [--root DIR] [--git-dir DIR]`. It prints PASS or FAIL and exits 1 on FAIL. For a bug fix, `python3 "$SKILL_DIR"/../shared/check_repro.py --test <path> --parent <sha> --head <sha>` reruns the repro itself.

## Slots

Each slot appears once, with exactly this label:

```
# Resume: <short title>

- Goal: <the run's goal>
- Branch: <branch name, or none>
- Status: in progress | waiting on user | blocked | done
- Done and verified:
  - <item> | evidence: <pointer>
- Not done: <what's left>
- Next step: <the first action on pickup>
- Key files: <paths>
- Gotchas: <or none>
- Waiting on: <the question, or none>
- Repro test: <path to a NEW test, or none: not a bug fix>
- Repro at parent: <fail evidence, or none>
- Repro at head: <pass evidence, or none>
```

| Slot | Rule |
|---|---|
| Title | `# Resume: ` and a short title, on the first non-empty line. |
| Goal, Next step, Key files | Required. Never empty, never `none`. |
| Status | One of `in progress`, `waiting on user`, `blocked`, `done`. |
| Branch, Not done, Gotchas | A value, or `none`. |
| Waiting on | The question, or `none`. Not `none` when Status is `waiting on user`. |
| Done and verified | One list line per item, each ending in `evidence:` and a pointer. `none` only when nothing is done yet, and never with Status `done`. |
| Repro test, Repro at parent, Repro at head | All three `none` (or `none: not a bug fix`) for a run that fixes no bug. Otherwise all three are filled, as below. |

`none` may carry a reason after a colon, as in `none: not a bug fix`.

## Evidence pointers

A pointer resolves in one of three ways. Paths are relative to `--root`, which defaults to the folder that holds the resume.

1. A log path that exists and is not empty: `evidence: logs/trim-test.txt` or `evidence: log: logs/trim-test.txt`. A quoted path may contain spaces: `log: "logs/trim parent.txt"`. An empty file fails, and so does a file whose only text is a claim such as "tests passed".
2. A script that exists, with its exit code and a log that exists: `evidence: script: checks/lint.sh exit 0 log: logs/lint.txt`. The exit code is recorded, not judged: a new test that fails on the parent is done work with `exit 1`.
3. A git commit SHA in the repo, full or an unambiguous short form: `evidence: 3f2a9c1`. The repo is `--git-dir`, or the current one. A branch or tag name is not a SHA, even if it looks like hex.

A pointer of only words ("tests passed", "I checked", "step 3 done", "ok") fails as self-report. A path that does not exist and a SHA the repo does not have fail too, even next to one that resolves.

## Bug fixes

When `Repro test` is not `none`, the run is a bug fix:

- `Repro test` is the path of the new test, and it exists.
- `Repro at parent` is fail evidence that resolves: a non-empty log and a recorded `exit N` with N not 0. A missing exit or a recorded `exit 0` fails.
- `Repro at head` is pass evidence: `exit 0` and a non-empty log.

A SHA may sit on a Repro line as extra pointer text, for example `exit 1 log: logs/parent.txt at 3f2a9c1`. It must exist.

The logs show what ran once. `check_repro.py` proves it again: the test file must be new (it did not exist at the parent commit), the parent must be an ancestor of head, and it runs the head version of the test on the parent tree, where it must fail, and on head, where it must pass. A tweaked old test, or a test that already passed on the parent, fails that check. It does not prune other worktrees in the repo.

## Example

```
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
- Gotchas: none
- Waiting on: none
- Repro test: trim/head/trim_tabs_test.py
- Repro at parent: exit 1 log: logs/trim-parent.txt
- Repro at head: exit 0 log: logs/trim-head.txt
```
