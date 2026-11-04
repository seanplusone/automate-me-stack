"""Check a project's .claude/query-db.json before query-db uses it.

Usage: python3 check/check_config.py <query-db.json>

Prints one FAIL or WARN line per problem, then PASS or FAIL, and exits 1 on FAIL. Fails on:
- a file that is not JSON, or has no databases;
- a field of the wrong type: default, prod and read_replica must be true or false, allow_writes_on,
  tenant_also and large_tables must be lists of names;
- a database with no environments, an unsupported engine, or more than one default environment
  (no default is allowed only when the database has one environment), or a default that is prod;
- an environment named like production (prod, production, prd) without "prod": true;
- a connect (or write_connect) that is not exactly one of mcp, psql_service, psql_env, command;
  a psql_service that is a URL; a psql_env that is not an env var name;
- allow_writes_on naming a prod environment, or one that does not exist; a write_connect on a prod
  environment or on one not in allow_writes_on;
- anything that looks like a secret: a key named like password, secret or token, a value holding
  password= or PGPASSWORD=, user:password@ (in a URL or not), a --password flag with a value, -p with
  a value that is not a port number, or -u user:password.
Warns (does not fail) on unknown keys, on a write environment with no write_connect, and on an mcp
name that the project's .mcp.json does not list.
"""
import json
import os
import re
import sys

ENGINES = {"postgres"}
CONNECT_KINDS = ("mcp", "psql_service", "psql_env", "command")
DB_KEYS = {"engine", "description", "environments", "tenant_column", "tenant_also", "large_tables",
           "allow_writes_on", "read_replica"}
