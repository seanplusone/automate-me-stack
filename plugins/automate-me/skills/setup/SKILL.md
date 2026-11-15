---
name: setup
description: Configure a project for automate-me's skills. Detects the tracker, branches, test commands, local app URL and databases, asks you to confirm each value, then writes .claude/project-profile.md (working-rules, open-pr), .claude/query-db.json (query-db) and .claude/verify-web.yaml (verify-web). Re-running it updates them. Use for /automate-me:setup, "set up automate-me", or adding a database to query-db.
disable-model-invocation: true
---

# Set up automate-me for a project

Write the project files that `working-rules`, `open-pr`, `query-db` and `verify-web` read. Detect first, then ask. Never write a value the user has not confirmed, and never write a secret.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads. The project is the current repo root (`git rev-parse --show-toplevel`), or the folder the user names.

| Part | File | Read by | Example to start from |
|---|---|---|---|
| Project profile | `.claude/project-profile.md` | `working-rules`, `open-pr` | `../working-rules/project-profile.example.md` |
| Databases | `.claude/query-db.json`, and `.mcp.json` when you add a server | `query-db` | `../query-db/query-db.example.json` |
| Web app checks | `.claude/verify-web.yaml` | `verify-web` | `../verify-web/verify-web.example.yaml` |

## Rules

- **Detected is not confirmed.** A detected value is the recommended option in a question, never a written value until the user picks it. A value you derive (such as a ticket view command from the tracker) is shown in the step 5 summary before anything is written.
- **Ask with choices.** Use the AskUserQuestion tool where it exists, with at most 3 questions per call and 2 to 4 options each. Put the recommended option first, with "(Recommended)" in its label and its source in the description. The tool adds a free-text "Other" on its own. Ask in plain text only for values no detection can offer, such as a reviewer handle.
- **Names, never secrets.** Files hold where a secret lives: an env var name, a `pg_service.conf` section, an MCP server name, a `${VAR}` reference in `.mcp.json`. Never a password, a token, or a URL with a password in it. Don't read `.env` values, `~/.pgpass` or a password manager item. When the user pastes a secret, don't write it; ask for the name of the env var that holds it instead.
- **Whole files.** Each file is written in full, from the current values plus the answers, so a re-run gives the same file. Keep keys and sections the user added by hand.
- **Shared things stay as they are.** Don't start, stop or restart services, and don't create database logins. Report what the user must do.

## 1. Pick the parts

Check which of the three files exist, then ask one multi-select question: "Which parts should I set up?" Options:

- "Project profile": tracker, branches, tests, local app. Used by working-rules and open-pr.
- "Databases": named databases and environments for query-db.
- "Web app checks": app URLs, logins and health checks for verify-web.

Pre-select (mark Recommended) each part whose file is missing. A part whose file exists is offered as "update". When only an old `.claude/query-db.md` exists, recommend "Databases" and say it will be turned into `.claude/query-db.json`.

## 2. Detect

```bash
python3 "$SKILL_DIR"/detect.py [<project dir>]
```

It prints JSON. Every key holds a list of `{"value", "source"}` items. The keys are `default_branch`, `base_remote`, `remote_url`, `tracker`, `tests`, `app_urls`, `databases`, `mcp_servers`, `mcp_literal_secrets`, `compose_containers` and `existing_config`. Sources name the file or command each value came from, such as `package.json: scripts.test` or `.mcp.json: mcpServers.shop-db`. It reads env var names, never their values. It is read-only. Show the user nothing yet; the values appear as options in step 4.

## 3. Load what exists

Read each existing file for the chosen parts and treat its values as the current choices:

- `.claude/project-profile.md`: one ``- `key`: value`` line per key. A value still in `<...>` is unset.
- `.claude/query-db.json`: the databases as they stand. An old `.claude/query-db.md` (from before the JSON file) is read the same way: its environments table, connect methods, tenant column and large tables become the proposed JSON, confirmed in step 4.
- `.claude/verify-web.yaml` (or `.yml`, `.json`).
- `.mcp.json`: its server names, for MCP connections.

When `mcp_literal_secrets` lists anything, warn the user before step 4. Name each server and key, never the value. A literal value there (a token, or a URL with a password) is committed with the repo. Offer once to move each one to a `${VAR}` reference. The user sets `VAR` in their shell or password manager and says when it is done. Then step 6 writes `.mcp.json` with `"${VAR}"` in place of the literal. Don't print, copy or test the old value. On no, leave it, and list it under "still to do" in step 6.

On a re-run, the current value is the recommended option, ahead of a detected one. Say "current" in its description.

## 4. Ask, part by part

One part at a time, at most 3 questions per call. Skip a question whose answer is already current and the user did not ask to change. The user can answer "skip" to any value; a skipped profile value is written blank, which the skills read as "skip this step" or "ask me".

