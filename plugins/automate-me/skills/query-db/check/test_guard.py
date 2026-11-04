"""Eval for guard.sql: a read-only login reads 0, a write-capable login reads more than 0.

Run: python3 check/test_guard.py

With local binaries it also builds a two-database query-db.json (app through psql_service entries,
analytics through psql_env URLs), checks it with check_config.py, resolves every db+env the way the
skill does, and asserts the guard reads 0 on each read-only login and more than 0 on the one that can write.

Starts a throwaway Postgres from local binaries (initdb, pg_ctl, psql), or from docker when the
postgres:16 image is already pulled. Prints SKIP and exits 0 when neither is available.
"""
import glob
import json
import os
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "..", "guard.sql")
CHECK_CONFIG = os.path.join(HERE, "check_config.py")
READ_OPTS = "-c default_transaction_read_only=on -c statement_timeout=60s"
IMAGE = "postgres:16"

SETUP = """
CREATE SCHEMA app;
CREATE TABLE app.orders (id serial PRIMARY KEY, total numeric);
CREATE TABLE app.customers (id serial PRIMARY KEY, name text);
CREATE VIEW app.order_totals AS SELECT id, total FROM app.orders;
CREATE TABLE public.notes (id serial PRIMARY KEY, body text);
CREATE ROLE ro_user LOGIN;
GRANT USAGE ON SCHEMA app TO ro_user;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO ro_user;
GRANT SELECT ON public.notes TO ro_user;
CREATE ROLE rw_user LOGIN;
GRANT USAGE ON SCHEMA app TO rw_user;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO rw_user;
GRANT INSERT, UPDATE ON app.orders TO rw_user;
CREATE ROLE trunc_user LOGIN;
GRANT TRUNCATE ON public.notes TO trunc_user;
"""

ANALYTICS = """
CREATE TABLE page_views (id bigserial PRIMARY KEY, path text);
GRANT SELECT ON page_views TO ro_user;
GRANT SELECT, INSERT ON page_views TO rw_user;
"""


def skip(why):
    print(f"SKIP guard eval: {why}")
    sys.exit(0)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_bin(name):
    found = shutil.which(name)
    if found:
        return found
    hits = sorted(glob.glob(f"/usr/lib/postgresql/*/bin/{name}") + glob.glob(f"/usr/local/pgsql/bin/{name}"))
    return hits[-1] if hits else None


class Local:
    """Postgres from local binaries in a temp dir. As root, runs it as the postgres OS user."""

    def __init__(self):
        self.initdb, self.pg_ctl, self.psql_bin = find_bin("initdb"), find_bin("pg_ctl"), find_bin("psql")
        if not (self.initdb and self.pg_ctl and self.psql_bin):
            raise RuntimeError("no initdb/pg_ctl/psql")
        self.prefix = []
        self.tmp = tempfile.mkdtemp(prefix="guard-pg-")
        if os.geteuid() == 0:
            try:
                pw = pwd.getpwnam("postgres")
            except KeyError:
                raise RuntimeError("running as root and no postgres OS user")
            os.chown(self.tmp, pw.pw_uid, pw.pw_gid)
            self.prefix = ["runuser", "-u", "postgres", "--"] if shutil.which("runuser") else None
            if self.prefix is None:
                raise RuntimeError("running as root and no runuser")
        self.data = os.path.join(self.tmp, "data")
        self.port = free_port()

    def run(self, *args, **kw):
        return subprocess.run([*self.prefix, *args], capture_output=True, text=True, timeout=60, **kw)

    def start(self):
        r = self.run(self.initdb, "-D", self.data, "-A", "trust", "-U", "postgres")
        if r.returncode:
            raise RuntimeError("initdb failed: " + r.stderr[-400:])
        opts = f"-k {self.tmp} -p {self.port} -c listen_addresses=''"
        r = self.run(self.pg_ctl, "-D", self.data, "-o", opts, "-l", os.path.join(self.tmp, "log"), "-w", "start")
        if r.returncode:
            raise RuntimeError("pg_ctl start failed: " + r.stderr[-400:])

    def psql(self, user, sql=None, file=None):
        args = [self.psql_bin, "-h", self.tmp, "-p", str(self.port), "-U", user, "-d", "postgres",
                "-X", "-At", "-v", "ON_ERROR_STOP=1"]
        if file:  # piped on stdin: the server user may not be able to read the checkout's path
            return self.run(*args, "-f", "-", input=open(file).read())
        return self.run(*args, "-c", sql)

    def conn(self, conninfo, sql=None, file=None, env=None):
        """psql on a libpq conninfo, the way the skill runs a psql_service or psql_env connection."""
        args = [self.psql_bin, conninfo, "-X", "-At", "-v", "ON_ERROR_STOP=1"]
        env = dict(os.environ, **(env or {}))
        if file:
            return self.run(*args, "-f", "-", input=open(file).read(), env=env)
        return self.run(*args, "-c", sql, env=env)

    def stop(self):
        self.run(self.pg_ctl, "-D", self.data, "-m", "immediate", "stop")
        shutil.rmtree(self.tmp, ignore_errors=True)


