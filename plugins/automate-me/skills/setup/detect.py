#!/usr/bin/env python3
"""Detect what automate-me's setup can infer about a project. Read-only, Python stdlib only.

Usage: python3 detect.py [<project dir>]     (default: the current directory)

Prints one JSON object. Every key except "project" holds a list of {"value": ..., "source": ...}
items, where source names the file (or command) the value came from; a value found in several places
lists each source, separated by "; ". Nothing found gives an empty list.

It never prints a secret. From .env files and .mcp.json it reports names only: an env var's name, an
MCP server's name. The only .env values it reads are PORT and APP_URL, and an APP_URL with a
user:password@ part is dropped. A git remote URL loses any user:password@ part, query string and
fragment. Env var names that look like secrets (PASS, SECRET, TOKEN) are not offered as databases.
"mcp_literal_secrets" lists the .mcp.json env, headers or args entries that hold a literal value instead
of a ${VAR} reference, by server and key name only, so setup can warn about them.
"""
import configparser
import json
import os
import re
import shutil
import subprocess
import sys

TRACKER_CLIS = {"acli": "Jira (acli)", "gh": "GitHub Issues (gh)", "linear": "Linear (linear CLI)"}
TRACKER_MCP = (("jira", "Jira"), ("atlassian", "Jira"), ("linear", "Linear"), ("github", "GitHub Issues"))
DB_ENV = re.compile(r"^(?:\w*DATABASE_URL\w*|\w+_DB_URL|PG[A-Z_]+)$")
NOT_A_DB_ENV = re.compile(r"PASS|SECRET|TOKEN", re.I)
ENV_FILES = (".env", ".env.example", ".env.sample", ".env.local", ".env.development")
DATA_IMAGES = re.compile(r"postgres|postgis|mysql|mariadb|redis|mongo|rabbitmq|elasticsearch|opensearch|kafka|"
                         r"zookeeper|memcached|minio|mailhog|mailpit|localstack|clickhouse", re.I)
PORT_IN_SCRIPT = re.compile(r"(?:--port[= ]|-p[= ]|PORT=|localhost:|127\.0\.0\.1:)(\d{2,5})\b")
DEFAULT_PORTS = (("next dev", 3000), ("vite", 5173), ("react-scripts start", 3000), ("nuxt", 3000),
                 ("astro dev", 4321), ("remix dev", 3000))
USERINFO = re.compile(r"(://)[^/@\s]+@")
CONFIGS = (("project_profile", ".claude/project-profile.md"), ("query_db", ".claude/query-db.json"),
           ("query_db_old_markdown", ".claude/query-db.md"), ("verify_web", ".claude/verify-web.yaml"),
           ("verify_web", ".claude/verify-web.yml"), ("verify_web", ".claude/verify-web.json"),
           ("mcp_servers", ".mcp.json"))


def item(value, source):
    return {"value": value, "source": source}


def read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def clean_url(url):
    """A URL without user:password@, query string or fragment, any of which can hold a token."""
    return re.split(r"[?#]", USERINFO.sub(r"\1", url), maxsplit=1)[0]


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


# --- git ----------------------------------------------------------------------------------------

def detect_git(root):
    out = {"base_remote": [], "default_branch": [], "remote_url": []}
    if git(root, "rev-parse", "--is-inside-work-tree") != "true":
        return out
    remotes = (git(root, "remote") or "").split()
    remote = "upstream" if "upstream" in remotes else ("origin" if "origin" in remotes else (remotes[0] if remotes else None))
    if remote:
        out["base_remote"].append(item(remote, "git remote"))
        url = git(root, "remote", "get-url", remote)
        if url:
            out["remote_url"].append(item(clean_url(url), f"git remote get-url {remote}"))
        head = git(root, "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD")
        if head and "/" in head:
            out["default_branch"].append(item(head.split("/", 1)[1], f"git symbolic-ref refs/remotes/{remote}/HEAD"))
    if not out["default_branch"]:
        local = (git(root, "branch", "--format=%(refname:short)") or "").split()
        for name in ("main", "master", "trunk", "develop"):
            if name in local:
                out["default_branch"].append(item(name, "git branch (local branch name)"))
                break
    return out


# --- tracker ------------------------------------------------------------------------------------

def mcp_servers(root):
    text = read(root, ".mcp.json")
    if text is None:
        return {}
    try:
        servers = json.loads(text).get("mcpServers") or {}
    except (ValueError, AttributeError):
        return {}
    return servers if isinstance(servers, dict) else {}


def detect_tracker(root, servers, remote_urls):
    found = []
    for cli, label in TRACKER_CLIS.items():
        if shutil.which(cli):
            found.append(item({"tracker": label, "via": cli}, f"PATH: {cli}"))
    for name in servers:
        low = name.lower()
        for needle, label in TRACKER_MCP:
            if needle in low:
                found.append(item({"tracker": label, "via": f"MCP server {name}"}, f".mcp.json: mcpServers.{name}"))
                break
    for r in remote_urls:
        if "github.com" in r["value"]:
            found.append(item({"tracker": "GitHub Issues", "via": "the repo's GitHub remote"}, r["source"]))
    return found


