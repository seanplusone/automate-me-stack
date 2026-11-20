# Attack pass

The default for a review. Assume the change is wrong. Do not trust a test count, a line that says pass, or the PR description until you have run it.

## What to run

Write the inputs before you treat the author's tests as evidence. Each input is one of these:

- an edge, such as empty, missing, or zero
- a malformed value, such as the wrong type
- a boundary, such as the cap and the count just under it
- keyword-stuffed nonsense, when the change scores or matches text
- a claim the PR asserts and never executes

Run the code. Record the command and the output you saw. A finding needs a file and a line, or a repro of that output. A null line is kept when the repro is filled in.

## Second pass

`python3 "$SKILL_DIR"/check/attack_agents.py` prints the CLIs it found. It knows `codex exec` and `claude -p`, and nothing else. `none` means you write the only pass. Names mean you run:

```
python3 "$SKILL_DIR"/check/attack_agents.py --run --brief <dir>/attack-brief.md --out <dir>/passes --cwd <checkout>
```

The script starts those CLIs in `<checkout>`. The brief is their stdin, not an argument. Codex uses a workspace-write sandbox. Claude may run Bash there, with `acceptEdits`, and does not get a machine-wide bypass. Each pass waits at most 600 seconds (`--timeout`). Stderr is saved next to the pass. A timeout is `Parse: timeout`, not an empty approve. The script appends the attack-file section below to every brief.

## Brief

Write `<dir>/attack-brief.md` in your own words from this outline. Paste the diff and the PR body. Do not paste a case key.

1. Assume the change is wrong. Try to break it.
2. Do not trust the PR's test count or its pass line. Re-run the claim.
3. Run the inputs from "What to run" against the code in the diff.
4. End the reply with exactly one json fence, in the shape below. Prose before it is ignored.

## Attack file

End the pass with exactly one json fence. Prose before it is fine. The machine reads only that block. A second fence is an error, even inside another fence. A json object with no fence is read only when it is the whole output.

```json
{"verdict": "approve", "tried": [{"input": "within_cap(4)", "broke": false, "observed": "True"}], "findings": []}
```

`verdict` is `approve` or `needs fixes`. Each tried row has a string `input`, a boolean `broke`, and a string `observed`. Each finding has string `file`, `claim`, and `repro`, and `line` as an integer or null. Extra keys are ignored. A repeated key is an error. A line of 0 or null uses a line suffix on the file, such as `:3` or `#L3`.

An approve needs at least one tried row, every `broke` false, and no findings. A true `broke` or any finding is needs fixes, even if the verdict says approve. Missing or invalid JSON is an error, and an error is not an approve.

Run `python3 "$SKILL_DIR"/check/check_attack.py <dir>/attack.md`. It finds `key.md` above the file and fails an approve when that key marks a planted bug.

## Merge

```
python3 "$SKILL_DIR"/check/merge_attacks.py --out <dir>/attack.md <dir>/passes/*.md
```

Findings on the same file and line are one finding. `head/cap.py` and `cap.py` match. A null line is kept and is not dropped. It matches a key only when the file matches too. Both passes' claims stay in the merged finding. The merge approves only when every pass is a valid approve.