ENV_KEYS = {"default", "prod", "connect", "write_connect", "description", "read_replica"}
BOOL_KEYS = ("default", "prod", "read_replica")
PROD_NAME = re.compile(r"(?:^|[^a-z0-9])(prod|production|prd)(?:$|[^a-z0-9])", re.I)
SECRET_KEY = re.compile(r"pass(word|wd)?$|password|secret|token|api_?key|credential", re.I)
SECRET_VALUE = [
    (re.compile(r"password\s*=", re.I), "holds password="),
    (re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@", re.I), "is a URL with user:password@"),
    (re.compile(r"(?:^|[\s'\"=(])[^\s/:@'\"=(]+:[^\s/@'\"]+@", re.I), "holds user:password@"),
    (re.compile(r"\bPGPASSWORD\s*=", re.I), "sets PGPASSWORD"),
    (re.compile(r"(?:^|\s)--?(?:password|passwd|pass|pw)(?:[= ]|\s+)\S+", re.I), "passes a password flag with a value"),
    (re.compile(r"(?:^|\s)-p\s*(?![0-9]+(?:\s|$))[^\s-]\S*"), "passes -p with a value that is not a port"),
    (re.compile(r"(?:^|\s)(?:-u|--user)[= ]?\s*[^\s:]+:\S+"), "passes -u user:password"),
]
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def find_secrets(node, where):
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if SECRET_KEY.search(str(k)):
                out.append(f"{where}.{k}: key looks like a secret; name where the secret lives, never the secret")
            out += find_secrets(v, f"{where}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += find_secrets(v, f"{where}[{i}]")
    elif isinstance(node, str):
        for rx, why in SECRET_VALUE:
            if rx.search(node):
                out.append(f"{where}: value {why}; keep secrets in ~/.pgpass, a service file or an env var")
                break
    return out


def check_connect(conn, where):
    if not isinstance(conn, dict):
        return [f"{where}: must be an object with exactly one of {', '.join(CONNECT_KINDS)}"]
    kinds = [k for k in conn if k in CONNECT_KINDS]
    extra = [k for k in conn if k not in CONNECT_KINDS]
    if len(kinds) != 1 or extra:
        got = ", ".join(conn) or "nothing"
        return [f"{where}: must be exactly one of {', '.join(CONNECT_KINDS)}; got {got}"]
    kind, value = kinds[0], conn[kinds[0]]
    if not isinstance(value, str) or not value.strip():
        return [f"{where}.{kind}: must be a non-empty string"]
    if kind == "psql_env" and not ENV_NAME.match(value):
        return [f"{where}.psql_env: must be the NAME of an env var that holds the URL, not the URL itself"]
    if kind == "psql_service" and (re.search(r"\s|=", value) or "://" in value):
        return [f"{where}.psql_service: must be a section name from ~/.pg_service.conf, not a URL or a conninfo"]
    return []


def mcp_servers(config_path):
    d = os.path.dirname(os.path.abspath(config_path))
    root = os.path.dirname(d) if os.path.basename(d) == ".claude" else d
    path = os.path.join(root, ".mcp.json")
    try:
        servers = json.load(open(path)).get("mcpServers") or {}
        return (set(servers.keys()) if isinstance(servers, dict) else set()), path
    except (OSError, ValueError, AttributeError):
        return None, path


def is_str_list(v, allow_dict=False):
    return isinstance(v, list) and all(isinstance(x, str) or (allow_dict and isinstance(x, dict)) for x in v)


def check_env(name, e, env, ew, servers, mcp_path, writable):
    fails, warns = [], []
    warns += [f"{ew}.{k}: unknown key" for k in env if k not in ENV_KEYS]
    for k in BOOL_KEYS:
        if k in env and not isinstance(env[k], bool):
            fails.append(f"{ew}.{k}: must be true or false, not {env[k]!r}")
    if "description" in env and not isinstance(env["description"], str):
        fails.append(f"{ew}.description: must be a string")
    prod = env.get("prod") is True
    if PROD_NAME.search(e) and not prod:
        fails.append(f"{ew}: the name looks like production but \"prod\" is not true; mark it \"prod\": true or rename it")
    looks_prod = prod or bool(PROD_NAME.search(e))
    if env.get("default") is True and looks_prod:
        fails.append(f"{ew}: a prod environment cannot be the default; prod is used only when named")
    if "connect" not in env:
        fails.append(f"{ew}: no connect")
    else:
        fails += check_connect(env["connect"], f"{ew}.connect")
    if "write_connect" in env:
        fails += check_connect(env["write_connect"], f"{ew}.write_connect")
        if looks_prod:
            fails.append(f"{ew}.write_connect: not allowed on a prod environment; prod writes are always refused")
        elif e not in writable:
            fails.append(f"{ew}.write_connect: {e!r} is not in allow_writes_on; add it there or remove write_connect")
    for key in ("connect", "write_connect"):
        conn = env.get(key)
        server = conn.get("mcp") if isinstance(conn, dict) else None
        if isinstance(server, str) and server and servers is not None and server not in servers:
            warns.append(f"{ew}.{key}.mcp: server {server!r} is not in {mcp_path}")
    return fails, warns, looks_prod


def check_db(name, db, servers, mcp_path):
    w = f"databases.{name}"
    if not isinstance(db, dict):
        return [f"{w}: must be an object"], []
    fails, warns = [], []
    warns += [f"{w}.{k}: unknown key" for k in db if k not in DB_KEYS]
    engine = db.get("engine")
    if not isinstance(engine, str) or engine not in ENGINES:
        fails.append(f"{w}.engine: {engine!r} is not supported; only \"postgres\" is supported now")
    for k in ("description", "tenant_column"):
        if k in db and not isinstance(db[k], str):
            fails.append(f"{w}.{k}: must be a string")
    if "read_replica" in db and not isinstance(db["read_replica"], bool):
        fails.append(f"{w}.read_replica: must be true or false")
    if "tenant_also" in db and not is_str_list(db["tenant_also"]):
        fails.append(f"{w}.tenant_also: must be a list of column names")
    if "large_tables" in db and not is_str_list(db["large_tables"], allow_dict=True):
        fails.append(f"{w}.large_tables: must be a list of table names")
    writes = db.get("allow_writes_on", [])
    if not is_str_list(writes):
        fails.append(f"{w}.allow_writes_on: must be a list of environment names (strings)")
        writes = [x for x in writes if isinstance(x, str)] if isinstance(writes, list) else []
    envs = db.get("environments")
    if not isinstance(envs, dict) or not envs:
        fails.append(f"{w}: no environments")
        return fails, warns
    defaults = [e for e, v in envs.items() if isinstance(v, dict) and v.get("default") is True]
    if len(defaults) > 1:
        fails.append(f"{w}: more than one default environment: {', '.join(defaults)}")
    if not defaults and len(envs) > 1:
        fails.append(f"{w}: {len(envs)} environments and none is marked \"default\": true")
    prod_envs = set()
    for e, env in envs.items():
        ew = f"{w}.environments.{e}"
        if not isinstance(env, dict):
            fails.append(f"{ew}: must be an object")
            continue
        f, wn, looks_prod = check_env(name, e, env, ew, servers, mcp_path, writes)
        fails += f
        warns += wn
        if looks_prod:
            prod_envs.add(e)
    for e in writes:
        env = envs.get(e)
        if env is None:
            fails.append(f"{w}.allow_writes_on: {e!r} is not one of its environments")
        elif e in prod_envs:
            fails.append(f"{w}.allow_writes_on: {e!r} is prod; prod writes are always refused")
        elif isinstance(env, dict) and "write_connect" not in env:
            warns.append(f"{w}.allow_writes_on: {e!r} has no write_connect, so writes there are handed to you as SQL")
    return fails, warns


def check(path):
    """Returns (fails, warns)."""
    try:
        cfg = json.load(open(path))
    except OSError as e:
        return [f"cannot read {path}: {e.strerror}"], []
    except ValueError as e:
        return [f"not valid JSON: {e}"], []
    if not isinstance(cfg, dict) or not isinstance(cfg.get("databases"), dict) or not cfg["databases"]:
        return ['no databases: the file needs {"databases": {"<name>": {...}}}'], []
    fails, warns = find_secrets(cfg, "$"), []
    servers, mcp_path = mcp_servers(path)
    for name, db in cfg["databases"].items():
        f, w = check_db(name, db, servers, mcp_path)
        fails += f
        warns += w
    return fails, warns


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2])
        return 2
    try:
        fails, warns = check(argv[1])
    except Exception as e:  # a malformed file must give a FAIL line, never a traceback
        fails, warns = [f"could not check the file: {type(e).__name__}: {e}"], []
    for f in fails:
        print(f"FAIL  {f}")
    for x in warns:
        print(f"WARN  {x}")
    print(f"{'FAIL' if fails else 'PASS'} query-db config {argv[1]}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
