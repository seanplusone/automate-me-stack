#!/usr/bin/env python3
"""Read-only health check for the app verify-web is about to drive. Python stdlib only.

Usage:
  python3 doctor.py [--config <file>] [--base-url <url>] [--expect-sha <sha>]
  python3 doctor.py --check-config [--config <file>]   # parse and check the config's shape only

The config is the first of .claude/verify-web.yaml, .claude/verify-web.yml or .claude/verify-web.json
found from the current directory upward, unless --config names one. Its shape is verify-web.example.yaml.

Prints one PASS, WARN or FAIL line per check, then `DOCTOR: OK` (exit 0) or `DOCTOR: FAIL` (exit 1).
It never restarts, edits or writes anything. On a FAIL that has a pre-authorized restart in the config,
it prints that command; it does not run it.

--check-config reads the config and checks its keys and types, with no HTTP, docker or process calls,
then prints `CONFIG: OK` (exit 0) or `CONFIG: FAIL` (exit 1). /automate-me:setup runs it before writing.

A health url that starts with "/" and a {base_url} in a serving_tree command use the first app
with test_data: true, or --base-url when given (PR mode, for a second copy of the app on its own port).
"""
import argparse
import json
import os
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

CONFIG_NAMES = ("verify-web.yaml", "verify-web.yml", "verify-web.json")
CLOCK_SLACK = 2  # seconds; /proc start times are rounded, so a file saved just before the start is not STALE
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


# --- minimal YAML subset -------------------------------------------------------------------------
# Enough for verify-web.example.yaml: nested mappings, lists of scalars or mappings, inline [a, b]
# lists, quoted or plain scalars, ints, true/false/null, and # comments. No anchors, no multi-line
# strings, no flow mappings. Anything else raises ValueError with the line number.

class YamlError(ValueError):
    pass


def _strip_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text, n):
    t = text.strip()
    if t == "" or t in ("null", "~"):
        return None
    if t[0] in "'\"":
        if len(t) < 2 or t[-1] != t[0]:
            raise YamlError(f"line {n}: unclosed quote: {t}")
        return t[1:-1]
    if t.startswith("["):
        if not t.endswith("]"):
            raise YamlError(f"line {n}: unclosed inline list: {t}")
        inner = t[1:-1].strip()
        return [_scalar(p, n) for p in _split_flow(inner)] if inner else []
    if t.startswith(("{", "&", "*", "|", ">")):
        raise YamlError(f"line {n}: unsupported YAML ({t[0]}); use the JSON config instead")
    if t in ("true", "True", "yes"):
        return True
    if t in ("false", "False", "no"):
        return False
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    return t


def _split_flow(inner):
    parts, cur, quote = [], [], None
    for ch in inner:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch == ",":
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    parts.append("".join(cur))
    return parts


def _split_key(text):
    m = re.match(r"""^("[^"]*"|'[^']*'|[^:'"]+?):(?:\s+(.*)|$)""", text)
    if not m:
        return None
    key = m.group(1).strip().strip("'\"")
    return key, (m.group(2) or "")


def parse_yaml(text):
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {n}: tab in indentation")
        body = _strip_comment(raw)
        if body.strip() in ("", "---"):
            continue
        lines.append((n, len(body) - len(body.lstrip(" ")), body.strip()))
    if not lines:
        return {}
    value, i = _block(lines, 0, lines[0][1])
    if i != len(lines):
        n = lines[i][0]
        raise YamlError(f"line {n}: bad indentation")
    return value


def _block(lines, i, indent):
    if lines[i][2].startswith("- ") or lines[i][2] == "-":
        return _list(lines, i, indent)
    return _map(lines, i, indent)


def _map(lines, i, indent):
    out = {}
    while i < len(lines) and lines[i][1] == indent:
        n, _, text = lines[i]
        if text.startswith("-"):
            raise YamlError(f"line {n}: list item where a key was expected")
        kv = _split_key(text)
        if not kv:
            raise YamlError(f"line {n}: expected 'key: value'")
        key, rest = kv
        if key in out:
            raise YamlError(f"line {n}: duplicate key {key}")
        i += 1
        if rest.strip() == "":
            if i < len(lines) and lines[i][1] > indent:
                out[key], i = _block(lines, i, lines[i][1])
            elif i < len(lines) and lines[i][1] == indent and lines[i][2].startswith("- "):
                out[key], i = _list(lines, i, indent)  # list items at the key's own indent
            else:
                out[key] = None
        else:
            out[key] = _scalar(rest, n)
    if i < len(lines) and lines[i][1] > indent:
        raise YamlError(f"line {lines[i][0]}: bad indentation")
    return out, i


