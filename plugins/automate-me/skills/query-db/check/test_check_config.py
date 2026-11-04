"""Run: python3 check/test_check_config.py"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_config.py")
EXAMPLE = os.path.join(HERE, "..", "query-db.example.json")
TMP = tempfile.mkdtemp(prefix="query-db-config-")
FAILS = []


def run(path):
    r = subprocess.run([sys.executable, CHECK, path], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def write(name, data, raw=False):
    d = os.path.join(TMP, name, ".claude")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "query-db.json")
    with open(path, "w") as f:
        f.write(data if raw else json.dumps(data, indent=2))
    return path


def expect(name, cond, out):
    print(f"{'PASS' if cond else 'FAIL'} {name}")
    if not cond:
        FAILS.append(f"{name}\n{out}")


def base():
    return copy.deepcopy(json.load(open(EXAMPLE)))


def fails_with(name, cfg, needle, raw=False):
    code, out = run(write(name, cfg, raw))
    expect(name, code == 1 and needle in out, out)


code, out = run(EXAMPLE)
expect("example passes", code == 0 and "PASS" in out and "FAIL" not in out, out)

one = {"databases": {"app": {"engine": "postgres", "environments": {"local": {"connect": {"psql_service": "app_local"}}}}}}
code, out = run(write("single env, no default", one))
expect("single env with no default passes", code == 0, out)

fails_with("invalid JSON", '{"databases": {', "not valid JSON", raw=True)
fails_with("no databases key", {"servers": {}}, "no databases")
fails_with("empty databases", {"databases": {}}, "no databases")

c = base(); c["databases"]["app"]["environments"] = {}
fails_with("db with no environments", c, "databases.app: no environments")

c = base(); c["databases"]["analytics"]["environments"]["prod"]["default"] = False
c["databases"]["analytics"]["environments"]["qa"] = {"default": True, "connect": {"psql_env": "QA_URL"}}
fails_with("two defaults", c, "more than one default environment: staging, qa")

c = base(); del c["databases"]["app"]["environments"]["staging"]["default"]
fails_with("two envs, no default", c, "none is marked")

c = base(); c["databases"]["app"]["environments"]["prod"]["default"] = True
del c["databases"]["app"]["environments"]["staging"]["default"]
fails_with("prod as default", c, "prod environment cannot be the default")

c = base(); c["databases"]["analytics"]["engine"] = "mysql"
fails_with("unknown engine", c, "only \"postgres\" is supported now")

c = base(); del c["databases"]["analytics"]["engine"]
fails_with("missing engine", c, "is not supported")

for label, conn in (("two kinds", {"mcp": "a", "psql_service": "b"}),
                    ("no kind", {}),
                    ("unknown kind", {"url": "postgres://localhost/app"}),
                    ("not an object", "app-staging-ro")):
    c = base(); c["databases"]["app"]["environments"]["staging"]["connect"] = conn
    fails_with(f"connect {label}", c, "must be")

c = base(); del c["databases"]["app"]["environments"]["staging"]["connect"]
fails_with("missing connect", c, "no connect")

c = base(); c["databases"]["app"]["environments"]["staging"]["connect"] = {"mcp": ""}
fails_with("empty connect value", c, "non-empty string")

c = base(); c["databases"]["analytics"]["environments"]["staging"]["connect"] = {"psql_env": "postgres://localhost/a"}
fails_with("psql_env holding a URL", c, "NAME of an env var")

c = base(); c["databases"]["app"]["environments"]["staging"]["write_connect"] = {"mcp": "x", "command": "y"}
fails_with("bad write_connect", c, "write_connect: must be exactly one")

c = base(); c["databases"]["app"]["allow_writes_on"] = ["staging", "prod"]
fails_with("prod in allow_writes_on", c, "'prod' is prod")

c = base(); c["databases"]["app"]["allow_writes_on"] = ["qa"]
fails_with("unknown env in allow_writes_on", c, "'qa' is not one of its environments")

c = base(); c["databases"]["app"]["environments"]["prod"]["connect"] = {"command": "psql 'host=db password=hunter2'"}
fails_with("password= in a value", c, "holds password=")

c = base(); c["databases"]["app"]["environments"]["prod"]["connect"] = {"command": "echo postgres://ro:hunter2@db/app"}
fails_with("URL with user:pass@", c, "user:password@")

for key in ("password", "db_secret", "token", "API_KEY"):
    c = base(); c["databases"]["app"]["environments"]["prod"][key] = "x"
    fails_with(f"secret-looking key {key}", c, f"{key}: key looks like a secret")

c = base(); c["databases"]["app"]["environments"]["staging"]["connect"] = {"psql_env": "APP_URL"}
c["databases"]["app"]["description"] = "postgres://ro@db/app, no password in it"
code, out = run(write("URL without password", c))
expect("a URL without a password passes", code == 0, out)

# Warnings do not fail: an unknown key, a write env with no write_connect, an mcp name not in .mcp.json.
c = base(); c["databases"]["app"]["colour"] = "blue"
del c["databases"]["app"]["environments"]["staging"]["write_connect"]
path = write("warnings", c)
with open(os.path.join(os.path.dirname(os.path.dirname(path)), ".mcp.json"), "w") as f:
    json.dump({"mcpServers": {"github": {"command": "gh-mcp"}}}, f)
code, out = run(path)
expect("warnings do not fail", code == 0 and out.count("WARN") == 3 and "'app-staging-ro' is not in" in out
       and "colour: unknown key" in out and "has no write_connect" in out, out)

# --- Round 2: adversarial configs from the independent verifier, and the rules added for them ---

def no_traceback(name, cfg, needle):
    code, out = run(write(name, cfg))
    expect(name, code == 1 and needle in out and "Traceback" not in out, out)


c = base(); c["databases"]["app"]["allow_writes_on"] = [["prod"]]
no_traceback("allow_writes_on with a nested list fails without a crash", c, "must be a list of environment names")
c = base(); c["databases"]["app"]["allow_writes_on"] = [1]
no_traceback("allow_writes_on with a number fails", c, "must be a list of environment names")
c = base(); c["databases"]["app"]["allow_writes_on"] = "staging"
no_traceback("allow_writes_on as a string fails", c, "must be a list of environment names")
c = base(); c["databases"]["app"]["allow_writes_on"] = ["Prod"]
fails_with("allow_writes_on with a wrong-case name fails", c, "'Prod' is not one of its environments")
c = base(); c["databases"]["app"]["allow_writes_on"] = ["prod"]
fails_with("allow_writes_on prod (flagged) fails", c, "'prod' is prod")

# Prod by name: an env named prod/production/prd must carry "prod": true.
for env_name in ("prod", "production", "PRD", "prod-eu", "us_production"):
    c = base(); envs = c["databases"]["app"]["environments"]
    del envs["prod"]
    envs[env_name] = {"connect": {"psql_service": "x"}}
    fails_with(f"env named {env_name} without prod: true", c, "name looks like production")
c = base(); del c["databases"]["app"]["environments"]["prod"]["prod"]
c["databases"]["app"]["allow_writes_on"] = ["staging", "prod"]
fails_with("unflagged prod-named env in allow_writes_on", c, "'prod' is prod")
c = base(); envs = c["databases"]["app"]["environments"]
del envs["staging"]["default"]; del envs["prod"]["prod"]; envs["prod"]["default"] = True
fails_with("unflagged prod-named env as default", c, "prod environment cannot be the default")
c = base(); c["databases"]["app"]["environments"]["prod"]["prod"] = False
fails_with("prod-named env with prod: false", c, "name looks like production")
c = base(); c["databases"]["app"]["environments"]["staging"]["description"] = "staging, a copy of prod data"
code, out = run(write("prod in a description", c))
expect("prod in a description is not a prod name", code == 0, out)
c = base(); c["databases"]["app"]["environments"]["product-demo"] = {"connect": {"mcp": "x"}}
code, out = run(write("product-demo env", c))
expect("an env named product-demo is not prod", code == 0, out)

# Booleans must be real booleans.
for key, value in (("prod", "true"), ("prod", 1), ("default", "yes"), ("read_replica", "false")):
    c = base(); c["databases"]["analytics"]["environments"]["prod"][key] = value
    fails_with(f"{key}: {value!r} is not a boolean", c, f"{key}: must be true or false")
c = base(); c["databases"]["analytics"]["environments"]["qa"] = {"prod": "true", "connect": {"mcp": "q"}}
c["databases"]["analytics"]["allow_writes_on"] = ["qa"]
fails_with("string prod flag in allow_writes_on", c, "prod: must be true or false")

# Other field types.
for key, value, needle in (("tenant_column", ["a"], "tenant_column: must be a string"),
                           ("tenant_also", "store_id", "tenant_also: must be a list"),
                           ("tenant_also", [1], "tenant_also: must be a list"),
                           ("large_tables", "events", "large_tables: must be a list"),
                           ("description", 5, "description: must be a string"),
                           ("engine", ["postgres"], "is not supported")):
    c = base(); c["databases"]["app"][key] = value
    no_traceback(f"{key} = {value!r} fails", c, needle)
for label, cfg, needle in (("environments as a list", {"databases": {"a": {"engine": "postgres", "environments": []}}}, "no environments"),
                           ("env is null", {"databases": {"a": {"engine": "postgres", "environments": {"x": None}}}}, "must be an object"),
                           ("top-level list", [1, 2], "no databases"),
                           ("db is a string", {"databases": {"a": "postgres"}}, "must be an object")):
    no_traceback(label, cfg, needle)

# write_connect only on a non-prod env listed in allow_writes_on.
c = base(); c["databases"]["app"]["environments"]["prod"]["write_connect"] = {"psql_service": "app_prod_rw"}
fails_with("write_connect on prod (not in allow_writes_on)", c, "write_connect: not allowed on a prod environment")
c = base(); c["databases"]["app"]["environments"]["prod"]["write_connect"] = {"psql_service": "app_prod_rw"}
c["databases"]["app"]["allow_writes_on"] = ["staging", "prod"]
fails_with("write_connect on prod in allow_writes_on", c, "not allowed on a prod environment")
c = base(); c["databases"]["app"]["allow_writes_on"] = []
fails_with("write_connect on an env not in allow_writes_on", c, "'staging' is not in allow_writes_on")
c = base(); del c["databases"]["app"]["allow_writes_on"]
fails_with("write_connect with no allow_writes_on", c, "'staging' is not in allow_writes_on")

# Secrets in commands and service names.
for label, conn, needle in (
        ("--password flag", {"command": "mydb-url --password hunter2"}, "password flag"),
        ("--password= flag", {"command": "mydb-url --password=hunter2"}, "password"),
        ("-p with a password", {"command": "mysql-url -p hunter2"}, "-p with a value"),
        ("-p glued password", {"command": "mysql-url -phunter2"}, "-p with a value"),
        ("curl -u user:pass", {"command": "curl -u admin:hunter2 https://vault.example.com/db"}, "-u user:password"),
        ("user:pass@ without a scheme", {"command": "db-tunnel admin:hunter2@bastion"}, "user:password@"),
        ("PGPASSWORD=", {"command": "PGPASSWORD=x psql-url"}, "PGPASSWORD"),
        ("URL with password", {"command": "echo postgres://u:p@h/db"}, "user:password@"),
        ("psql_service URL with password", {"psql_service": "postgres://u:p@h/db"}, "user:password@"),
        ("psql_service URL without password", {"psql_service": "postgres://u@h/db"}, "not a URL"),
        ("psql_env holding a URL", {"psql_env": "postgres://u@h/db"}, "NAME of an env var"),
        ("mcp + psql_env", {"mcp": "a", "psql_env": "B"}, "exactly one"),
        ("mcp + password key", {"mcp": "a", "password": "x"}, "key looks like a secret")):
    c = base(); c["databases"]["analytics"]["environments"]["prod"]["connect"] = conn
    fails_with(f"connect {label}", c, needle)
c = base(); c["databases"]["app"]["api_key"] = "x"
fails_with("api_key at db level", c, "api_key: key looks like a secret")
c = base(); c["databases"]["app"]["description"] = "read at postgres://u:hunter2@h/db"
fails_with("password URL in a description", c, "user:password@")

# Commands that only look close to a secret still pass.
for cmd in ("psql-url -p 5432 analytics", "ssh -N -L 15432:db.internal:5432 deploy@bastion && echo url",
            "demo-shop-db-url analytics-prod", "aws ssm start-session --target i-0abc --document-name pf"):
    c = base(); c["databases"]["analytics"]["environments"]["prod"]["connect"] = {"command": cmd}
    code, out = run(write("ok command", c))
    expect(f"command {cmd!r} passes", code == 0, out)
c = base(); c["databases"]["analytics"]["environments"] = {"prod": {"prod": True, "connect": {"psql_service": "a_prod"}}}
code, out = run(write("single prod env", c))
expect("a single prod env with no default passes", code == 0, out)

shutil.rmtree(TMP, ignore_errors=True)
if FAILS:
    print("FAIL test_check_config")
    for f in FAILS:
        print("  " + f.replace("\n", "\n    "))
    sys.exit(1)
print("PASS test_check_config")
