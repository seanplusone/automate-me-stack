"""Tests for detect.py against cases/sample-project, plus small one-file projects.

Run: python3 check/test_detect.py

Copies the fixture to a temp dir and makes it a git repo there (main branch, an origin remote with a
token in its URL, origin/HEAD set), with a fake HOME holding a ~/.pg_service.conf and a PATH that has
only a stub acli and git. Asserts every detected value and its source, and that no secret value from
the fixture's .env.example, docker-compose.yml, .mcp.json, remote URL or service file is printed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
DETECT = os.path.join(SKILL, "detect.py")
FIXTURE = os.path.join(SKILL, "cases", "sample-project")
SECRETS = ["compose-fake-secret-123", "envfile-fake-secret-456", "envfile-fake-secret-789", "envfile-fake-secret-000",
           "mcp-fake-secret-aaa", "mcp-fake-secret-bbb", "remote-fake-secret", "pgservice-fake-secret"]
FAILS = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        FAILS.append(name)
        if detail:
            print("    " + str(detail).replace("\n", "\n    "))


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "init.defaultBranch=main",
                    *args], cwd=cwd, check=True, capture_output=True, timeout=30)


def run_detect(project, env):
    r = subprocess.run([sys.executable, DETECT, project], capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, r.stdout, r.stderr


def pairs(items):
    return [(i["value"], i["source"]) for i in items]


def test_sample_project(tmp):
    project = os.path.join(tmp, "demo-shop")
    shutil.copytree(FIXTURE, project)
    git(project, "init", "-q", "-b", "main")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "initial")
    git(project, "remote", "add", "origin", "https://ci-user:remote-fake-secret@github.com/acme/demo-shop.git")
    git(project, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(project, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

    home = os.path.join(tmp, "home")
    os.makedirs(home)
    with open(os.path.join(home, ".pg_service.conf"), "w") as f:
        f.write("[shop_staging_ro]\nhost=localhost\nport=5433\nuser=shop_ro\npassword=pgservice-fake-secret\n\n"
                "[shop_prod_ro]\nhost=db.example.com\nuser=shop_ro\n")
    fakebin = os.path.join(tmp, "bin")
    os.makedirs(fakebin)
    acli = os.path.join(fakebin, "acli")
    with open(acli, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(acli, 0o755)
    os.symlink(shutil.which("git"), os.path.join(fakebin, "git"))
    env = {k: v for k, v in os.environ.items() if k not in ("PGSERVICEFILE",)}
    env.update(HOME=home, PATH=fakebin)

    code, out, err = run_detect(project, env)
    check("sample: exits 0 and prints JSON", code == 0, err)
    try:
        d = json.loads(out)
    except ValueError:
        check("sample: output is JSON", False, out)
        return

    check("sample: project path", d["project"] == os.path.abspath(project), d["project"])
    check("sample: base remote", pairs(d["base_remote"]) == [("origin", "git remote")], d["base_remote"])
    check("sample: default branch from origin/HEAD",
          pairs(d["default_branch"]) == [("main", "git symbolic-ref refs/remotes/origin/HEAD")], d["default_branch"])
    check("sample: remote URL without its token",
          pairs(d["remote_url"]) == [("https://github.com/acme/demo-shop.git", "git remote get-url origin")], d["remote_url"])
    check("sample: tracker hints", pairs(d["tracker"]) == [
        ({"tracker": "Jira (acli)", "via": "acli"}, "PATH: acli"),
        ({"tracker": "GitHub Issues", "via": "MCP server github"}, ".mcp.json: mcpServers.github"),
        ({"tracker": "GitHub Issues", "via": "the repo's GitHub remote"}, "git remote get-url origin"),
    ], d["tracker"])
    check("sample: test commands", pairs(d["tests"]) == [
        ("npm test", "package.json: scripts.test"), ("make test", "Makefile: test target")], d["tests"])
    check("sample: app URLs", pairs(d["app_urls"]) == [
        ("http://localhost:5174", "package.json: scripts.dev"),
        ("http://localhost:8080", "docker-compose.yml: services.web.ports; .env.example: APP_URL"),
    ], d["app_urls"])
    check("sample: databases", pairs(d["databases"]) == [
        ({"kind": "compose_service", "name": "db", "image": "postgres:16", "host_port": 5433}, "docker-compose.yml: services.db"),
        ({"kind": "env_var", "name": "DATABASE_URL"}, ".env.example"),
        ({"kind": "env_var", "name": "ANALYTICS_DATABASE_URL"}, ".env.example"),
        ({"kind": "mcp_server", "name": "shop-db"}, ".mcp.json: mcpServers.shop-db"),
        ({"kind": "pg_service", "name": "shop_staging_ro"}, "~/.pg_service.conf"),
        ({"kind": "pg_service", "name": "shop_prod_ro"}, "~/.pg_service.conf"),
    ], d["databases"])
    check("sample: MCP servers", pairs(d["mcp_servers"]) == [
        ("github", ".mcp.json: mcpServers.github"), ("shop-db", ".mcp.json: mcpServers.shop-db")], d["mcp_servers"])
    check("sample: existing config", pairs(d["existing_config"]) == [("mcp_servers", ".mcp.json")], d["existing_config"])
    check("sample: literal secrets in .mcp.json, by name only", pairs(d["mcp_literal_secrets"]) == [
        ({"server": "github", "env": "GITHUB_PERSONAL_ACCESS_TOKEN"}, ".mcp.json: mcpServers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN"),
        ({"server": "shop-db", "env": "DATABASE_URI"}, ".mcp.json: mcpServers.shop-db.env.DATABASE_URI"),
    ], d["mcp_literal_secrets"])
    check("sample: compose container names use the folder as project", pairs(d["compose_containers"]) == [
        ("demo-shop-db-1", "docker-compose.yml: services.db (project demo-shop)"),
        ("demo-shop-web-1", "docker-compose.yml: services.web (project demo-shop)"),
        ("demo-shop-cache-1", "docker-compose.yml: services.cache (project demo-shop)"),
    ], d["compose_containers"])
    leaked = [s for s in SECRETS if s in out or s in err]
    check("sample: no secret value printed", not leaked, leaked)
    check("sample: no redis or cache URL", "6380" not in out, out)

    # Existing automate-me config is listed once it is there.
    os.makedirs(os.path.join(project, ".claude"))
    for rel in ("project-profile.md", "query-db.json", "query-db.md", "verify-web.yaml"):
        open(os.path.join(project, ".claude", rel), "w").close()
    d = json.loads(run_detect(project, env)[1])
    check("sample: existing config files", pairs(d["existing_config"]) == [
        ("project_profile", ".claude/project-profile.md"), ("query_db", ".claude/query-db.json"),
        ("query_db_old_markdown", ".claude/query-db.md"), ("verify_web", ".claude/verify-web.yaml"),
        ("mcp_servers", ".mcp.json")], d["existing_config"])


def small(tmp, name, files):
    d = os.path.join(tmp, name)
    os.makedirs(d)
    for rel, text in files.items():
        with open(os.path.join(d, rel), "w") as f:
            f.write(text)
    env = dict(os.environ, HOME=os.path.join(tmp, "nohome"), PATH=os.path.join(tmp, "emptybin"))
    env.pop("PGSERVICEFILE", None)
    code, out, err = run_detect(d, env)
    return json.loads(out) if code == 0 else {"error": err}


def test_remote_query_string(tmp):
    project = os.path.join(tmp, "qs")
    os.makedirs(project)
    git(project, "init", "-q", "-b", "main")
    git(project, "commit", "-q", "--allow-empty", "-m", "initial")
    git(project, "remote", "add", "upstream", "https://github.com/acme/demo-shop.git?token=query-fake-secret#frag-fake-secret")
    git(project, "remote", "add", "origin", "ssh://me:ssh-fake-secret@git.example.com/me/demo-shop.git")
    env = dict(os.environ, HOME=os.path.join(tmp, "nohome"), PATH=os.path.dirname(shutil.which("git")))
    env.pop("PGSERVICEFILE", None)
    code, out, err = run_detect(project, env)
    d = json.loads(out)
    check("remote: upstream wins over origin", pairs(d["base_remote"]) == [("upstream", "git remote")], d)
    check("remote: query string and fragment are stripped", pairs(d["remote_url"]) == [
        ("https://github.com/acme/demo-shop.git", "git remote get-url upstream")], d)
    check("remote: default branch from the local branch", pairs(d["default_branch"]) == [
        ("main", "git branch (local branch name)")], d)
    check("remote: no secret printed", not any(x in out + err for x in ("query-fake-secret", "frag-fake-secret", "ssh-fake-secret")), out)
    sys.path.insert(0, SKILL)
    import detect  # noqa: E402
    check("clean_url strips userinfo too", detect.clean_url("ssh://me:pw@h/x.git?t=1") == "ssh://h/x.git")


def test_small(tmp):
    d = small(tmp, "go", {"go.mod": "module example.com/demo\n"})
    check("go.mod gives go test", pairs(d["tests"]) == [("go test ./...", "go.mod")], d)
    check("not a git repo gives empty git lists", d["default_branch"] == [] and d["base_remote"] == [], d)
    d = small(tmp, "rust", {"Cargo.toml": "[package]\nname = \"demo\"\n"})
    check("Cargo.toml gives cargo test", pairs(d["tests"]) == [("cargo test", "Cargo.toml")], d)
    d = small(tmp, "py", {"pyproject.toml": "[tool.pytest.ini_options]\naddopts = \"-q\"\n"})
    check("pyproject pytest section gives pytest", pairs(d["tests"]) == [("pytest", "pyproject.toml")], d)
    d = small(tmp, "pyini", {"pytest.ini": "[pytest]\n"})
    check("pytest.ini gives pytest", pairs(d["tests"]) == [("pytest", "pytest.ini")], d)
    d = small(tmp, "pnpm", {"package.json": json.dumps({"scripts": {"test": "jest", "dev": "next dev"}}),
                            "pnpm-lock.yaml": ""})
    check("pnpm lockfile gives pnpm test", pairs(d["tests"]) == [("pnpm test", "package.json: scripts.test")], d)
    check("next dev gives its default port", pairs(d["app_urls"]) == [
        ("http://localhost:3000", "package.json: scripts.dev (next dev default port)")], d)
    d = small(tmp, "npm-default", {"package.json": json.dumps({"scripts": {
        "test": "echo \"Error: no test specified\" && exit 1"}})})
    check("npm's placeholder test script is skipped", d["tests"] == [], d)
    d = small(tmp, "envport", {".env": "PORT=4000\nAPP_URL=https://admin:envport-secret@app.example.com\n"
                                        "ORDERS_DB_URL=postgres://u:envport-secret@db/orders\nPGHOST=localhost\n"
                                        "PGPASSWORD=envport-secret\nDATABASE_URL_TOKEN=x\nSECRET_DB_URL=x\n"})
    check("PORT gives a URL, an APP_URL with a password is dropped",
          pairs(d["app_urls"]) == [("http://localhost:4000", ".env: PORT")], d)
    check("_DB_URL and PG* names are listed, PGPASSWORD and secret-like names are not", pairs(d["databases"]) == [
        ({"kind": "env_var", "name": "ORDERS_DB_URL"}, ".env"), ({"kind": "env_var", "name": "PGHOST"}, ".env")], d)
    check("no .env value leaks", "envport-secret" not in json.dumps(d), d)
    d = small(tmp, "compose-long", {"compose.yaml": "services:\n  api:\n    build: .\n    ports:\n"
                                                    "      - target: 8000\n        published: 9000\n"
                                                    "  pg:\n    image: postgis/postgis:16-3.4\n"})
    check("compose long port syntax", pairs(d["app_urls"]) == [("http://localhost:9000", "compose.yaml: services.api.ports")], d)
    check("postgis image counts as Postgres", pairs(d["databases"]) == [
        ({"kind": "compose_service", "name": "pg", "image": "postgis/postgis:16-3.4"}, "compose.yaml: services.pg")], d)
    d = small(tmp, "compose-named", {"docker-compose.yml": "name: Shop_Stack\nservices:\n  web:\n    build: .\n"
                                                          "  db:\n    image: postgres:16\n    container_name: shop-db\n"})
    check("compose name: and container_name: set the container names", pairs(d["compose_containers"]) == [
        ("shop_stack-web-1", "docker-compose.yml: services.web (project shop_stack)"),
        ("shop-db", "docker-compose.yml: services.db.container_name")], d)
    d = small(tmp, "mcp-refs", {".mcp.json": json.dumps({"mcpServers": {
        "pg": {"command": "uvx", "args": ["postgres-mcp", "postgresql://u:mcpargs-secret@h/db"],
               "env": {"DATABASE_URI": "${APP_RO_URL}"}},
        "api": {"type": "http", "url": "https://mcp.example.com", "headers": {"Authorization": "Bearer ${API_TOKEN}"}}}})})
    check("${VAR} references are fine, a password URL in args is flagged", pairs(d["mcp_literal_secrets"]) == [
        ({"server": "pg", "args": 1}, ".mcp.json: mcpServers.pg.args[1]")], d)
    check("no .mcp.json value leaks", "mcpargs-secret" not in json.dumps(d), d)
    d = small(tmp, "badjson", {"package.json": "{", ".mcp.json": "not json"})
    check("broken package.json and .mcp.json are skipped", d.get("tests") == [] and d.get("mcp_servers") == [], d)


if __name__ == "__main__":
    tmp = tempfile.mkdtemp(prefix="setup-detect-")
    try:
        test_sample_project(tmp)
        test_small(tmp)
        test_remote_query_string(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(os.path.join(SKILL, "__pycache__"), ignore_errors=True)
    print(f"\n{'FAIL' if FAILS else 'PASS'} test_detect ({len(FAILS)} failing)")
    sys.exit(1 if FAILS else 0)
