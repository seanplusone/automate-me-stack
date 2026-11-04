---
name: verify-web
description: Prove a change works in the running web app the way a user sees it, with saved evidence. Runs a config-driven doctor first, drives the screens in a browser (Playwright MCP by default), and checks each side effect a second way. `verify-web pr <number|url>` runs the PR's claims on base and head and writes verify.md for review-pr. Use before saying a web change works, and whenever the local app behaves oddly.
---

# verify-web

Check the app is worth driving, drive the feature through the browser as a user, and keep the
evidence. A green test run, a 200 from an API, or a reading of the code is not proof of what a
user sees.

**Run the doctor before anything else, and again whenever a result looks wrong.** Most "my fix
does not work" moments are the stack, not the fix. A server is down, a worker is running code from
before your edit, or the page and the job run two different checkouts.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

## Modes

- `verify-web <what to prove>`: prove one change or reproduce one bug. Follow this file.
- `verify-web pr <number|url>`: prove or disprove what a PR claims, before and after. Follow
  [`playbooks/pr.md`](playbooks/pr.md), which uses everything in this file.

## Setup, once per project

1. Run `/automate-me:setup` and pick "web app checks", or copy
   [`verify-web.example.yaml`](verify-web.example.yaml) to `.claude/verify-web.yaml` in the project
   and fill it in. A `.claude/verify-web.json` with the same keys also works. If neither exists,
   stop and point the user at `/automate-me:setup`; do not guess URLs or container names.
2. Copy [`users.env.example`](users.env.example) to `~/.config/verify-web/users.env` and
   `chmod 600` it. The user fills in the logins. See [`personas.md`](personas.md).
3. Install a browser MCP. The default is Playwright MCP: `claude mcp add playwright npx @playwright/mcp@latest`.
   The chrome-devtools MCP (`npx chrome-devtools-mcp@latest`) also works. This file names browser
   tools by what they do (snapshot, screenshot, console messages, network requests); use the
   matching tool of whichever MCP is loaded.

## Non-negotiables

- **Create data only on an app marked `test_data: true`.** Any other app is read and look only,
  unless the user says otherwise in that message.
- **Drive through the screens a user uses.** The API and the database are for checking what the
  screen claimed, never for getting past a step. A run that skips a step with an API call or a SQL
  write proves nothing.
- **Diagnose a shared stack, don't repair it.** Do not edit its config, restart its services or
  reinstall its packages to get past a doctor FAIL. Report the line and stop until the user fixes
  it. The exceptions are the commands listed under `restarts:` in the config, which the doctor
  prints next to the line they fix. Those you may run, then rerun the doctor.
- **Never paste a password** into a report, a file name, a screenshot name or a commit. Read it
  from `users.env` at the moment you type it.
- Never stop or remove containers or kill processes by name. Other sessions may use them.

## Doctor

```bash
python3 "$SKILL_DIR"/doctor.py                           # finds .claude/verify-web.yaml from the cwd upward
python3 "$SKILL_DIR"/doctor.py --config path/to/verify-web.json
python3 "$SKILL_DIR"/doctor.py --expect-sha <sha>        # PR mode: fail unless the app serves this sha
python3 "$SKILL_DIR"/doctor.py --check-config            # the config's keys and types only, no network
```

Read-only and Python stdlib only. It prints one PASS, WARN or FAIL line per check, then
`DOCTOR: OK` (exit 0) or `DOCTOR: FAIL` (exit 1). Ready means `DOCTOR: OK`, not "the containers
are Up". Every container can be Up while every page returns 502.

It checks, in order:
- the apps in the config, and which one is safe for test data;
- each `health` URL returns its `expect_status`, without following redirects;
- each listed container is running;
- each worker is running, and no file under its `source_dirs` is newer than its start time;
- which tree serves the page and which tree runs the jobs, from the `serving_tree` commands;
- each persona has a login in `users.env`, and the file is mode 600;
- the evidence folder is outside the plugin.

| Doctor says | What it means | What you do |
|---|---|---|
| `FAIL http <name> no answer` | Nothing listens on that URL. | Report it. Starting a shared stack is the user's call. |
| `FAIL http <name> 502` | The proxy is up and the app behind it is not. | Report it with the URL. |
| `FAIL worker <name> STALE` | A source file changed after that worker started, so it runs old code. | Run the pre-authorized fix if the doctor printed one, then rerun the doctor. Otherwise report it. |
| `WARN tree match ... DIFFERENT trees` | The page and the background job run different checkouts. | A result proves only the half that ran your code. Say which half in the report. |
| `FAIL tree page ... expected <sha>` | The app serves another tree than the one you mean to test. | Point the app at that tree (PR mode step 5), or report it. |
| `WARN persona <role> no value` | That login is missing. | Use another persona only if the task allows it. Otherwise ask the user. |

The staleness check compares the worker's start time with the newest file in its source dirs, so
it also catches an uncommitted edit. It does not see a change to environment variables or cached
config. Restart after those regardless, if a restart is pre-authorized.

## Drive

- Open your own browser page or tab and close it at the end. Leave other tabs alone.
- Sign in on the config's `login_path` as the default persona (the first one in the config). Use
  another persona only when the task names it.
- Locate controls from the accessibility snapshot, by role, accessible name, label or `name=`
  attribute. Never by screen coordinates.
- Record every id the run creates, so cleanup can find it.
- Feature recipes live in the project's `.claude/verify-web/features/`. Read its index, then the
  feature's file. [`features/README.md`](features/README.md) has the conventions, the recipe
  template and an example. When a run needed setup no recipe covers, write one afterwards.

## Evidence

Write to `<evidence_dir>/<YYYYMMDD-HHMM>-<feature>/` (default `~/.claude/verify-evidence/web/`),
outside the plugin, so a plugin update never deletes it. For every proof keep:

- the doctor output for the run, saved as `doctor.txt`;
- a snapshot before and after the action, and a screenshot with the URL visible;
- the console messages, and every non-2xx response from the network requests;
- the side effect proven a second way, such as the row in the database, the job in the queue's own
  screen, the file in storage, or the record reopened in a fresh page load. A screen that says
  "saved" is the claim, not the proof;
- the branch and sha of the tree that served the page and of the tree that ran the job.

## Cleanup

- Undo what the run created through the app's own screens. Never reset state with direct SQL.
- List the ids you created and could not remove in the report, so a leftover can be found.
- Close the pages you opened.
- Restart nothing except a pre-authorized restart for a line the doctor flagged.
- Evidence stays. Cleanup never deletes the evidence folder.

## Report

Say what you proved, on which app and tree (branch and sha), as which persona, and where the
evidence is. Name anything you could not reach, with the step you tried and the precondition that
was missing. Never report a step as verified through a different entry point than the one asked.

## Files

- `doctor.py`: the health check. Read-only, exit 0 or 1.
- `verify-web.example.yaml`: every config key, with comments.
- `personas.md` and `users.env.example`: who to sign in as, and where the logins live.
- `features/`: recipe conventions, the template, and an example recipe for the demo app.
- `playbooks/pr.md`: PR mode.
- `check/check_verify.py`: checks a PR-mode `verify.md` before you hand it on.
- `check/`: tests for the doctor and the PR case, run against `cases/demo-app/`.