### Project profile

Keys, sections and their order come from `../working-rules/project-profile.example.md`. Write each key on its own line in exactly this form, with the value in backticks: ``- `base_branch`: `main` ``. A blank value is the key and colon with nothing after them: ``- `review_skill`:``. The profile check reads only lines of that form.

Each numbered item is one call, with at most 3 questions:

1. `tracker` (options from `tracker`: Jira with acli, GitHub Issues with gh, Linear), `base_remote` (from `base_remote`) and `base_branch` (from `default_branch`).
2. `worktree` (yes, or no for a repo that cannot run from a worktree), and `ticket_key_format` (for Jira and Linear, ask for the project key and write `KEY-123`; for GitHub Issues, `#123`).
3. `test_one` and `test_full`, with options from `tests`. For `test_one`, offer the runner with a file argument, such as `npx vitest run <file>` or `pytest <file>`. Also `app_url_test` (options from `app_urls`; it must be a local site safe for test data).
4. `worktree_copy` (offer the gitignored runtime files that exist: `.env`, `node_modules/`, `vendor/`), `clients`, and `client_repos` (default: this repo only, `web=.`).
5. Opening a PR: `ticket_url` (derived from the tracker and the remote, such as `https://github.com/acme/demo-shop/issues/<key>`), `review_status` and `default_reviewer`.
6. `project_board` and `labels`. Offer "leave blank" first for both, and for `default_reviewer` in item 5.

Derive `ticket_search`, `ticket_view` and `ticket_comments` from the tracker: for `gh`, `gh issue list --search "<words>"`, `gh issue view <n>` and `gh issue view <n> --comments`; for `acli`, `acli jira workitem search --jql '...'`, `acli jira workitem view <KEY>` and `acli jira workitem comment list --key <KEY>`; for Linear, its MCP server's search and get tools by name. Ask for `worktree_check`, `test_notes`, `app_url_other`, `review_skill` and `change_checklist` only when the user wants to fill them now; otherwise write them blank.

### Databases

Propose databases from `databases` in the detect output, then loop:

1. **Name and description.** One database per distinct thing. `DATABASE_URL` suggests `app`, `ANALYTICS_DATABASE_URL` suggests `analytics`, a compose Postgres service suggests a `local` environment of `app`. The engine is `postgres`, the only one query-db supports now; don't ask.
2. **Environments.** Multi-select from `local`, `staging`, `prod`, plus "Other". Pre-select a recommended set from the detect output. Include `local` when a compose Postgres service or a `DATABASE_URL`-style name was found. Include `staging` or `prod` when a `pg_service` section or MCP server name contains that word. With no such hint, recommend `staging` and `prod`. Then ask which one is the default (single select, non-prod only, recommend `staging`, else `local`) and which are prod (recommend any named `prod`, `production` or `prd`). The checker fails an environment with such a name that lacks `"prod": true`. A database with one environment needs no default.
3. **Connect, per environment.** Options, recommended first when its name matches the database and environment. A detected env var from a `.env` file is the local dev URL; never offer it as the recommended option for a prod or staging environment. When nothing detected fits an environment, mark no option as recommended and list `psql_service` first, since its password stays in `~/.pgpass`:
   - an MCP server from `.mcp.json` whose command mentions Postgres: `{"mcp": "<name>"}`;
   - a `~/.pg_service.conf` section: `{"psql_service": "<name>"}`;
   - an env var that holds a URL: `{"psql_env": "<VAR>"}`. Offer the detected names;
   - the user's own command that prints a connection URL, opening a tunnel first if it needs one: `{"command": "<command>"}`;
   - "Add an MCP server for this" (below).
4. **Scoping.** Tenant column (free text, or "none"), large tables (free text, or "none"), and which non-prod environments allow writes the user asks for (`allow_writes_on`). Recommend none. Each one needs a `write_connect` with a different login, asked the same way as connect. Prod is never offered.
5. Ask "Add another database?" and loop until no.

**Adding an MCP server.** When the user picks MCP and no server in `.mcp.json` fits, offer to add one. Ask which Postgres MCP server they use, and show the command each option writes:

- "postgres-mcp, run with uvx": `{"command": "uvx", "args": ["postgres-mcp", "--access-mode=restricted"], "env": {"DATABASE_URI": "${<VAR>}"}}`. Its `restricted` mode allows reads only. This package and flag were checked on PyPI (version 0.3.0); say so, and that the user should check it is still the one they want.
- "Another server": the user gives the command and args, and the env key it reads the URL from.

Name the server `<database>-<environment>-ro`, and the env var `<DATABASE>_<ENVIRONMENT>_RO_URL`. Merge it into `.mcp.json`, keeping every other server as it is. The credentials go in only as a `${VAR}` reference. Tell the user three things. Set that env var in their shell or password manager to a URL for a read-only login. Restart Claude Code so it loads the server. The login is the first lock and the server's read-only mode is the second.