# --- tests --------------------------------------------------------------------------------------

def package_json(root):
    text = read(root, "package.json")
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def runner(root):
    if os.path.isfile(os.path.join(root, "pnpm-lock.yaml")):
        return "pnpm"
    if os.path.isfile(os.path.join(root, "yarn.lock")):
        return "yarn"
    if os.path.isfile(os.path.join(root, "bun.lockb")) or os.path.isfile(os.path.join(root, "bun.lock")):
        return "bun"
    return "npm"


def detect_tests(root, pkg):
    found = []
    scripts = (pkg or {}).get("scripts") or {}
    test = scripts.get("test")
    if isinstance(test, str) and "no test specified" not in test:
        found.append(item(f"{runner(root)} test", "package.json: scripts.test"))
    py = read(root, "pyproject.toml") or ""
    cfg = read(root, "setup.cfg") or ""
    if "[tool.pytest" in py or re.search(r"^\s*\"?pytest\b", py, re.M):
        found.append(item("pytest", "pyproject.toml"))
    elif os.path.isfile(os.path.join(root, "pytest.ini")):
        found.append(item("pytest", "pytest.ini"))
    elif "[tool:pytest]" in cfg:
        found.append(item("pytest", "setup.cfg"))
    elif os.path.isfile(os.path.join(root, "conftest.py")):
        found.append(item("pytest", "conftest.py"))
    make = read(root, "Makefile")
    if make and re.search(r"^test\s*:", make, re.M):
        found.append(item("make test", "Makefile: test target"))
    if os.path.isfile(os.path.join(root, "go.mod")):
        found.append(item("go test ./...", "go.mod"))
    if os.path.isfile(os.path.join(root, "Cargo.toml")):
        found.append(item("cargo test", "Cargo.toml"))
    return found


# --- docker compose (a line scan for services, image and ports; no YAML library) -----------------

def compose_file(root):
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        if os.path.isfile(os.path.join(root, name)):
            return name
    return None


