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

The script starts those CLIs in `<checkout>`. The brief is their stdin, not an argument. Codex uses a workspace-write sandbox. Claude may run Bash there, with `acceptEdits`, and does not get a machine-wide bypass. Each pass waits at most 600 seconds (`--timeout`). Stderr is saved next to the pass. A timeout is `Parse: timeout`, not an empty approve. The script puts the attack-file section below in front of every brief. `--sandbox auto` uses `bwrap` when it is installed. A reachable `key.md` runs only inside `bwrap`. `--sandbox none` cannot override that. A checkout with no reachable `key.md` may use `--sandbox none`, and that prints a warning. Inside `bwrap`, Codex starts from its real binary with `--sandbox danger-full-access` and the host network. `bwrap` is the boundary. Codex's own bubblewrap cannot start there. Claude still uses `acceptEdits` and may run Bash.

## Sandbox

`bwrap` is the reference backend. `--sandbox docker` is a stub. Before a mount, the script walks the cwd and every parent up to the root. The walk follows links and enters dot directories, `.git`, and `node_modules`.

If a `key.md` is reachable and the cwd is not a case with `head` and `base`, the run is refused. A directory that cannot be listed is treated the same way. A practice run without `bwrap` is refused too.

The sandbox is a fresh root. `/usr`, `/bin`, `/lib`, and `/etc/alternatives` are read-only, so `awk`, `sed`, `grep`, `find`, `python3`, `python`, and `git` resolve. `/tmp` is a writable empty disk. The CLI package directory is read-only, so a helper next to the real binary is visible.

Network stays on. A real review can reach the public internet and a local service, such as a Docker API on port 2375. That is accepted because `bwrap` is the boundary, and Codex runs with full access inside it.

`/work` is the checkout when no `key.md` is reachable. When the cwd is a case, `/work` holds only the copied `head` and `base`. The case key is not copied. While copying a case, every file with more than one link is left out, and the path is printed. In a directory that is not a case, a hard link to a key anywhere under a `cases` tree is refused. A hard link to a key.md outside those trees is not detected.

Login files are passed in with `bwrap --file` and are not written to the host. Codex gets `auth.json` and `config.toml` with host tables removed: projects, hooks, plugins, mcp servers, and notify. History keeps its settings, except paths under the home directory or the repo. Claude gets `.credentials.json`, and `.claude.json` under `CLAUDE_CONFIG_DIR` with onboarding and account fields only. `CODEX_HOME` and `CLAUDE_CONFIG_DIR` point at `/home/agent`. API key variables are passed by name and are not printed. Add a backend by teaching `attack_agents.py` a new `--sandbox` name.

## Brief

Write `<dir>/attack-brief.md` in your own words from this outline. Paste the diff and the PR body. Do not paste a case key.

1. Assume the change is wrong. Try to break it.
2. Do not trust the PR's test count or its pass line. Re-run the claim.
3. Run the inputs from "What to run" against the code in the diff.
4. End the reply with exactly one json fence, in the shape below. Prose before it is ignored.

## Attack file

End the pass with exactly one json fence. Prose before it is fine. The machine reads only that block. A second fence is an error, even inside a quote or another fence. A json object with no fence is read only when it is the whole output.

```json
{"verdict": "approve", "tried": [{"input": "within_cap(4)", "broke": false, "observed": "True"}], "findings": []}
```

`verdict` is `approve` or `needs fixes`. Each tried row has a string `input`, a boolean `broke`, and a string `observed`. Each finding has string `file`, `claim`, and `repro`, and `line` as an integer or null. Extra keys are ignored. A repeated key is an error. A line of 0 or null uses a line suffix on the file, such as `:3` or `#L3`.

An approve needs at least one tried row, every `broke` false, and no findings. A true `broke` or any finding is needs fixes, even if the verdict says approve. Missing or invalid JSON is an error, and an error is not an approve.

## Check

Run `python3 "$SKILL_DIR"/check/check_attack.py <dir>/attack.md`. It uses the case key and fails an approve when that key marks a planted bug.

## Merge

```
python3 "$SKILL_DIR"/check/merge_attacks.py --out <dir>/attack.md <dir>/passes/*.md
```

Findings on the same file and line are one finding. `head/cap.py` and `cap.py` match. A range such as `file:3-6` stays a range. A null line is kept. It matches a key only when the file matches too. Both passes' claims stay in the merged finding. The merge approves only when every pass is a valid approve. Do not pass `--out` as one of the inputs.