### Web app checks

Keys and comments come from `../verify-web/verify-web.example.yaml`.

1. `apps`: one per URL from `app_urls`, the first local one with `test_data: true` (recommended). Ask which others exist, such as a shared staging site with `test_data: false`.
2. `login_path` (recommend `/login`), and `personas`: role names (recommend `admin` and `regular`). Each persona gets `username_env` and `password_env` names such as `ADMIN_USERNAME`, never the logins.
3. `health`: recommend the login page with status 200, plus any `/health` or `/api/health` route the user names. `containers`, `workers` and `serving_tree` only when the user has them. For `containers`, offer the names in `compose_containers`, which are compose's default `<project>-<service>-1` names (the project is the folder name unless the compose file sets `name:`). Ask the user to confirm them against `docker ps --format '{{.Names}}'` when the stack is running, since a `-p` flag or `COMPOSE_PROJECT_NAME` changes them. Never offer a bare service name such as `db`. Leave `restarts` out unless the user names one. `evidence_dir`: recommend `~/.claude/verify-evidence/web`.

If `~/.config/verify-web/users.env` is missing, offer to create it with the persona var names and empty values, mode 600. The user fills in the logins; never ask for them.

## 5. Validate before writing

Write each draft to a temp folder first, in the same layout as the project (`<tmp>/.claude/...` and `<tmp>/.mcp.json`), and check it there:

```bash
python3 "$SKILL_DIR"/../query-db/check/check_config.py <tmp>/.claude/query-db.json
python3 "$SKILL_DIR"/../working-rules/check/check_profile.py "$SKILL_DIR"/../working-rules <tmp>/.claude/project-profile.md --filled
python3 "$SKILL_DIR"/../verify-web/doctor.py --check-config --config <tmp>/.claude/verify-web.yaml
```

A FAIL goes back to the question that set that value. Don't write a file that fails its check. A WARN is shown in the summary and does not block.

**Guard the databases.** Offer once: "Run the read-only guard on each environment now?" On yes, run `../query-db/guard.sql` through each environment's `connect`, the way query-db does:

- `psql_service`: `psql "service=<name>" -X -At -f "$SKILL_DIR"/../query-db/guard.sql`
- `psql_env`: first check the variable is set, with `test -n "${<VAR>:-}"`. When it is empty or unset, mark that environment "not run: set <VAR>" and skip it. An empty string makes `psql` fall back to the local socket and any `PG*` variables, so it would guard the wrong database. When it is set, run `psql "$<VAR>" -X -At -f "$SKILL_DIR"/../query-db/guard.sql`.
- `command`: `psql "$(<command>)" -X -At -f "$SKILL_DIR"/../query-db/guard.sql`
- `mcp`: send the guard's one `SELECT` through that server's query tool. A server added in this run is not loaded until Claude Code restarts, so mark it "not run: restart first".

Prefix each `psql` call with `PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=60s'`. Report a table: database, environment, writable tables, verdict. 0 is read-only. More than 0 means the login can write, and query-db refuses that environment until it is fixed. On a prod environment that is a blocker: list it first in the reply. Don't change the config to get past it. The fix is a read-only login, made by the user or their database admin. A connection error is reported as it is, without the URL or any password.

## 6. Write and summarize

Show the drafts' values in one table (file, key, value, source: detected, current, derived or typed) and ask once: "Write these files?" On yes, write each file whole. Skip a file whose content would not change. Then reply with:

| File | Result | Checks |
|---|---|---|
| `.claude/project-profile.md` | written, or unchanged | PASS profile keys |
| `.claude/query-db.json` | written, or unchanged | PASS, and any WARN lines |
| `.mcp.json` | written (server added), or unchanged | |
| `.claude/verify-web.yaml` | written, or unchanged | CONFIG: OK |

Under it, show the guard table and any blocker. Then list what the user still has to do, such as setting an env var or restarting Claude Code. Other items: fill in `users.env`, create a read-only login, move a literal secret out of `.mcp.json`.

An old `.claude/query-db.md` stays where it is. Tell the user query-db no longer reads it and they can delete it.

## 7. Offer the doctor (optional)

When the web part was set up, offer once: "Run the verify-web doctor now, to check the app answers?" On yes, run `python3 "$SKILL_DIR"/../verify-web/doctor.py` from the project and show its lines. On no, move on. Don't offer it again.

## Eval

`check/test_detect.py` copies `cases/sample-project` to a temp folder, makes it a git repo with a `main` branch and an origin remote, and runs `detect.py` with a fake home folder and PATH. It asserts every detected value and its source, and that none of the fixture's fake secrets appear in the output.

```bash
python3 "$SKILL_DIR"/check/test_detect.py
```