class Docker:
    """Postgres in a throwaway container. Never pulls: the image must already be present."""

    def __init__(self):
        if not shutil.which("docker"):
            raise RuntimeError("no docker")
        r = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=20)
        if r.returncode:
            raise RuntimeError(f"docker image {IMAGE} not present")
        self.name = f"guard-eval-{os.getpid()}"

    def start(self):
        r = subprocess.run(["docker", "run", "-d", "--rm", "--name", self.name,
                            "-e", "POSTGRES_HOST_AUTH_METHOD=trust", IMAGE],
                           capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise RuntimeError("docker run failed: " + r.stderr[-400:])
        for _ in range(60):
            if self.psql("postgres", "SELECT 1").returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError("container Postgres did not come up")

    def psql(self, user, sql=None, file=None):
        if file:
            sql = open(file).read()
        return subprocess.run(["docker", "exec", "-i", self.name, "psql", "-U", user, "-d", "postgres",
                               "-X", "-At", "-v", "ON_ERROR_STOP=1"],
                              input=sql, capture_output=True, text=True, timeout=60)

    def stop(self):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True, timeout=60)


def two_databases(db):
    """A query-db.json with two databases, each env resolved and guarded the way the skill does it."""
    fails = []
    r = db.psql("postgres", "CREATE DATABASE analytics")
    if r.returncode:
        return ["create analytics failed: " + r.stderr]
    r = db.conn(f"host={db.tmp} port={db.port} user=postgres dbname=analytics", ANALYTICS)
    if r.returncode:
        return ["analytics setup failed: " + r.stderr]

    services = os.path.join(db.tmp, "pg_service.conf")
    with open(services, "w") as f:
        for name, user in (("app_staging_ro", "ro_user"), ("app_prod_ro", "ro_user"), ("app_staging_rw", "rw_user")):
            f.write(f"[{name}]\nhost={db.tmp}\nport={db.port}\nuser={user}\ndbname=postgres\n\n")
    os.chmod(services, 0o644)
    urls = {"ANALYTICS_STAGING_URL": f"postgresql://ro_user@/analytics?host={db.tmp}&port={db.port}",
            "ANALYTICS_PROD_URL": f"postgresql://rw_user@/analytics?host={db.tmp}&port={db.port}"}
    cfg = {"databases": {
        "app": {"engine": "postgres", "tenant_column": "account_id", "allow_writes_on": ["staging"],
                "environments": {
                    "staging": {"default": True, "connect": {"psql_service": "app_staging_ro"},
                                "write_connect": {"psql_service": "app_staging_rw"}},
                    "prod": {"prod": True, "connect": {"psql_service": "app_prod_ro"}}}},
        "analytics": {"engine": "postgres", "large_tables": ["page_views"],
                      "environments": {
                          "staging": {"default": True, "connect": {"psql_env": "ANALYTICS_STAGING_URL"}},
                          "prod": {"prod": True, "connect": {"psql_env": "ANALYTICS_PROD_URL"}}}}}}
    proj = tempfile.mkdtemp(prefix="guard-proj-")
    os.makedirs(os.path.join(proj, ".claude"))
    path = os.path.join(proj, ".claude", "query-db.json")
    with open(path, "w") as f:
        json.dump(cfg, f)
    r = subprocess.run([sys.executable, CHECK_CONFIG, path], capture_output=True, text=True)
    if r.returncode:
        fails.append("two-database config does not pass check_config.py:\n" + r.stdout)
    shutil.rmtree(proj, ignore_errors=True)

    # analytics prod points at a login that can write: the guard must catch it.
    want = {("app", "staging"): 0, ("app", "prod"): 0, ("analytics", "staging"): 0, ("analytics", "prod"): "many"}
    for (name, env), expected in want.items():
        connect = cfg["databases"][name]["environments"][env]["connect"]
        env_vars = {"PGSERVICEFILE": services, "PGOPTIONS": READ_OPTS}
        if "psql_service" in connect:
            conninfo = f"service={connect['psql_service']}"
        else:
            conninfo = urls[connect["psql_env"]]
        r = db.conn(conninfo, file=GUARD, env=env_vars)
        out = r.stdout.strip()
        if r.returncode or not out.isdigit():
            fails.append(f"{name} {env}: guard did not return a count: {out!r} {r.stderr.strip()}")
            continue
        n = int(out)
        print(f"{name} {env}: writable_tables={n}")
        if (expected == 0) != (n == 0):
            fails.append(f"{name} {env}: unexpected writable_tables={n}")
    return fails


def main():
    db, reasons = None, []
    for kind in (Local, Docker):
        candidate = None
        try:
            candidate = kind()
            candidate.start()
            db = candidate
            break
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
            reasons.append(f"{kind.__name__}: {e}")
            if candidate is not None:
                candidate.stop()
    if db is None:
        skip("; ".join(reasons))

    fails = []
    try:
        r = db.psql("postgres", SETUP)
        if r.returncode:
            fails.append("setup failed: " + r.stderr)
        else:
            want = {"ro_user": lambda n: n == 0, "rw_user": lambda n: n > 0,
                    "trunc_user": lambda n: n > 0, "postgres": lambda n: n > 0}
            for user, ok in want.items():
                r = db.psql(user, file=GUARD)
                out = r.stdout.strip()
                if r.returncode or not out.isdigit():
                    fails.append(f"{user}: guard did not return a count: {out!r} {r.stderr.strip()}")
                    continue
                n = int(out)
                print(f"{user}: writable_tables={n}")
                if not ok(n):
                    fails.append(f"{user}: unexpected writable_tables={n}")
            if isinstance(db, Local):
                fails += two_databases(db)
            else:
                print("SKIP two-database config: needs local Postgres binaries")
    finally:
        db.stop()

    if fails:
        print("FAIL guard eval")
        for f in fails:
            print("  " + f)
        sys.exit(1)
    print(f"PASS guard eval ({type(db).__name__})")


if __name__ == "__main__":
    main()