def compose_services(text):
    """{service: {"image": str|None, "ports": [str]}} from the top-level services: block."""
    services, current, in_services, svc_indent, in_ports, ports_indent = {}, None, False, None, False, None
    for raw in text.splitlines():
        line = raw.split(" #")[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            in_services = stripped == "services:"
            current = None
            continue
        if not in_services:
            continue
        if svc_indent is None:
            svc_indent = indent
        if indent == svc_indent and stripped.endswith(":"):
            current = stripped[:-1].strip().strip("'\"")
            services[current] = {"image": None, "ports": []}
            in_ports = False
            continue
        if current is None:
            continue
        if in_ports and indent > ports_indent:
            m = re.match(r"-\s*['\"]?([^'\"]+)['\"]?$", stripped)
            if m:
                services[current]["ports"].append(m.group(1).strip())
            pm = re.match(r"-?\s*published:\s*['\"]?(\d+)", stripped)
            if pm:
                services[current]["ports"].append(f"{pm.group(1)}:published")
            continue
        in_ports = False
        m = re.match(r"image:\s*['\"]?([^'\"\s]+)", stripped)
        if m:
            services[current]["image"] = m.group(1)
        elif stripped == "ports:":
            in_ports, ports_indent = True, indent
        else:
            m = re.match(r"ports:\s*\[(.*)\]", stripped)
            if m:
                services[current]["ports"] += [p.strip().strip("'\"") for p in m.group(1).split(",") if p.strip()]
    return services


def compose_project(root, text):
    """Compose's project name: a top-level name:, else the folder name, lowercased, as compose does."""
    m = re.search(r"^name:\s*['\"]?([^'\"\s#]+)", text or "", re.M)
    raw = m.group(1) if m else os.path.basename(os.path.abspath(root))
    return re.sub(r"[^a-z0-9_-]", "", raw.lower())


def compose_containers(root, text, services, compose):
    """Container names compose gives by default (<project>-<service>-1), or container_name: when set."""
    explicit = {}
    current = None
    for line in (text or "").splitlines():
        m = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
        if m:
            current = m.group(1)
        m = re.match(r"^\s+container_name:\s*['\"]?([^'\"\s#]+)", line)
        if m and current:
            explicit[current] = m.group(1)
    project = compose_project(root, text)
    return [item(explicit.get(svc, f"{project}-{svc}-1"),
                 f"{compose}: services.{svc}" + (".container_name" if svc in explicit else f" (project {project})"))
            for svc in services]


def mcp_literal_secrets(servers):
    """MCP servers whose env or headers hold a literal value instead of a ${VAR} reference. Names only."""
    found = []
    for name, server in servers.items():
        if not isinstance(server, dict):
            continue
        for block in ("env", "headers"):
            values = server.get(block)
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                if isinstance(value, str) and value and not re.fullmatch(r"(?:\w+\s+)?\$\{\w+(?::-[^}]*)?\}", value.strip()):
                    found.append(item({"server": name, block: key}, f".mcp.json: mcpServers.{name}.{block}.{key}"))
        args = server.get("args") if isinstance(server.get("args"), list) else []
        for i, a in enumerate(args):
            if isinstance(a, str) and (USERINFO.search(a) or re.search(r"password\s*=", a, re.I)):
                found.append(item({"server": name, "args": i}, f".mcp.json: mcpServers.{name}.args[{i}]"))
    return found


def host_port(mapping):
    """The host port of a compose port mapping: "8080:80" -> 8080, "127.0.0.1:5433:5432" -> 5433."""
    parts = mapping.split("/")[0].split(":")
    if len(parts) == 1:
        return None
    candidate = parts[-2]
    return int(candidate) if candidate.isdigit() else None


# --- local app URL -------------------------------------------------------------------------------

def env_lines(root):
    """(file, name, value) for each NAME=value line. Values stay inside this module."""
    out = []
    for rel in ENV_FILES:
        text = read(root, rel)
        if text is None:
            continue
        for line in text.splitlines():
            m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
            if m:
                out.append((rel, m.group(1), m.group(2).strip().strip("'\"")))
    return out


def detect_app_urls(root, pkg, services, compose):
    found = []

    def add(url, source):
        for f in found:
            if f["value"] == url:
                f["source"] += f"; {source}"
                return
        found.append(item(url, source))

    scripts = (pkg or {}).get("scripts") or {}
    for name in ("dev", "start", "serve"):
        cmd = scripts.get(name)
        if not isinstance(cmd, str):
            continue
        m = PORT_IN_SCRIPT.search(cmd)
        if m:
            add(f"http://localhost:{m.group(1)}", f"package.json: scripts.{name}")
            continue
        for needle, port in DEFAULT_PORTS:
            if needle in cmd:
                add(f"http://localhost:{port}", f"package.json: scripts.{name} ({needle} default port)")
                break
    for svc, info in services.items():
        if info["image"] and DATA_IMAGES.search(info["image"]):
            continue
        if DATA_IMAGES.search(svc):
            continue
        for p in info["ports"]:
            hp = host_port(p)
            if hp:
                add(f"http://localhost:{hp}", f"{compose}: services.{svc}.ports")
    for rel, name, value in env_lines(root):
        if name == "PORT" and value.isdigit():
            add(f"http://localhost:{value}", f"{rel}: PORT")
        elif name == "APP_URL" and re.match(r"https?://", value) and not USERINFO.search(value):
            add(value, f"{rel}: APP_URL")
    return found


# --- databases ----------------------------------------------------------------------------------

def mentions_postgres(name, server):
    args = server.get("args") if isinstance(server.get("args"), list) else []
    parts = [name, str(server.get("command", ""))] + [str(a) for a in args]
    return any(re.search(r"postgres|\bpg\b|psql", p, re.I) for p in parts)


def pg_service_names():
    path = os.environ.get("PGSERVICEFILE") or os.path.join(os.path.expanduser("~"), ".pg_service.conf")
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(path)
    except configparser.Error:
        return [], path
    return parser.sections(), path


def detect_databases(root, servers, services, compose):
    found = []
    for svc, info in services.items():
        if info["image"] and re.search(r"postgres|postgis", info["image"], re.I):
            ports = [host_port(p) for p in info["ports"] if host_port(p)]
            value = {"kind": "compose_service", "name": svc, "image": info["image"]}
            if ports:
                value["host_port"] = ports[0]
            found.append(item(value, f"{compose}: services.{svc}"))
    seen = set()
    for rel, name, _value in env_lines(root):
        if DB_ENV.match(name) and not NOT_A_DB_ENV.search(name) and (rel, name) not in seen:
            seen.add((rel, name))
            found.append(item({"kind": "env_var", "name": name}, rel))
    for name, server in servers.items():
        if isinstance(server, dict) and mentions_postgres(name, server):
            found.append(item({"kind": "mcp_server", "name": name}, f".mcp.json: mcpServers.{name}"))
    sections, path = pg_service_names()
    for s in sections:
        found.append(item({"kind": "pg_service", "name": s}, path.replace(os.path.expanduser("~"), "~", 1)))
    return found


def detect(root):
    root = os.path.abspath(root)
    out = {"project": root}
    out.update(detect_git(root))
    servers = mcp_servers(root)
    pkg = package_json(root)
    compose = compose_file(root)
    compose_text = read(root, compose) if compose else None
    services = compose_services(compose_text) if compose else {}
    out["tracker"] = detect_tracker(root, servers, out["remote_url"])
    out["tests"] = detect_tests(root, pkg)
    out["app_urls"] = detect_app_urls(root, pkg, services, compose)
    out["databases"] = detect_databases(root, servers, services, compose)
    out["mcp_servers"] = [item(name, f".mcp.json: mcpServers.{name}") for name in servers]
    out["mcp_literal_secrets"] = mcp_literal_secrets(servers)
    out["compose_containers"] = compose_containers(root, compose_text, services, compose) if compose else []
    out["existing_config"] = [item(kind, rel) for kind, rel in CONFIGS if os.path.isfile(os.path.join(root, rel))]
    return out


if __name__ == "__main__":
    print(json.dumps(detect(sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))
