---
name: query-db
description: Run read-only queries against a project's Postgres databases, non-prod by default, prod only when the user names it in that message, prod writes always refused. Reads the named databases and their environments from the project's .claude/query-db.json. Use for "query staging", "query analytics prod", "check this row in production", or any look at live data.
---

# query-db

This skill runs SQL against the databases a project lists in `.claude/query-db.json`, under fixed safety rules. It does not open connections itself. The project picks how to connect to each environment of each database. It can use a Postgres MCP server, a `psql` service entry, an env var that holds a URL, or the user's own command. The rules below hold for every method.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

## Setup (once per project)

1. Run `/automate-me:setup` and pick "databases", or copy `query-db.example.json` from this folder to `.claude/query-db.json` in the project and edit it. The file is shaped like an MCP servers file: one entry per database under `"databases"`, each with its environments.
2. Create a read-only login on each database: `SELECT` grants only, no table ownership, not a superuser. Point every `connect` at it.
3. Check the file: `python3 "$SKILL_DIR"/check/check_config.py .claude/query-db.json`. It fails on a missing default, a prod environment open to writes or used as the default, and an environment named like prod without `"prod": true`. It also fails on a `write_connect` outside `allow_writes_on`, a field of the wrong type, an unknown engine, and a connect that is not exactly one method. It also fails on the common shapes of a secret: a password key, `password=`, `user:password@`, a password flag with a value. It cannot catch every secret, so read the file too.
4. Run the guard below once against each environment and check that it returns 0 on every one.

If `.claude/query-db.json` is missing, stop and point the user at step 1. Don't guess hosts or logins. An old `.claude/query-db.md` from an earlier version is not read; `/automate-me:setup` turns it into the JSON file.

## The config

```json
{
  "databases": {
    "app": {
      "engine": "postgres",
      "description": "main app database",
      "environments": {
        "staging": { "default": true, "connect": { "mcp": "app-staging-ro" } },
        "prod": { "prod": true, "connect": { "psql_service": "app_prod_ro" } }
      },
      "tenant_column": "account_id",
      "large_tables": ["events", "audit_log"],
      "allow_writes_on": ["staging"]
    }
  }
}
```

| Key | Where | Meaning |
|---|---|---|
| `engine` | database | `"postgres"`. It is the only engine supported now; the checker rejects any other. |
| `description` | database or environment | What it holds. Used to match a request like "the reporting database". |
| `environments` | database | One entry per environment, at least one. |
| `default` | environment | The environment used when the user names none. At most one per database, and never a prod one. A database with one environment needs none. |
| `prod` | environment | `true` for every environment that serves customers. It must be a real `true`, not `"true"`. An environment named `prod`, `production` or `prd` must have it. |
| `read_replica` | environment | `true` when that connection reaches a read replica, not the primary. |
| `connect` | environment | How to reach it with the read-only login. Exactly one of the four methods below. |
| `write_connect` | environment | Optional. A second login for writes, only on a non-prod environment in `allow_writes_on`. The checker fails it anywhere else. |
| `tenant_column`, `tenant_also` | database | The column every query is scoped by, and any second columns where a table has them. |
| `large_tables` | database | Tables where a full scan or `COUNT(*)` hurts. |
| `allow_writes_on` | database | Non-prod environments where a write the user asks for may run. Empty or missing means none. |

Connect methods. None of them holds a password; the file names where the secret lives.

| Method | Value | How the skill connects |
|---|---|---|
| `{"mcp": "<name>"}` | A server in the project's `.mcp.json` (or the user's MCP config) | Through that server's query tool. Its own read-only mode is a second lock. The login is the first. |
| `{"psql_service": "<name>"}` | A section in `~/.pg_service.conf` | `psql "service=<name>"`. The password comes from `~/.pgpass` or the service file. |
| `{"psql_env": "<VAR>"}` | The name of an env var that holds a connection URL | `psql "$<VAR>"`, only after checking the variable is set and not empty. The user's shell or password manager sets it. |
| `{"command": "<command>"}` | The user's own command that prints a connection URL, opening a tunnel first if it needs one | `psql "$(<command>)"`. The output goes straight into `psql`, never to the screen. |

The skill does not build or open tunnels. A command that opens one is the user's own, written by them.

## Picking the target

Each query runs on one database and one environment. Pick both from the user's message.

- **Database.** The name the user gives ("query analytics prod" means `analytics`), or the one whose `description` matches what they asked about. With no name: the only database when the file has one; with several, ask which one in one line that lists the names. Don't guess from the table name.
- **Environment.** The one the user names in this message. With none named: the database's `default` environment, or its only environment.
- **Prod only when named.** A prod environment is used only when the user names it in this message. A prod request from an earlier message does not carry over. When the database's only environment is prod and the user did not name it, ask before running.
- Say the target in the reply: `analytics / prod`.

## Non-negotiables