def _list(lines, i, indent):
    out = []
    while i < len(lines) and lines[i][1] == indent and (lines[i][2].startswith("- ") or lines[i][2] == "-"):
        n, _, text = lines[i]
        rest = text[1:].strip()
        if rest == "":
            i += 1
            if i < len(lines) and lines[i][1] > indent:
                item, i = _block(lines, i, lines[i][1])
            else:
                item = None
            out.append(item)
            continue
        kv = _split_key(rest) if not rest.startswith(("'", '"', "[")) else None
        if kv:
            # "- key: value" starts a mapping whose keys sit at the column after "- ".
            child = indent + (len(text) - len(rest))
            sub = [(n, child, rest)] + lines[i + 1:]
            item, j = _map(sub, 0, child)
            i = i + j
            out.append(item)
        else:
            out.append(_scalar(rest, n))
            i += 1
    return out, i


def load_config(path):
    text = open(path).read()
    if path.endswith(".json"):
        return json.loads(text)
    return parse_yaml(text)


def find_config(start):
    d = os.path.abspath(start)
    while True:
        for name in CONFIG_NAMES:
            p = os.path.join(d, ".claude", name)
            if os.path.isfile(p):
                return p
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def project_root(config_path):
    d = os.path.dirname(os.path.abspath(config_path))
    return os.path.dirname(d) if os.path.basename(d) == ".claude" else d


# --- helpers -------------------------------------------------------------------------------------

def expand(value):
    """${VAR} and ~ in strings. An unset ${VAR} stays as written, so the check that uses it fails loudly."""
    if not isinstance(value, str):
        return value
    value = re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), value)
    return os.path.expanduser(value)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def http_status(url, timeout=10):
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, OSError) as e:
        return 0, str(getattr(e, "reason", e))


def run(cmd, cwd, timeout=20):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"


