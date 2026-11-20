# Attack pass

The default for a review. Assume the change is wrong. Do not trust a test count, a line that says pass, or the PR description until you have run it.

## What to run

Write the inputs before you treat the author's tests as evidence. Each input is one of these:

- an edge, such as empty, missing, or zero
- a malformed value, such as the wrong type
- a boundary, such as the cap and the count just under it
- keyword-stuffed nonsense, when the change scores or matches text
- a claim the PR asserts and never executes

Run the code. Record the command and the output you saw. A finding without a file and line, and without that output, is dropped.

## Second pass

`python3 "$SKILL_DIR"/check/attack_agents.py` prints the CLIs it found. It knows `codex exec` and `claude -p`, and nothing else. `none` means you write the only pass. Names mean you run:

```
python3 "$SKILL_DIR"/check/attack_agents.py --run --brief <dir>/attack-brief.md --out <dir>/passes --cwd <checkout>
```

The script starts those CLIs in `<checkout>`. The brief is their stdin, not an argument. Codex uses a workspace-write sandbox. Claude may run Bash there, with `acceptEdits`, and does not get a machine-wide bypass. Each pass waits at most 600 seconds (`--timeout`). Stderr is saved next to the pass. A timeout is `Parse: timeout`, not an empty approve. The script does not contain the attack rules. Put the rules in the brief, and paste the same brief to every pass.

## Brief

Write `<dir>/attack-brief.md` in your own words from this outline. Paste the diff and the PR body. Do not paste a case key.

1. Assume the change is wrong. Try to break it.
2. Do not trust the PR's test count or its pass line. Re-run the claim.
3. Run the inputs from "What to run" against the code in the diff.
4. Reply with only an attack file, in the shape below. No preamble.

## Attack file

Run `python3 "$SKILL_DIR"/check/check_attack.py <dir>/attack.md` on the file. It fails when the file does not parse. It fails when no input was tried. It fails a finding with neither a file and line nor a repro. It fails when Held omits an input that did not break. It finds `key.md` above the file and fails an approve when that key marks a planted bug.

```
# Attack review: <topic>

Verdict: approve | needs fixes

## Tried
- Input: <the value or command you ran>
  Observed: <what the run printed>
  Broke: yes | no

## Findings
### F1 | <path>:<line> | passes: <agent names>
<One sentence: what broke, and what a caller would see.>
Repro: <the input, or none>
Observed: <the output, or none>

## Held
- Input: <an input that did not break>
  Observed: <what the run printed>
```

`Verdict` is `needs fixes` when any finding remains, and `approve` when none do. A finding's middle field is `none` only when the repro and the observed output are both filled in. Held lists every Tried input whose Broke line is `no`. With one pass, that pass's name is `current`.

## Merge

```
python3 "$SKILL_DIR"/check/merge_attacks.py --out <dir>/attack.md <dir>/passes/*.md
```

Findings match on the file and the line. `head/cap.py:3` and `cap.py:3` are the same line. Wording does not split them. A finding from either pass is kept, with both passes' evidence. The verdict is needs fixes when a finding remains. A pass that does not parse does not become an approve. A clean pair of passes with no finding is an approve.