- **Read-only by default.** Every query is a read unless the user asks for a specific write in this message.
- **The default environment is non-prod.** Use the database's `default` environment unless the user names another in this message. Use a production environment only when the user names it in that same message. A prod request from an earlier message does not carry over.
- **Prod writes are refused, always.** Whatever is asked, no write reaches production through this skill, whatever the config says. Hand the user the exact SQL and stop.
- **Non-prod writes are limited.** Write only when the user asks for that write in this message, and only on an environment listed in that database's `allow_writes_on`. The write goes through that environment's `write_connect`. With no `write_connect`, hand the user the SQL. Show the statement first. It has a `WHERE` that names the rows. Never `DROP`, `TRUNCATE`, or an `UPDATE` or `DELETE` without a `WHERE`.
- **Production may be the primary.** Unless the environment has `"read_replica": true`, assume a prod query runs on the database that serves customers. Use `LIMIT`, filter on indexed columns, and never run a full-table scan or `COUNT(*)` on a table in `large_tables`. Run `EXPLAIN` first when unsure.
- **Every session has a statement timeout.** Set `statement_timeout` to 60s or less before the first query (`SET statement_timeout = '60s'`, or `PGOPTIONS` with `psql`).
- **Never print credentials.** Don't echo `$PGPASSWORD` or a `psql_env` variable, run `env`, print the output of a `command` connection, `cat` a `.pgpass` or service file, or read a password manager item yourself.
- **Personal data stays out of the reply.** Names, emails, phone numbers, addresses and similar fields stay out unless the user asked for them. Select the columns you need, not `*`.
- **Tenant scoping (multi-tenant projects).** When the database has a `tenant_column`, scope every query by it, and by each `tenant_also` column where the table has it. Without row-level security, an unscoped query reads every tenant.

## The guard: refuse a write-capable login

Before the first query on each database and environment pair in a session, run `guard.sql` from this folder through that environment's `connect`. It counts the tables the current login can `INSERT`, `UPDATE`, `DELETE` or `TRUNCATE` in non-system schemas. `app / staging` and `analytics / staging` are two pairs, and each gets its own guard run.

- `mcp`: read `"$SKILL_DIR"/guard.sql` and send its one `SELECT` through that server's query tool.
- `psql_service`: `psql "service=<name>" -X -At -f "$SKILL_DIR"/guard.sql`
- `psql_env`: `test -n "${<VAR>:-}" && psql "$<VAR>" -X -At -f "$SKILL_DIR"/guard.sql`. When the variable is unset or empty, stop and tell the user to set it. Never run `psql` with an empty connection string: it falls back to the local socket and any `PG*` variables, and would guard and query the wrong database.
- `command`: `psql "$(<command>)" -X -At -f "$SKILL_DIR"/guard.sql`

If the result is more than 0, refuse to run anything on that pair. Tell the user which database and environment, how many tables, and that the login behind its `connect` can write. They fix it by pointing that `connect` at a read-only login. Don't work around the guard by wrapping queries in a read-only transaction. A `write_connect` login is expected to write and is not guarded.

The guard reads 0 on a database with no tables, so a 0 there proves nothing. Say so when it happens.

## Use

1. Read `.claude/query-db.json`. Pick the database and environment (see "Picking the target").
2. Run the guard on that pair, once per session.
3. Set the statement timeout. With `psql`, start read sessions with `PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=60s'`.
4. Write the query against the rules above, and run it.
5. Reply with the answer first, then the query you ran and the database and environment it ran on. Say how many rows came back and whether `LIMIT` cut them off.

For a write on non-prod, show the statement and the rows its `WHERE` matches (a `SELECT` with the same `WHERE`). Wait for the user's go before running it through `write_connect`. Report the affected row count.

## When it fails

| Message | Fix |
|---|---|
| No `.claude/query-db.json` | The user runs Setup step 1. |
| `check_config.py` fails | Fix each FAIL line it prints, or rerun `/automate-me:setup`. |
| Several databases and none named | Ask which one, listing the names. |
| The guard returns more than 0 | The login can write. The user points that `connect` at a read-only login. |
| Password authentication failed | Wrong password in the user's store, or that login doesn't exist on that database. The user fixes it. Don't ask for the password. |
| Connection refused on a tunnel port | The tunnel is not open. The user runs their own tunnel command, or fixes the `command` in the config. |
| The MCP server named in `connect` is not loaded | It is missing from `.mcp.json`, or Claude Code has not restarted since it was added. The user adds it or restarts. |
| `canceling statement due to statement timeout` | The query is too broad. Filter on an indexed column or add `LIMIT`. Don't raise the timeout on prod. |
| `cannot execute ... in a read-only transaction` | A write was attempted in a read session. Writes follow the non-prod write rule above, or the user gets the SQL. |

## Eval

`check/test_check_config.py` runs the config checker on the example and on one broken file per rule.

`check/test_guard.py` starts a throwaway Postgres (local binaries, or docker when the `postgres:16` image is already pulled). It creates a read-only role and a write-capable role, and asserts the guard returns 0 for the first and more than 0 for the second and for a superuser. With local binaries it also builds a two-database config and checks it with `check_config.py`. It connects to each environment through its `psql_service` or `psql_env` entry, and asserts the guard catches the one environment whose login can write. With neither available it prints SKIP and exits 0.

```bash
python3 "$SKILL_DIR"/check/test_check_config.py
python3 "$SKILL_DIR"/check/test_guard.py
```