def pid_start_time(pid):
    """Epoch seconds the process started, or None if it is not running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        pass
    if os.path.exists(f"/proc/{pid}/stat"):
        stat_line = open(f"/proc/{pid}/stat").read()
        fields = stat_line[stat_line.rindex(")") + 2:].split()
        ticks = int(fields[19])  # field 22 of the full line: starttime in clock ticks since boot
        btime = next(int(l.split()[1]) for l in open("/proc/stat") if l.startswith("btime"))
        return btime + ticks / os.sysconf("SC_CLK_TCK")
    code, out, _ = run(["ps", "-o", "etime=", "-p", str(pid)], None)  # macOS and BSD: [[dd-]hh:]mm:ss
    if code != 0 or not out:
        return None
    days, _, clock = out.strip().rpartition("-")
    parts = [int(x) for x in clock.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    secs = (int(days or 0) * 86400) + parts[0] * 3600 + parts[1] * 60 + parts[2]
    return time.time() - secs


def container_start_time(name):
    code, out, err = run(["docker", "inspect", "-f", "{{.State.Running}} {{.State.StartedAt}}", name], None)
    if code != 0:
        return None, err or "not found"
    running, _, started = out.partition(" ")
    if running != "true":
        return None, "not running"
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z", started)
    if not m:
        return None, f"cannot read start time {started!r}"
    import calendar
    return calendar.timegm(time.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")) + float(m.group(2) or 0), ""


def newest_file(dirs, exts):
    best = (0.0, None)
    for d in dirs:
        if os.path.isfile(d):
            candidates = [(os.path.dirname(d), [], [os.path.basename(d)])]
        else:
            candidates = os.walk(d)
        for root, subdirs, files in candidates:
            subdirs[:] = [s for s in subdirs if s not in SKIP_DIRS and not s.startswith(".")]
            for f in files:
                if exts and not any(f.endswith(e) for e in exts):
                    continue
                p = os.path.join(root, f)
                try:
                    m = os.stat(p).st_mtime
                except OSError:
                    continue
                if m > best[0]:
                    best = (m, p)
    return best


def tree_of(text):
    """'<branch> <sha>' printed by a serving-tree command, as (branch, sha)."""
    parts = text.split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return "?", parts[0]
    return None


# --- the doctor ----------------------------------------------------------------------------------

class Doctor:
    def __init__(self, cfg, root, expect_sha=None, skill_dir=None, base_url=None):
        self.cfg, self.root, self.expect_sha = cfg or {}, root, expect_sha
        self.override = base_url
        safe = [a for a in (self.cfg.get("apps") or []) if isinstance(a, dict) and a.get("test_data")]
        if not base_url and safe:
            base_url = expand(safe[0].get("base_url") or "")
        self.base_url = (base_url or "").rstrip("/")
        self.skill_dir = skill_dir or os.path.dirname(os.path.abspath(__file__))
        self.fails = 0
        self.restarts = {r.get("for"): r.get("command") for r in (self.cfg.get("restarts") or []) if isinstance(r, dict)}

    def line(self, level, name, msg):
        print(f"{level:<5} {name:<32} {msg}")
        if level == "FAIL":
            self.fails += 1
            if name in self.restarts:
                print(f"      pre-authorized fix: {self.restarts[name]}  (then rerun the doctor)")

    def path(self, p):
        p = expand(p)
        return p if os.path.isabs(p) else os.path.join(self.root, p)

    def check_apps(self):
        apps = self.cfg.get("apps") or []
        if self.override:
            self.line("PASS", "checking", f"{self.base_url} (--base-url)")
        if not apps:
            self.line("FAIL", "config apps", "no apps listed; run /automate-me:setup or fill in verify-web.example.yaml")
            return
        safe = [a for a in apps if a.get("test_data")]
        for a in apps:
            tag = "safe for test data" if a.get("test_data") else "NOT for test data"
            self.line("PASS" if a.get("base_url") else "FAIL", f"app {a.get('name', '?')}",
                      f"{expand(a.get('base_url')) or 'no base_url'}  ({tag})")
        if not safe:
            self.line("WARN", "config apps", "no app has test_data: true, so no run may create data")

    def check_health(self):
        for h in self.cfg.get("health") or []:
            name, url = f"http {h.get('name', '?')}", expand(h.get("url", ""))
            if url.startswith("/"):
                url = self.base_url + url
            want = h.get("expect_status", 200)
            want = want if isinstance(want, list) else [want]
            code, err = http_status(url, timeout=h.get("timeout", 10))
            if code in want:
                self.line("PASS", name, f"{code}  {url}")
            elif code == 0:
                self.line("FAIL", name, f"no answer from {url} ({err})")
            else:
                self.line("FAIL", name, f"{code}, expected {'/'.join(map(str, want))}  {url}")

    def check_containers(self):
        for c in self.cfg.get("containers") or []:
            c = expand(c)
            code, out, err = run(["docker", "inspect", "-f", "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}", c], None)
            state = out.strip()
            if code != 0:
                self.line("FAIL", f"container {c}", f"not found ({err or 'docker inspect failed'})")
            elif state in ("running", "running healthy"):
                self.line("PASS", f"container {c}", state)
            elif state == "running unhealthy":
                self.line("WARN", f"container {c}", "running, its healthcheck is failing; trust the http checks")
            else:
                self.line("FAIL", f"container {c}", state)

    def check_workers(self):
        for w in self.cfg.get("workers") or []:
            name = f"worker {w.get('name', '?')}"
            if w.get("container"):
                started, err = container_start_time(expand(w["container"]))
                if started is None:
                    self.line("FAIL", name, f"container {expand(w['container'])}: {err}")
                    continue
            elif w.get("pid_file"):
                pf = self.path(w["pid_file"])
                try:
                    pid = int(open(pf).read().strip())
                except (OSError, ValueError):
                    self.line("FAIL", name, f"no readable pid file at {pf}")
                    continue
                started = pid_start_time(pid)
                if started is None:
                    self.line("FAIL", name, f"pid {pid} from {pf} is not running")
                    continue
            else:
                self.line("FAIL", name, "config needs container or pid_file")
                continue
            dirs = [self.path(d) for d in (w.get("source_dirs") or [])]
            exts = w.get("source_ext") or []
            mtime, newest = newest_file(dirs, exts)
            age = int((time.time() - started) / 60)
            if newest and mtime > started + CLOCK_SLACK:
                rel = os.path.relpath(newest, self.root)
                self.line("FAIL", name, f"STALE: started {age}m ago, {rel} changed after. It is running old code.")
            elif not dirs:
                self.line("WARN", name, f"running, started {age}m ago; no source_dirs, so staleness is not checked")
            else:
                self.line("PASS", name, f"started {age}m ago, no source file newer than its start")

    def check_trees(self):
        st = self.cfg.get("serving_tree") or {}
        if not st:
            if self.expect_sha:
                self.line("FAIL", "tree page", "--expect-sha given but the config has no serving_tree command")
            return
        trees = {}
        for key, label in (("page_command", "page"), ("job_command", "job")):
            cmd = st.get(key)
            if not cmd:
                continue
            code, out, err = run(expand(cmd).replace("{base_url}", self.base_url), self.root)
            t = tree_of(out) if code == 0 else None
            if not t:
                self.line("FAIL", f"tree {label}", f"`{cmd}` gave no '<branch> <sha>' ({err or out or 'empty'})")
                continue
            trees[label] = t
            msg = f"{label} runs {t[0]} {t[1][:12]}"
            if self.expect_sha and not t[1].startswith(self.expect_sha[:7]) and not self.expect_sha.startswith(t[1][:7]):
                self.line("FAIL", f"tree {label}", f"{msg}, expected {self.expect_sha[:12]}. Point the app at that tree first.")
            else:
                self.line("PASS", f"tree {label}", msg)
        if "page" in trees and "job" in trees and trees["page"][1][:7] != trees["job"][1][:7]:
            self.line("WARN", "tree match", f"page and job run DIFFERENT trees: page {trees['page'][1][:12]}, job {trees['job'][1][:12]}. "
                      "A result proves only the half that ran your code.")

    def check_logins(self):
        personas = self.cfg.get("personas") or {}
        if not personas:
            return
        env_path = self.path(self.cfg.get("users_env") or "~/.config/verify-web/users.env")
        if not os.path.isfile(env_path):
            self.line("WARN", "logins", f"{env_path} missing; copy users.env.example there and chmod 600 it")
            return
        mode = stat.S_IMODE(os.stat(env_path).st_mode)
        if mode & 0o077:
            self.line("WARN", "logins", f"{env_path} is mode {oct(mode)[2:]}; run chmod 600 on it")
        values = {}
        for raw in open(env_path):
            k, sep, v = raw.strip().partition("=")
            if sep and not k.startswith("#"):
                values[k.strip()] = v.strip()
        for role, p in personas.items():
            p = p or {}
            missing = [p.get(k) for k in ("username_env", "password_env") if p.get(k) and not values.get(p.get(k))]
            if missing:
                self.line("WARN", f"persona {role}", f"no value for {', '.join(missing)} in {env_path}")
            else:
                self.line("PASS", f"persona {role}", "login present")

    def check_evidence(self):
        ev = self.path(self.cfg.get("evidence_dir") or "~/.claude/verify-evidence/web")
        plugin = os.path.dirname(os.path.dirname(self.skill_dir))
        if os.path.abspath(ev).startswith(os.path.abspath(plugin) + os.sep):
            self.line("WARN", "evidence dir", f"{ev} is inside the plugin; an update would delete it")
        else:
            self.line("PASS", "evidence dir", ev)

    def run(self):
        for step in (self.check_apps, self.check_health, self.check_containers, self.check_workers,
                     self.check_trees, self.check_logins, self.check_evidence):
            step()
        print()
        print("DOCTOR: OK" if self.fails == 0 else f"DOCTOR: FAIL ({self.fails} failing). Fix before driving the app.")
        return 0 if self.fails == 0 else 1


def config_problems(cfg):
    """Shape problems in a parsed config, as (level, message) pairs. No I/O."""
    out = []
    if not isinstance(cfg, dict):
        return [("FAIL", "the config is not a mapping of keys")]
    apps = cfg.get("apps")
    if not isinstance(apps, list) or not apps:
        out.append(("FAIL", "apps: list at least one app with a name and a base_url"))
        apps = []
    for i, a in enumerate(apps):
        if not isinstance(a, dict) or not a.get("name") or not a.get("base_url"):
            out.append(("FAIL", f"apps[{i}]: needs name and base_url"))
        elif not re.match(r"(https?://|\$\{)", str(a["base_url"])):
            out.append(("FAIL", f"apps[{i}].base_url: {a['base_url']!r} is not an http(s) URL"))
    if apps and not any(isinstance(a, dict) and a.get("test_data") is True for a in apps):
        out.append(("WARN", "apps: no app has test_data: true, so no run may create data"))
    personas = cfg.get("personas")
    if personas is None:
        out.append(("WARN", "personas: none listed, so runs cannot sign in"))
    elif not isinstance(personas, dict):
        out.append(("FAIL", "personas: must map a role to username_env and password_env"))
    else:
        for role, p in personas.items():
            if not isinstance(p, dict) or not p.get("username_env") or not p.get("password_env"):
                out.append(("FAIL", f"personas.{role}: needs username_env and password_env (env var names)"))
    for key in ("health", "workers", "restarts", "containers"):
        if key in cfg and not isinstance(cfg[key], list):
            out.append(("FAIL", f"{key}: must be a list"))
    for i, h in enumerate(cfg.get("health") or []):
        want = h.get("expect_status", 200) if isinstance(h, dict) else None
        codes = want if isinstance(want, list) else [want]
        if not isinstance(h, dict) or not h.get("url"):
            out.append(("FAIL", f"health[{i}]: needs a url"))
        elif not all(isinstance(c, int) for c in codes):
            out.append(("FAIL", f"health[{i}].expect_status: must be a status code or a list of them"))
    for i, w in enumerate(cfg.get("workers") or []):
        if not isinstance(w, dict) or not w.get("name") or not (w.get("container") or w.get("pid_file")):
            out.append(("FAIL", f"workers[{i}]: needs a name and a container or pid_file"))
        elif not isinstance(w.get("source_dirs"), list) or not w["source_dirs"]:
            out.append(("FAIL", f"workers[{i}].source_dirs: list the folders it loads code from"))
    for i, r in enumerate(cfg.get("restarts") or []):
        if not isinstance(r, dict) or not r.get("for") or not r.get("command"):
            out.append(("FAIL", f"restarts[{i}]: needs for and command"))
    if not cfg.get("evidence_dir"):
        out.append(("WARN", "evidence_dir: not set"))
    return out


def check_config_only(path):
    print(f"config: {path}")
    try:
        cfg = load_config(path)
    except (OSError, ValueError) as e:
        print(f"FAIL  {e}")
        print("\nCONFIG: FAIL")
        return 1
    problems = config_problems(cfg)
    for level, msg in problems:
        print(f"{level:<5} {msg}")
    fails = sum(1 for level, _ in problems if level == "FAIL")
    print("\nCONFIG: OK" if not fails else f"\nCONFIG: FAIL ({fails} failing)")
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config")
    ap.add_argument("--expect-sha", help="FAIL unless the serving tree reports this sha (PR mode)")
    ap.add_argument("--base-url", help="the app to check, instead of the first test_data app (PR mode)")
    ap.add_argument("--check-config", action="store_true", help="check the config's shape only; no network")
    a = ap.parse_args(argv)
    path = a.config or find_config(os.getcwd())
    if not path or not os.path.isfile(path):
        print("FAIL  config                           no .claude/verify-web.yaml (or .json) found from here upward; "
              "run /automate-me:setup, or copy verify-web.example.yaml there")
        print("\nDOCTOR: FAIL (1 failing). Fix before driving the app.")
        return 1
    if a.check_config:
        return check_config_only(path)
    try:
        cfg = load_config(path)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"FAIL  config                           {path}: {e}")
        print("\nDOCTOR: FAIL (1 failing). Fix before driving the app.")
        return 1
    print(f"config: {path}")
    return Doctor(cfg, project_root(path), a.expect_sha, base_url=a.base_url).run()


if __name__ == "__main__":
    sys.exit(main())
